#!/usr/bin/env python3
"""Exercise one signed local package repository inside an owned offline guest."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


def run(command, expected=0):
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=120,
                            env={**os.environ, "LC_ALL": "C", "DEBIAN_FRONTEND": "noninteractive"})
    print("COMMAND", json.dumps(command), flush=True)
    print(result.stdout, flush=True)
    if expected == 0 and result.returncode != 0:
        raise RuntimeError(f"Guest command failed: {command[0]} ({result.returncode})")
    return result


def apt_options(root, repository, label):
    lists = root / "apt" / label / "lists"
    (lists / "partial").mkdir(parents=True)
    sources = root / "apt" / (label + ".list")
    sources.write_text(f"deb [signed-by={root}/archive-key.gpg] file:{repository} ./\n")
    return ["apt-get", "-o", f"Dir::Etc::sourcelist={sources}",
            "-o", "Dir::Etc::sourceparts=-", "-o", f"Dir::State::lists={lists}",
            "-o", "Acquire::Retries=0", "-o", "Acquire::Languages=none",
            "-o", "DPkg::Lock::Timeout=30",
            "-o", "Acquire::AllowInsecureRepositories=false",
            "-o", "Acquire::AllowDowngradeToInsecureRepositories=false"]


def main():
    root = Path("/run/supralinux-package-smoke")
    manifest = json.loads((root / "manifest.json").read_text())
    if os.geteuid() != 0:
        raise RuntimeError("This probe requires the owned guest's root account, never host execution")
    virtualization = run(["systemd-detect-virt", "--vm"]).stdout.strip()
    os_release = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
    if virtualization != "kvm" or os_release.get("ID", "").strip('"') != "ubuntu" or os_release.get("VERSION_ID", "").strip('"') != "26.04":
        raise RuntimeError("Disposable Ubuntu 26.04 KVM guest required")
    interfaces = sorted(path.name for path in Path("/sys/class/net").iterdir())
    if interfaces != ["lo"]:
        raise RuntimeError("This probe must have zero network interfaces, except loopback")
    name, version = manifest["package"], manifest["version"]
    before = run(["dpkg-query", "-W", "-f=${Status}", name], expected=None)
    if before.returncode == 0 and before.stdout == "install ok installed":
        raise RuntimeError("Base already contains the candidate package")
    options = apt_options(root, root / "repository", "valid")
    run(options + ["update"])
    requested = manifest.get("install_packages", [f"{name}={version}"])
    run(options + ["install", "-y", "--no-install-recommends", *requested])
    for spec in requested:
        package, _, expected_version = spec.partition("=")
        identity = run(["dpkg-query", "-W", "-f=${Package}\n${Version}\n${Architecture}\n", package]).stdout.splitlines()
        expected_architecture = manifest["architecture"] if package == name else None
        if identity[:2] != [package, expected_version]:
            raise RuntimeError("Installed package identity does not match the request: " + package)
        if expected_architecture and identity[2] != expected_architecture:
            raise RuntimeError("Installed package architecture does not match: " + package)
    hashes = {}
    for filename, expected in manifest["installed_files"].items():
        path = Path(filename)
        if path.is_symlink():
            raise RuntimeError("Installed payload must not be a symlink")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError("Installed payload differs from original source: " + filename)
        hashes[filename] = actual
    smoke = ["bash", str(root / "smoke")]
    run(smoke)
    negative_spec = manifest.get("negative_test", {})
    if not negative_spec.get("path"):
        raise RuntimeError("The smoke manifest must define a negative test path")
    data = Path(negative_spec["path"])
    hidden = data.with_name(data.name + negative_spec.get("suffix", ".hidden-for-smoke"))
    if hidden.exists():
        raise RuntimeError("Unexpected negative-test residue")
    data.rename(hidden)
    try:
        negative = run(smoke, expected=None)
        if negative.returncode == 0:
            raise RuntimeError("Smoke accepted a missing runtime payload")
    finally:
        hidden.rename(data)
    run(smoke)
    if hashlib.sha256(data.read_bytes()).hexdigest() != manifest["installed_files"][str(data)]:
        raise RuntimeError("Negative test did not restore the original payload")
    tampered = root / "tampered-repository"
    tampered.mkdir()
    for item in (root / "repository").iterdir():
        target = tampered / item.name
        if item.name in {"Packages", "Packages.gz", "Release", "Release.gpg", "InRelease"}:
            shutil.copyfile(item, target)
        else:
            os.link(item, target)
    for filename in ["Packages", "Packages.gz"]:
        path = tampered / filename
        raw = path.read_bytes()
        path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    rejected = run(apt_options(root, tampered, "tampered") + ["update"], expected=None)
    if rejected.returncode == 0 or not any(text in rejected.stdout for text in ["Hash Sum mismatch", "File has unexpected size"]):
        raise RuntimeError("APT did not reject the modified index for the expected integrity reason")
    run(["apt-get", "check"])
    result = {
        "schema": 1, "state": "PASS", "scope": manifest["scope"],
        "package": name, "version": version, "architecture": manifest["architecture"],
        "virtualization": virtualization, "interfaces": interfaces,
        "signed_local_apt_install": "PASS", "installed_files_sha256": hashes,
        "original_smoke": "PASS", "missing_payload_rejected": True,
        "tampered_index_rejected": True, "sbuild_invoked": False,
        "new_package_build_certification": False,
    }
    (root / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
