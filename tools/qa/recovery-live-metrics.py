"""Exercise recovery on a disposable VM disk or measure the live session."""
import argparse
import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from package_smoke import wait_agent


ROOT = Path(__file__).resolve().parents[2]
GUEST_SCRIPTS = {"recovery": ROOT / "tools/qa/guest/recovery.sh",
                 "metrics": ROOT / "tools/qa/guest/live-metrics.sh"}


def probe_script(mode):
    return GUEST_SCRIPTS[mode].read_text()


def load_boot():
    spec = importlib.util.spec_from_file_location("live_boot", ROOT / "tools/ci/boot-live.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(args):
    boot = load_boot()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {"scope": args.mode + " on live QA guest", "status": "INFRA_INVALID"}
    proc = qmp = agent = None
    with tempfile.TemporaryDirectory(prefix="supra-qa-") as tmp:
        runtime = Path(tmp)
        try:
            command = boot.command_line(args.iso.resolve(), out, runtime, "uefi")
            if args.mode == "recovery":
                disk = runtime / "rollback.qcow2"
                subprocess.run(["qemu-img", "create", "-f", "qcow2", str(disk), "4G"], check=True)
                command += ["-drive", f"if=none,id=rollback,file={disk},format=qcow2",
                            "-device", "virtio-blk-pci,drive=rollback,serial=SUPRAQA-ROLLBACK"]
            start = time.monotonic()
            with (out / "qemu.log").open("w") as log:
                proc = subprocess.Popen(command, stdout=log, stderr=log)
                qmp = boot.connect_until(runtime / "qmp.sock", proc, time.monotonic() + 30, True)
                report["kvm"] = qmp.call("query-kvm")
                if not all(report["kvm"].get(key) for key in ("present", "enabled")):
                    raise RuntimeError("KVM not enabled")
                report["status"] = "FAIL"
                agent = wait_agent(runtime / "qga.sock", proc, timeout=180)
                deadline = time.monotonic() + 180
                while time.monotonic() < deadline:
                    status = agent.execute("/bin/sh", ["-c", boot.CHECK], timeout=15)
                    if status.get("exitcode") == 0:
                        break
                    time.sleep(5)
                else:
                    raise RuntimeError("Live desktop not ready")
                report["desktop_ready_seconds"] = round(time.monotonic() - start, 2)
                if args.mode == "metrics":
                    time.sleep(30)
                script = probe_script(args.mode)
                if args.recovery_source:
                    if args.mode != "recovery":
                        raise ValueError("Source override is only for recovery QA")
                    import hashlib
                    data = (ROOT / "installer/recovery/supralinux-recover.sh").read_bytes()
                    report["recovery_source_sha256"] = hashlib.sha256(data).hexdigest()
                    # Inject the checked-out helper only into this disposable live guest.
                    agent.put("/tmp/supra-qa-recover.sh", data)
                    prepared = agent.execute("/bin/chmod", ["0700", "/tmp/supra-qa-recover.sh"], timeout=10)
                    if prepared.get("exitcode") != 0:
                        raise RuntimeError("Could not prepare candidate recovery helper")
                    script = "SUPRA_QA_RECOVERY_HELPER=/tmp/supra-qa-recover.sh\nexport SUPRA_QA_RECOVERY_HELPER\n" + script
                result = agent.execute("/bin/sh", ["-c", script], timeout=180)
                for key in ("out-data", "err-data"):
                    report[key] = base64.b64decode(result.get(key, "")).decode(errors="replace")
                report["exitcode"] = result.get("exitcode")
                if result.get("exitcode") != 0:
                    raise RuntimeError("Guest checks failed")
                if args.mode == "recovery" and "ROLLBACK_PASS:" not in report["out-data"]:
                    raise RuntimeError("Missing rollback assertion")
                qmp.call("screendump", {"filename": str(out / "screen.ppm")})
                report["status"] = "PASS"
        except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
            report["error"] = str(exc)
        finally:
            if agent:
                agent.close()
            if qmp:
                qmp.close()
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
    (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--mode", choices=["recovery", "metrics"], required=True)
    parser.add_argument("--recovery-source", action="store_true",
                        help="Test exact checked-out helper in guest instead of ISO copy")
    raise SystemExit(run(parser.parse_args()))
