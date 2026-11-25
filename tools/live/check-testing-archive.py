"""Inspect the signed testing archive without changing host APT configuration."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def expected_versions(inventory):
    result = {}
    for package in inventory["packages"]:
        if package.get("test_only"):
            continue
        for binary in package["binaries"]:
            if binary in result:
                raise ValueError(f"Duplicate binary in inventory: {binary}")
            result[binary] = package["version"]
    return result


def parse_madison(text):
    versions = {}
    for line in text.splitlines():
        name, version, _ = (field.strip() for field in line.split("|", 2))
        versions.setdefault(name, set()).add(version)
    return versions


def archive_report(expected, profile, available):
    gaps = []
    for name, version in sorted(expected.items()):
        actual = sorted(available.get(name, set()))
        if version not in actual:
            gaps.append({"package": name, "expected": version,
                         "available": actual, "desktop_profile": name in profile})
    return {"status": "BLOCKED" if gaps else "PASS",
            "scope": "signed testing archive versions only",
            "inventory_binaries": len(expected),
            "matching_binaries": len(expected) - len(gaps),
            "desktop_profile_gaps": sum(gap["desktop_profile"] for gap in gaps),
            "gaps": gaps}


def probe(root):
    inventory = json.loads((root / "manifests/packages-1.0.0.json").read_text())
    expected = expected_versions(inventory)
    profile = {line.split("#", 1)[0].strip()
               for line in (root / "packages/desktop/desktop-packages.list").read_text().splitlines()}
    if not expected or not (profile & expected.keys()):
        raise ValueError("Empty inventory/profile")
    source = (root / "installer/apt/supralinux-testing.sources").read_text()
    key = root / "installer/keys/supralinux-archive-key.asc"
    if not key.is_file():
        raise ValueError("Missing checked-in archive public key")
    old = "Signed-By: /usr/share/keyrings/supralinux-archive-key.asc"
    if source.count(old) != 1 or "Suites: testing" not in source.splitlines():
        raise ValueError("Unexpected testing source contract")
    with tempfile.TemporaryDirectory(prefix="supra-archive-") as directory:
        tmp = Path(directory)
        (tmp / "lists" / "partial").mkdir(parents=True)
        (tmp / "cache" / "archives" / "partial").mkdir(parents=True)
        sources = tmp / "testing.sources"
        sources.write_text(source.replace(old, f"Signed-By: {key}"))
        config = tmp / "apt.conf"
        config.write_text(
            'Dir::Etc::parts "-";\nDir::Etc::main "-";\n'
            f'Dir::Etc::sourcelist "{sources}";\nDir::Etc::sourceparts "-";\n'
            f'Dir::State::lists "{tmp / "lists"}";\nDir::State::status "/dev/null";\n'
            f'Dir::Cache "{tmp / "cache"}";\n'
            'Dir::Cache::pkgcache "";\nDir::Cache::srcpkgcache "";\n'
            'APT::Architecture "amd64";\nAPT::Architectures { "amd64"; };\n'
            'Acquire::Languages "none";\nAcquire::Retries "1";\n'
            'Acquire::http::Timeout "30";\nAcquire::https::Timeout "30";\n'
            'APT::Update::Error-Mode "any";\n'
        )
        env = {**os.environ, "APT_CONFIG": str(config), "LC_ALL": "C"}
        subprocess.run(["apt-get", "update"], env=env, check=True, timeout=180)
        output = subprocess.check_output(
            ["apt-cache", "madison", *sorted(expected)], env=env, text=True, timeout=60)
        return archive_report(expected, profile, parse_madison(output))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        report = probe(ROOT)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        report = {"status": "INFRA_INVALID", "error": str(exc),
                  "scope": "signed testing archive versions only"}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "gaps"}, indent=2))
    if report["status"] == "INFRA_INVALID":
        raise SystemExit(1)
    # A valid diagnostic can identify missing versions without certifying ISO readiness.
    if report["status"] == "BLOCKED":
        print("::warning::BLOCKED: archive lacks current inventory versions; see JSON report")


if __name__ == "__main__":
    main()
