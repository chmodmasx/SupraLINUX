#!/usr/bin/env python3
"""Import reviewed KDE packaging and pin one clean-build manifest.

The tool is intentionally limited to quilt sources whose upstream tarball is
already downloaded and verified by SHA-256.  It resolves Build-Depends against
the Ubuntu archive plus the signed SupraLINUX archive, then records both the
packaging tree and the exact dependency closure in Git.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = Path(os.environ.get("SUPRALINUX_WORKSPACE", ROOT.parent / "SupraLINUX-workspace")).expanduser().resolve()
sys.path.insert(0, str(ROOT / "tools"))
import clean_build
import import_framework


def workspace_path(value):
    path = Path(value).expanduser()
    return (WORKSPACE / path).resolve() if not path.is_absolute() else path.resolve()


def portable_path(path):
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(WORKSPACE))
    except ValueError:
        return str(resolved)



def digest(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def drop_patch(debian, name):
    patches = debian / "patches"
    patch = patches / name
    if patch.exists():
        patch.unlink()
    series = patches / "series"
    if series.is_file():
        lines = [line for line in series.read_text().splitlines()
                 if line.strip() != name and line.strip() != "#" + name]
        series.write_text("\n".join(lines) + ("\n" if lines else ""))


def disable_qch_installs(debian):
    for path in debian.glob("*.install"):
        lines = []
        for line in path.read_text().splitlines():
            if re.fullmatch(r"usr/share/qt6/doc/.*\.(?:qch|tags)", line.strip()):
                lines.append("#" + line)
            else:
                lines.append(line)
        path.write_text("\n".join(lines) + ("\n" if lines else ""))


def copy_packaging(source, destination, drop_patches):
    if destination.exists():
        shutil.rmtree(destination)
    import_framework.copy_packaging(source, destination)
    disable_qch_installs(destination)
    for name in drop_patches:
        drop_patch(destination, name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--debian-source", type=Path, required=True)
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--main-package", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--upstream-version", required=True)
    parser.add_argument("--upstream-url", required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--preferences", type=Path, required=True)
    parser.add_argument("--base-image", type=Path, required=True)
    parser.add_argument("--base-image-sha256", required=True)
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--sbuild-version", default="0.91.2ubuntu3")
    parser.add_argument("--guest-ram-mib", type=int, default=4096)
    parser.add_argument("--guest-vcpus", type=int, default=4)
    parser.add_argument("--deps-output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--drop-patch", action="append", default=[])
    parser.add_argument("--note", action="append", default=[])
    parser.add_argument("--expected-path", action="append", default=[])
    parser.add_argument("--timeout", type=int, default=7200)
    args = parser.parse_args()

    if args.upstream.is_symlink() or not args.upstream.is_file():
        raise SystemExit("Missing upstream tarball")
    base_image = workspace_path(args.base_image)
    rootfs = workspace_path(args.rootfs)
    sources = workspace_path(args.sources)
    preferences = workspace_path(args.preferences)
    deps_output = workspace_path(args.deps_output)
    manifest_path = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    if not base_image.is_file() or not rootfs.is_file():
        raise SystemExit("Missing builder image or rootfs")
    if digest(base_image) != args.base_image_sha256:
        raise SystemExit("Builder image SHA-256 mismatch")
    upstream_sha = digest(args.upstream)

    package_dir = ROOT / args.package_dir
    copy_packaging(args.debian_source, package_dir / "debian", args.drop_patch)
    control = (package_dir / "debian/control").read_text()
    fields = clean_build.control_fields(control)
    declared = " ".join(fields["Build-Depends"].split())

    changelog = package_dir / "debian/changelog"
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    entry = (
        f"{args.source_name} ({args.version}) resolute; urgency=medium\n\n"
        + "".join(f"  * {note}\n" for note in args.note)
        + f"\n -- SupraLINUX Project <packages@supralinux.invalid>  {timestamp}\n\n"
    )
    if not changelog.read_text().startswith(f"{args.source_name} ({args.version})"):
        changelog.write_text(entry + changelog.read_text())

    subprocess.run([
        sys.executable, str(ROOT / "tools/resolve_build_deps.py"),
        "--build-depends", declared,
        "--sources", str(sources),
        "--preferences", str(preferences),
        "--rootfs", str(rootfs),
        "--output", str(deps_output),
    ], check=True)
    record = json.loads((deps_output / "resolved.json").read_text())

    version_no_epoch = args.version.split(":", 1)[-1]
    upstream_name = args.upstream.name
    manifest = {
        "schema": 1,
        "scope": "offline-clean-sbuild-build",
        "package": args.main_package,
        "version": args.version,
        "architecture": "amd64",
        "source": {
            "kind": "quilt",
            "path": str(package_dir.resolve().relative_to(ROOT.resolve())),
            "source_package": args.source_name,
            "version": args.version,
            "upstream_version": args.upstream_version,
            "dsc_name": f"{args.source_name}_{version_no_epoch}.dsc",
            "declared_build_depends": declared,
            "upstream": {
                "url": args.upstream_url,
                "sha256": upstream_sha,
                "filename": upstream_name,
                "extracted_dir": upstream_name.removesuffix(".tar.xz"),
                "orig_filename": f"{args.source_name}_{args.upstream_version}.orig.tar.xz",
            },
        },
        "base_image": {
            "path": portable_path(base_image),
            "sha256": args.base_image_sha256,
            "format": "qcow2",
            "scope": "inherited-builder-image; disposable-overlay-only",
        },
        "rootfs": {
            "path": portable_path(rootfs),
            "sha256": digest(rootfs),
            "bytes": rootfs.stat().st_size,
            "installed_package_count": record["rootfs"]["installed_package_count"],
            "scope": "inherited-buildd-rootfs; debhelper and fakeroot absent",
        },
        "build_dependencies": {
            "declared": declared,
            "source_evidence": record["source_evidence"],
            "resolved_at": record["generated_at"],
            "sources_sha256": record["sources"]["sha256"],
            "preferences_sha256": (record["preferences"]["sha256"]
                                   if record.get("preferences") else None),
            "packages": record["packages"],
        },
        "builder": {
            "sbuild_version": args.sbuild_version,
            "chroot_mode": "unshare",
            "distribution": "resolute",
            "architecture": "amd64",
            "guest_ram_mib": args.guest_ram_mib,
            "guest_vcpus": args.guest_vcpus,
            "guest_network": "none; loopback only",
            "repository_transport": "read-only ext4 input disk",
            "repository_scope": "local signed file: repository; archive sources disabled in chroot",
            "guest_timeout_seconds": args.timeout,
        },
        "expected_binaries": [
            {"package": name, "architecture": arch}
            for name, arch in import_framework.package_architectures(control)
        ],
        "verification": {"expected_paths": args.expected_path},
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    clean_build.load_manifest(manifest_path)
    print(json.dumps({
        "state": "PASS",
        "manifest": str(manifest_path),
        "packages": len(manifest["expected_binaries"]),
        "dependencies": len(record["packages"]),
    }, indent=2))


if __name__ == "__main__":
    main()
