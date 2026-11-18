#!/usr/bin/env python3
"""Resolve Build-Depends against the current Ubuntu archive without installing them."""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = Path(os.environ.get("SUPRALINUX_WORKSPACE", ROOT.parent / "SupraLINUX-workspace")).expanduser().resolve()
ARCH = "amd64"


def workspace_path(value):
    path = Path(value).expanduser()
    return (WORKSPACE / path).resolve() if not path.is_absolute() else path.resolve()


def portable_path(path):
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(WORKSPACE))
    except ValueError:
        return str(resolved)


def installed_package_count(status):
    text = status.decode(errors="replace") if isinstance(status, bytes) else status
    return sum(
        1 for paragraph in text.split("\n\n")
        if any(line == "Status: install ok installed" for line in paragraph.splitlines())
    )



def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def command(args, cwd=None, timeout=300):
    environment = {**os.environ, "LC_ALL": "C", "LANG": "C"}
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True,
                            timeout=timeout, env=environment)
    if result.returncode:
        raise RuntimeError(f"{Path(args[0]).name} failed ({result.returncode}): {result.stderr[-3000:]}")
    return result.stdout


def extract_status(rootfs):
    with tarfile.open(rootfs) as archive:
        names = {name.lstrip("./"): name for name in archive.getnames()}
        if "var/lib/dpkg/status" not in names:
            raise ValueError("Rootfs has no dpkg status")
        return archive.extractfile(names["var/lib/dpkg/status"]).read()


def apt_options(lists, cache, sources, status=None, preferences=None):
    options = [
        "-o", f"Dir::State::lists={lists}",
        "-o", f"Dir::Cache={cache}",
        "-o", f"Dir::Etc::sourcelist={sources}",
        "-o", "Dir::Etc::sourceparts=-",
        "-o", "Acquire::Retries=0",
        "-o", "Acquire::Languages=none",
        "-o", f"APT::Architecture={ARCH}",
        "-o", f"APT::Architectures={ARCH}",
    ]
    if status is not None:
        options += ["-o", f"Dir::State::status={status}"]
    if preferences is not None:
        options += ["-o", f"Dir::Etc::preferences={preferences}",
                    "-o", "Dir::Etc::preferencesparts=-"]
    return options


def build_depends_names(build_depends):
    names = []
    for clause in build_depends.split(","):
        clause = clause.split("|", 1)[0].strip()
        if not clause:
            continue
        clause = re.sub(r"\[[^\]]*\]", "", clause)
        clause = re.sub(r"<[^>]*>", "", clause)
        name = re.sub(r"\([^)]*\)", "", clause).strip()
        name = name.split(":", 1)[0]
        if name == "debhelper-compat":
            name = "debhelper"
        if name and name not in names:
            names.append(name)
    if not names:
        raise ValueError("Build-Depends did not contain a package name")
    return names


def parse_installs(simulation):
    pattern = re.compile(r"^Inst (\S+)(?: \[[^\]]+\])? \(([^ ]+) ")
    packages = []
    for line in simulation.splitlines():
        if line.startswith("Remv "):
            raise RuntimeError("APT would remove a package: " + line)
        if not line.startswith("Inst "):
            continue
        match = pattern.match(line)
        if not match:
            raise RuntimeError("Cannot parse APT install line: " + line)
        name, version = match.groups()
        packages.append({"name": name, "version": version})
    return packages


def install_names(build_depends, extra_packages=()):
    names = build_depends_names(build_depends)
    for name in extra_packages:
        require(re.fullmatch(r"[a-z0-9][a-z0-9+.-]+", name), "Invalid extra package name: " + name)
        if name not in names:
            names.append(name)
    return names


def require(condition, message):
    if not condition:
        raise ValueError(message)


def resolve(build_depends, rootfs, sources, output, extra_packages=(), preferences=None):
    require(os.geteuid() != 0, "Run as an unprivileged user; this tool never installs packages")
    rootfs = workspace_path(rootfs)
    sources = workspace_path(sources)
    preferences = workspace_path(preferences) if preferences is not None else None
    output = workspace_path(output)
    require(sources.is_file() and not sources.is_symlink(), "APT sources file is missing")
    require(rootfs.is_file() and not rootfs.is_symlink(), "Rootfs tarball is missing")
    if preferences is not None:
        require(preferences.is_file() and not preferences.is_symlink(),
                "APT preferences file is missing")
    packages_to_install = install_names(build_depends, extra_packages)
    require(output.is_relative_to(WORKSPACE), "Output must stay inside the workspace")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory must be empty: " + str(output))
    output.mkdir(parents=True, exist_ok=True)
    cache = WORKSPACE / "cache"
    cache.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="apt-resolve-", dir=cache) as directory:
        temporary = Path(directory)
        lists, cache = temporary / "lists", temporary / "cache"
        (lists / "partial").mkdir(parents=True)
        (cache / "archives" / "partial").mkdir(parents=True)
        source_copy = temporary / "ubuntu.sources"
        shutil.copyfile(sources, source_copy)
        status_bytes = extract_status(rootfs)
        status_file = temporary / "dpkg-status"
        status_file.write_bytes(status_bytes)

        command(["apt-get", *apt_options(lists, cache, source_copy,
                                         preferences=preferences), "update"], timeout=300)
        simulation = command(
            ["apt-get", *apt_options(lists, cache, source_copy, status_file, preferences),
             "-s", "--no-install-recommends", "install", *packages_to_install],
            timeout=300
        )
        (output / "apt-simulation.log").write_text(simulation)
        selected = parse_installs(simulation)
        require(selected, "APT selected no packages")

        command(
            ["apt-get", *apt_options(lists, cache, source_copy, status_file, preferences),
             "-y", "--download-only", "--no-install-recommends", "install",
             *packages_to_install],
            timeout=900,
        )
        downloads = cache / "archives"
        selected_set = {(item["name"], item["version"]) for item in selected}
        packages = []
        for downloaded in sorted(downloads.glob("*.deb")):
            fields = {}
            for line in command(["dpkg-deb", "-f", str(downloaded),
                                 "Package", "Version", "Architecture"]).splitlines():
                if ": " in line:
                    key, value = line.split(": ", 1)
                    fields[key] = value
            key = (fields.get("Package"), fields.get("Version"))
            if key not in selected_set:
                continue
            require(fields.get("Architecture") in (ARCH, "all"), "Downloaded package architecture mismatch")
            hash_value = digest(downloaded)
            destination = output / hash_value / downloaded.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(downloaded, destination)
            destination.chmod(0o444)
            packages.append({
                "name": fields["Package"],
                "version": fields["Version"],
                "architecture": fields["Architecture"],
                "filename": downloaded.name,
                "sha256": hash_value,
            })
            selected_set.remove(key)
        require(not selected_set, "APT did not download every selected package: " + str(sorted(selected_set)))
        packages.sort(key=lambda entry: entry["name"])

        record = {
            "schema": 1,
            "scope": "current-ubuntu-build-dependencies",
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "architecture": ARCH,
            "build_depends": build_depends,
            "extra_packages": list(extra_packages),
            "sources": {"path": portable_path(sources), "sha256": digest(sources)},
            "preferences": ({"path": portable_path(preferences), "sha256": digest(preferences)}
                            if preferences is not None else None),
            "rootfs": {"path": portable_path(rootfs), "sha256": digest(rootfs),
                       "status_sha256": hashlib.sha256(status_bytes).hexdigest(),
                       "installed_package_count": installed_package_count(status_bytes)},
            "packages": packages,
            "source_evidence": portable_path(output),
        }
        (output / "resolved.json").write_text(json.dumps(record, indent=2) + "\n")
        (output / "Packages.list").write_text(
            "".join(f"{package['sha256']}  {package['filename']}\n" for package in packages)
        )
        return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-depends", required=True,
                        help="Debian Build-Depends string, for example 'debhelper-compat (= 13)'")
    parser.add_argument("--rootfs", type=Path, required=True,
                        help="buildd rootfs tarball used to resolve against its dpkg status")
    parser.add_argument("--sources", type=Path,
                        default=Path("/etc/apt/sources.list.d/ubuntu.sources"))
    parser.add_argument("--preferences", type=Path,
                        help="APT preferences file used to select the SupraLINUX archive")
    parser.add_argument("--extra-packages", nargs="*", default=[],
                        help="additional packages whose closure must be present in the local repository")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = resolve(args.build_depends, args.rootfs, args.sources, args.output,
                     args.extra_packages, args.preferences)
    print(json.dumps({"state": "PASS", "packages": len(record["packages"]),
                      "output": record["source_evidence"]}, indent=2))


if __name__ == "__main__":
    main()
