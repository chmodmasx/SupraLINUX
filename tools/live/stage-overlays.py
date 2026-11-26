"""Stage the three current testing overlays, validating their binary metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OVERLAYS = {
    "supralinux-calamares-config": "all",
    "supralinux-defaults": "all",
    "supralinux-kdeconnect-sftp": "amd64",
}


def metadata(path):
    return tuple(subprocess.check_output(
        ["dpkg-deb", "-f", str(path), field], text=True).strip()
        for field in ("Package", "Version", "Architecture"))


def select(files, versions, inspect=metadata):
    selected = {}
    for path in files:
        package, version, arch = inspect(path)
        if package not in OVERLAYS or package in selected:
            raise ValueError(f"Unexpected or duplicate overlay: {package}")
        if version != versions[package] or arch != OVERLAYS[package]:
            raise ValueError(f"Invalid overlay {package}: {version}/{arch}; expected {versions[package]}/{OVERLAYS[package]}")
        selected[package] = path
    if set(selected) != set(OVERLAYS):
        raise ValueError(f"Missing overlays: {sorted(set(OVERLAYS) - set(selected))}")
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    inventory = json.loads((ROOT / "manifests/packages-1.0.0.json").read_text())
    versions = {entry["source"]: entry["version"] for entry in inventory["packages"]
                if entry["source"] in OVERLAYS}
    if set(versions) != set(OVERLAYS):
        raise ValueError("Missing overlay sources from inventory")
    selected = select(sorted(args.artifacts.rglob("*.deb")), versions)
    args.output.mkdir(parents=True, exist_ok=False)
    report = []
    for name, path in sorted(selected.items()):
        target = args.output / path.name
        shutil.copyfile(path, target)
        target.chmod(0o644)
        report.append({"package": name, "version": versions[name],
                       "architecture": OVERLAYS[name], "file": target.name,
                       "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    (args.output / "overlays.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
