#!/usr/bin/env python3
"""Run the pinned 1.0.0 clean-build set sequentially and resumably.

This is a thin orchestrator: each package still runs through
``tools/clean_build.py`` and keeps its own evidence, artifact and cleanup
report.  The orchestrator only records progress outside Git so the source
tree stays clean while the batch runs.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = Path(os.environ.get("SUPRALINUX_WORKSPACE", ROOT.parent / "SupraLINUX-workspace")).expanduser().resolve()
STATE_SCHEMA = 1


def workspace_path(value):
    path = Path(value).expanduser()
    return (WORKSPACE / path).resolve() if not path.is_absolute() else path.resolve()


def digest(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    temporary.replace(path)


def parse_result(output):
    """Return the JSON object printed by clean_build, if present."""
    text = output.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.rfind("\n{")
    if start == -1:
        return None
    try:
        return json.loads(text[start + 1:])
    except json.JSONDecodeError:
        return None


def artifact_is_retained(entry):
    artifact = entry.get("artifact") or {}
    path = artifact.get("path")
    expected = artifact.get("sha256")
    if not path or not expected:
        return False
    target = workspace_path(path)
    return target.is_file() and digest(target) == expected


def manifest_version(path):
    return read_json(path).get("version")


def package_state(previous, manifest):
    state = dict(previous or {})
    state.update({
        "manifest": str(Path(manifest).resolve().relative_to(ROOT)),
        "manifest_sha256": digest(manifest),
        "version": manifest_version(manifest),
    })
    return state


def run_one(manifest, log_path):
    started = time.monotonic()
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools/clean_build.py"), "--manifest", str(manifest)],
        cwd=ROOT, text=True, capture_output=True, timeout=4 * 60 * 60,
    )
    seconds = round(time.monotonic() - started, 3)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "$ clean_build.py --manifest " + str(manifest) + "\n"
        + completed.stdout
        + ("\n--- stderr ---\n" + completed.stderr if completed.stderr else "")
    )
    result = parse_result(completed.stdout)
    if result is None:
        return {
            "state": "INFRA_INVALID",
            "error": f"clean_build produced no JSON (exit {completed.returncode})",
            "timings_seconds": {"total": seconds},
        }
    result.setdefault("timings_seconds", {})["orchestrator_total"] = seconds
    if completed.returncode != 0 and result.get("state") == "PASS":
        result["state"] = "INFRA_INVALID"
        result["error"] = "clean_build exited non-zero after reporting PASS"
    return result


def summarize(packages, order):
    counts = {}
    for source in order:
        state = (packages.get(source) or {}).get("state", "PENDING")
        counts[state] = counts.get(state, 0) + 1
    return {
        "total": len(order),
        "pass": counts.get("PASS", 0),
        "fail": counts.get("FAIL", 0),
        "infra_invalid": counts.get("INFRA_INVALID", 0),
        "pending": counts.get("PENDING", 0),
        "by_state": counts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifests-dir", type=Path, default=ROOT / "manifests/release-1.0.0")
    parser.add_argument("--state", type=Path,
                        default=WORKSPACE / "state/full-build-1.0.0.json")
    parser.add_argument("--package", action="append", default=[])
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--max-consecutive-infra", type=int, default=3)
    args = parser.parse_args()

    if os.geteuid() == 0:
        raise SystemExit("Run as the unprivileged KVM user, not root")
    if subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True).strip():
        raise SystemExit("Commit the pinned manifests before starting the batch")
    manifests_dir = args.manifests_dir if args.manifests_dir.is_absolute() else ROOT / args.manifests_dir
    manifests = sorted(manifests_dir.glob("*.json"))
    if not manifests:
        raise SystemExit("No manifests found")
    inventory = read_json(ROOT / "manifests/packages-1.0.0.json")
    order = [entry["source"] for entry in inventory["packages"]]
    by_source = {path.stem: path for path in manifests}
    missing = [source for source in order if source not in by_source]
    if missing:
        raise SystemExit("Missing manifests: " + ", ".join(missing))
    selected = [source for source in order if not args.package or source in args.package]

    state_path = args.state if args.state.is_absolute() else workspace_path(args.state)
    state = read_json(state_path) if state_path.exists() else {
        "schema": STATE_SCHEMA,
        "scope": "full-clean-build-run",
        "product": "SupraLINUX",
        "version": "1.0.0",
        "codename": "Aurora",
        "started_at": now(),
        "packages": {},
    }
    state.setdefault("packages", {})
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = WORKSPACE / "evidence/full-build" / run_id

    lock_path = WORKSPACE / "cache/full-build.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("BLOCKED: another full-release build owns the execution slot")

        consecutive_infra = 0
        for index, source in enumerate(selected, 1):
            manifest = by_source[source]
            previous = state["packages"].get(source) or {}
            manifest_current = previous.get("manifest_sha256") == digest(manifest)
            if previous.get("state") == "PASS" and manifest_current and artifact_is_retained(previous):
                print(f"[{index}/{len(selected)}] {source}: PASS retained", flush=True)
                continue
            print(f"[{index}/{len(selected)}] {source}: building", flush=True)
            try:
                result = run_one(manifest, log_dir / f"{source}.log")
            except subprocess.TimeoutExpired:
                result = {"state": "INFRA_INVALID", "error": "orchestrator timeout"}
            entry = package_state(previous, manifest)
            entry.update({
                "state": result.get("state", "INFRA_INVALID"),
                "evidence": result.get("evidence"),
                "artifact": result.get("artifact"),
                "error": result.get("error"),
                "timings_seconds": result.get("timings_seconds", {}),
                "finished_at": now(),
            })
            entry["cleanup"] = result.get("cleanup")
            state["packages"][source] = entry
            state["updated_at"] = now()
            state["last_run_log_dir"] = str(log_dir.relative_to(WORKSPACE))
            state["summary"] = summarize(state["packages"], order)
            write_json(state_path, state)
            print(f"[{index}/{len(selected)}] {source}: {entry['state']}"
                  + (f" ({entry['error']})" if entry.get("error") else ""), flush=True)
            if entry["state"] == "INFRA_INVALID":
                consecutive_infra += 1
            else:
                consecutive_infra = 0
            if entry["state"] != "PASS" and args.stop_on_fail:
                break
            if consecutive_infra >= args.max_consecutive_infra:
                print("Stopping after consecutive infrastructure failures", flush=True)
                break

    state["finished_at"] = now() if len(state["packages"]) == len(order) else None
    state["summary"] = summarize(state["packages"], order)
    write_json(state_path, state)
    print(json.dumps(state["summary"], indent=2), flush=True)
    return 0 if state["summary"]["fail"] == 0 and state["summary"]["infra_invalid"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
