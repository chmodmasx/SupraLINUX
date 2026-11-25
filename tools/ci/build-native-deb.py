"""Direct native Debian binary build for the supported testing packages.

This is not a clean-build/sbuild certification.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PAYLOAD = {
    "supralinux-defaults": "etc/systemd/zram-generator.conf",
    "supralinux-calamares-config": "etc/calamares/modules/shellprocess_finalvalidation.conf",
}


def command(args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def only_file(directory, pattern):
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1 or not matches[0].is_file():
        raise ValueError(f"Expected exactly one file matching {pattern}: {matches}")
    return matches[0]


def build(package, output):
    source = ROOT / "packages/desktop" / package
    inventory = json.loads((ROOT / "manifests/packages-1.0.0.json").read_text())
    entries = [entry for entry in inventory["packages"] if entry["source"] == package]
    if len(entries) != 1:
        raise ValueError(f"Expected one inventory entry for {package}")
    entry = entries[0]
    if entry["path"] != str(source.relative_to(ROOT)) or entry["binaries"] != [package]:
        raise ValueError(f"Unexpected inventory contract for {package}")
    version = command(["dpkg-parsechangelog", "-SVersion"], cwd=source)
    if version != entry["version"]:
        raise ValueError(f"Changelog {version} differs from inventory {entry['version']}")
    if (source / "debian/source/format").read_text().strip() != "3.0 (native)":
        raise ValueError("Expected native Debian source format")
    subprocess.run(["dpkg-checkbuilddeps"], cwd=source, check=True)
    subprocess.run(["dpkg-buildpackage", "-b", "-us", "-uc"], cwd=source, check=True)
    binary = only_file(source.parent, f"{package}_*.deb")
    for field, expected in (("Package", package), ("Version", version), ("Architecture", "all")):
        actual = command(["dpkg-deb", "-f", str(binary), field])
        if actual != expected:
            raise ValueError(f"{field}: expected {expected}, got {actual}")
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["dpkg-deb", "-x", str(binary), tmp], check=True)
        if not (Path(tmp) / PAYLOAD[package]).is_file():
            raise ValueError(f"Missing payload: {PAYLOAD[package]}")
    artifacts = [binary, only_file(source.parent, f"{package}_*.changes"),
                 only_file(source.parent, f"{package}_*.buildinfo")]
    output.mkdir(parents=True, exist_ok=False)
    for artifact in artifacts:
        shutil.copy2(artifact, output / artifact.name)
    print(f"Verified direct binary build: {package} {version} (not clean-build PASS)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", choices=sorted(PAYLOAD))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.package, args.output.resolve())


if __name__ == "__main__":
    main()
