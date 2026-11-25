"""Select expensive CI jobs from the exact tree delta; unknown delta runs all."""
import os
import subprocess
from pathlib import PurePosixPath

JOBS = ("kdeconnect", "kvm")


def classify(paths):
    selected = set()
    for name in paths:
        if name.startswith((".github/", "tools/ci/")) or name in ("Makefile", "tests/test_ci_routing.py"):
            return set(JOBS)
        if name.startswith("packages/") and any(
            part.startswith(("kdeconnect", "supralinux-kdeconnect"))
            for part in PurePosixPath(name).parts
        ):
            selected.add("kdeconnect")
        if name.startswith(("tests/test_kdeconnect", "tools/clean_build", "tools/guest_clean_build", "tools/resolve_build_deps")):
            selected.add("kdeconnect")
        if name.startswith(("tools/live/", "tools/iso", "tools/vm", "tools/qemu", "tools/clean_build", "tools/guest_clean_build", "tools/package_smoke", "installer/", "packages/desktop/supralinux-calamares-config/")):
            selected.add("kvm")
    return selected


def plan(event, base, head):
    if event not in ("push", "pull_request") or not base or not head:
        return set(JOBS), "full: manual or missing comparison"
    try:
        # Compare complete trees, including renamed/deleted paths. Never truncate.
        raw = subprocess.check_output(
            ["git", "diff", "--no-renames", "--name-only", "-z", base, head, "--"],
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError:
        return set(JOBS), "full: comparison unavailable"
    paths = os.fsdecode(raw).split("\0")
    return classify(p for p in paths if p), "changed paths"


def main():
    selected, reason = plan(
        os.environ.get("GITHUB_EVENT_NAME"),
        os.environ.get("CI_BASE_SHA"),
        os.environ.get("GITHUB_SHA"),
    )
    print(f"CI routing: {reason}; selected={sorted(selected)}", flush=True)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
        for job in JOBS:
            out.write(f"{job}={str(job in selected).lower()}\n")


if __name__ == "__main__":
    main()
