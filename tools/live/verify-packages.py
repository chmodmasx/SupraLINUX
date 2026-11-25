"""Check a live rootfs against the current SupraLINUX package inventory."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def expected_packages(inventory):
    expected = {}
    for entry in inventory["packages"]:
        if entry.get("test_only"):
            continue
        for binary in entry["binaries"]:
            if binary in expected:
                raise ValueError(f"Duplicate inventory binary: {binary}")
            expected[binary] = entry["version"]
    return expected


def profile_packages(text):
    return {line.split("#", 1)[0].strip() for line in text.splitlines()
            if line.split("#", 1)[0].strip()}


def verify(expected, required, status):
    installed = {}
    errors = []
    for line in status.splitlines():
        name, version, state = line.split("\t")
        if state != "installed" or name not in expected:
            continue
        installed.setdefault(name, set()).add(version)
    for name in sorted(required - installed.keys()):
        errors.append(f"{name}: required inventory package missing")
    for name, versions in sorted(installed.items()):
        if versions != {expected[name]}:
            errors.append(f"{name}: expected {expected[name]}, installed {', '.join(sorted(versions))}")
    return len(installed), errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rootfs", type=Path)
    args = parser.parse_args()
    inventory = json.loads((ROOT / "manifests/packages-1.0.0.json").read_text())
    expected = expected_packages(inventory)
    profile = profile_packages((ROOT / "packages/desktop/desktop-packages.list").read_text())
    required = profile & expected.keys()
    if not required:
        raise SystemExit("Invalid inventory/profile: no required packages")
    admindir = args.rootfs.resolve() / "var/lib/dpkg"
    if not (admindir / "status").is_file():
        raise SystemExit(f"Missing dpkg status database: {admindir}")
    status = subprocess.check_output(
        ["dpkg-query", f"--admindir={admindir}", "-W",
         "-f=${Package}\\t${Version}\\t${db:Status-Status}\\n"], text=True)
    count, errors = verify(expected, required, status)
    for error in errors:
        print(error)
    if errors:
        raise SystemExit("ISO package contract failed; rebuild or stage the current packages")
    print(f"ISO package contract: {count} installed inventory binaries match; {len(required)} required")


if __name__ == "__main__":
    main()
