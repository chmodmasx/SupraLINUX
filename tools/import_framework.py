#!/usr/bin/env python3
"""Import reviewed Ubuntu packaging for one Frameworks source and write a clean-build manifest."""
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


def strip_multiline_field(text, field):
    lines = text.splitlines()
    output = []
    skipping = False
    for line in lines:
        if line.startswith(field + ":"):
            skipping = True
            continue
        if skipping and line.startswith((" ", "\t")):
            continue
        skipping = False
        output.append(line)
    return "\n".join(output) + ("\n" if text.endswith("\n") else "")


def sanitize_control(text, maintainer="SupraLINUX Project <packages@supralinux.invalid>"):
    text = re.sub(r"^Maintainer:.*$", "Maintainer: " + maintainer, text, flags=re.MULTILINE)
    for field in ["Uploaders", "XSBC-Original-Maintainer", "Vcs-Browser", "Vcs-Git"]:
        text = strip_multiline_field(text, field)
    text = re.sub(r"^Testsuite:.*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r",\n(?=[A-Z][A-Za-z-]+:)", "\n", text)
    return text


def sanitize_rules(text):
    return text.replace("-DBUILD_QCH=ON", "-DBUILD_QCH=OFF")


def package_architectures(control):
    result = []
    current = None
    for line in control.splitlines():
        if line.startswith("Package: "):
            current = line.split(": ", 1)[1].strip()
        elif line.startswith("Architecture: ") and current:
            arch = line.split(": ", 1)[1].strip()
            result.append((current, "all" if arch == "all" else "amd64"))
            current = None
    return result


def copy_packaging(debian_source, destination):
    for item in ["tests", "salsa", "salsa-ci.yml"]:
        path = Path(debian_source) / item
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    destination.mkdir(parents=True, exist_ok=True)
    for item in Path(debian_source).iterdir():
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copyfile(item, target)
            target.chmod(item.stat().st_mode & 0o777)
    control = (destination / "control").read_text()
    (destination / "control").write_text(sanitize_control(control))
    rules = destination / "rules"
    if rules.is_file():
        rules.write_text(sanitize_rules(rules.read_text()))


def dependency_names(path):
    output = subprocess.check_output(
        ["dpkg-deb", "-f", str(path), "Depends", "Pre-Depends"], text=True
    )
    names = []
    for line in output.splitlines():
        if ": " not in line:
            continue
        for clause in line.split(": ", 1)[1].split(","):
            name = clause.split("|", 1)[0].strip().split(" ", 1)[0].split("(", 1)[0].split(":")[0].strip()
            if name and re.fullmatch(r"[a-z0-9][a-z0-9+.-]+", name):
                names.append(name)
    return names


def local_dependency_names(db_path):
    db = json.loads(Path(db_path).read_text())
    local = {entry["package"] for entry in db["packages"]}
    names = set()
    for entry in db["packages"]:
        names.update(dependency_names(entry["path"]))
    return sorted(names - local)


def add_local_packages(repo, db_path):
    db = json.loads(Path(db_path).read_text())
    record = json.loads((repo / "resolved.json").read_text())
    by_name = {entry["package"]: entry for entry in db["packages"]}
    for entry in by_name.values():
        path = Path(entry["path"])
        expected = entry["sha256"]
        if digest(path) != expected:
            raise ValueError("Local package hash mismatch: " + str(path))
        target = repo / expected / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copyfile(path, target)
            target.chmod(0o444)
        record["packages"] = [item for item in record["packages"] if item["name"] != entry["package"]]
        record["packages"].append({
            "name": entry["package"], "version": entry["version"],
            "architecture": entry["architecture"], "filename": path.name, "sha256": expected,
        })
    record["packages"].sort(key=lambda item: (item["name"], item["version"]))
    (repo / "resolved.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def write_manifest(args, repo, record, declared, upstream_sha, control):
    upstream = args.upstream
    extracted = upstream.name.removesuffix(".tar.xz")
    source_name = args.source_name
    upstream_version = args.upstream_version or args.version.split("-", 1)[0]
    version_no_epoch = args.version.split(":", 1)[-1]
    dsc_name = args.dsc_name or f"{source_name}_{version_no_epoch}.dsc"
    orig_filename = args.orig_filename or f"{source_name}_{upstream_version}.orig.tar.xz"
    url = args.upstream_url or (
        f"https://download.kde.org/stable/frameworks/{upstream_version.rsplit('.', 1)[0]}/{upstream.name}"
    )
    base_image = workspace_path(args.base_image)
    rootfs = workspace_path(args.rootfs)
    manifest = {
        "schema": 1,
        "scope": "offline-clean-sbuild-build",
        "package": args.main_package,
        "version": args.version,
        "architecture": "amd64",
        "source": {
            "kind": "quilt",
            "path": str((ROOT / args.package_dir).resolve().relative_to(ROOT.resolve())),
            "source_package": source_name,
            "version": args.version,
            "upstream_version": upstream_version,
            "dsc_name": dsc_name,
            "declared_build_depends": declared,
            "upstream": {
                "url": url,
                "sha256": upstream_sha,
                "filename": upstream.name,
                "extracted_dir": extracted,
                "orig_filename": orig_filename,
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
            {"package": name, "architecture": arch} for name, arch in package_architectures(control)
        ],
        "verification": {"expected_paths": args.expected_path},
    }
    path = Path(args.manifest)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--debian-source", type=Path, required=True)
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--main-package", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--upstream-version")
    parser.add_argument("--upstream-url")
    parser.add_argument("--dsc-name")
    parser.add_argument("--orig-filename")
    parser.add_argument("--base-image", type=Path, required=True)
    parser.add_argument("--base-image-sha256", required=True)
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--sbuild-version", default="0.91.2ubuntu3")
    parser.add_argument("--guest-ram-mib", type=int, default=4096)
    parser.add_argument("--guest-vcpus", type=int, default=4)
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--preferences", type=Path)
    parser.add_argument("--deps-output", type=Path, required=True)
    parser.add_argument("--local-db", type=Path, required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--expected-path", action="append", default=[])
    parser.add_argument("--timeout", type=int, default=5400)
    args = parser.parse_args()

    package_dir = ROOT / args.package_dir
    copy_packaging(args.debian_source, package_dir / "debian")
    control = (package_dir / "debian/control").read_text()
    fields = clean_build.control_fields(control)
    declared = " ".join(fields["Build-Depends"].split())
    if args.upstream.is_symlink() or not args.upstream.is_file():
        raise SystemExit("Missing upstream tarball")
    base_image = workspace_path(args.base_image)
    rootfs = workspace_path(args.rootfs)
    if not base_image.is_file() or not rootfs.is_file():
        raise SystemExit("Missing builder image or rootfs")
    if digest(base_image) != args.base_image_sha256:
        raise SystemExit("Builder image SHA-256 mismatch")
    upstream_sha = digest(args.upstream)
    local_db = args.local_db if args.local_db.is_absolute() else ROOT / args.local_db

    extra_packages = ["python3"] + local_dependency_names(local_db)
    resolver = [
        sys.executable, str(ROOT / "tools/resolve_build_deps.py"),
        "--build-depends", declared,
        "--extra-packages", *extra_packages,
        "--rootfs", str(rootfs),
        "--output", str(args.deps_output),
    ]
    if args.sources:
        resolver += ["--sources", str(workspace_path(args.sources))]
    if args.preferences:
        resolver += ["--preferences", str(workspace_path(args.preferences))]
    subprocess.run(resolver, check=True)
    repo = workspace_path(args.deps_output)
    record = add_local_packages(repo, local_db)
    # Add a reviewed changelog entry without keeping the distro maintainer identity.
    changelog = package_dir / "debian/changelog"
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    entry = (
        f"{args.source_name} ({args.version}) resolute; urgency=medium\n\n"
        "  * Package KDE Frameworks from upstream stable.\n"
        "  * Reuse the reviewed Ubuntu packaging layout for Debian-family names.\n"
        "  * Keep QCH disabled under the common SupraLINUX Frameworks profile.\n\n"
        f" -- SupraLINUX Project <packages@supralinux.invalid>  {timestamp}\n\n"
    )
    changelog.write_text(entry + changelog.read_text())
    manifest = write_manifest(args, repo, record, declared, upstream_sha, control)
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path
    clean_build.load_manifest(manifest_path)
    print(json.dumps({
        "state": "PASS", "manifest": str(manifest_path), "packages": len(manifest["expected_binaries"]),
        "dependencies": len(record["packages"]),
    }, indent=2))


if __name__ == "__main__":
    main()
