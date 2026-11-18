#!/usr/bin/env python3
"""Generate the source-package inventory for a SupraLINUX release."""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AREAS = {
    "kde": "Frameworks",
    "plasma": "Plasma",
    "gear": "Gear",
    "gear-extras": "Gear extras",
    "desktop": "Desktop",
    "apps": "Apps",
    "fonts": "Fonts",
    "system": "System",
}
EXCLUDE = {"supralinux-build-test"}


def command(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE).strip()


def package_dirs():
    for area in AREAS:
        base = ROOT / "packages" / area
        if not base.is_dir():
            continue
        for package in sorted(base.iterdir()):
            if package.is_dir() and (package / "debian/control").is_file():
                yield area, package


def control_binaries(control):
    binaries = []
    for line in control.read_text(errors="ignore").splitlines():
        if line.startswith("Package:"):
            name = line.split(":", 1)[1].strip()
            if name and not name.startswith("${"):
                binaries.append(name)
    return binaries


def copyright_licenses(copyright):
    licenses = []
    for line in copyright.read_text(errors="ignore").splitlines():
        if line.startswith("License:"):
            value = line.split(":", 1)[1].strip()
            if value and value not in licenses:
                licenses.append(value)
    return licenses


def inventory(include_test=False):
    packages = []
    for area, package in package_dirs():
        changelog = package / "debian/changelog"
        source = command(["dpkg-parsechangelog", "-l", str(changelog), "-SSource"])
        version = command(["dpkg-parsechangelog", "-l", str(changelog), "-SVersion"])
        if source in EXCLUDE and not include_test:
            continue
        packages.append({
            "source": source,
            "version": version,
            "area": area,
            "path": str(package.relative_to(ROOT)),
            "binaries": control_binaries(package / "debian/control"),
            "licenses": copyright_licenses(package / "debian/copyright"),
            "test_only": source in EXCLUDE,
        })
    packages.sort(key=lambda item: (item["area"], item["source"]))
    counts = {area: sum(1 for item in packages if item["area"] == area) for area in AREAS}
    return {
        "schema": 1,
        "scope": "source-inventory",
        "product": "SupraLINUX",
        "version": "1.0.0",
        "codename": "Aurora",
        "status": "packaging",
        "areas": counts,
        "packages": packages,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "manifests/packages-1.0.0.json")
    parser.add_argument("--check", action="store_true",
                        help="fail if the output file is not the current inventory")
    parser.add_argument("--include-test", action="store_true",
                        help="include the synthetic build-test package")
    args = parser.parse_args()

    output = args.output if args.output.is_absolute() else ROOT / args.output
    data = inventory(args.include_test)
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not output.is_file() or output.read_text() != text:
            raise SystemExit(f"{output}: source inventory is out of date")
        print(f"{output}: {len(data['packages'])} packages, inventory is current")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text)
    print(f"{output}: {len(data['packages'])} packages")


if __name__ == "__main__":
    main()
