"""Collect offline first-boot evidence for the reviewed disposable LUKS2 installation."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(args):
    boot = load(ROOT / "tools/ci/boot-live.py", "boot_live")
    installed = load(ROOT / "tools/qa/boot-installed.py", "boot_installed")
    disk = args.disk.resolve(strict=True)
    installed.verify_disk(disk)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {"status": "INFRA_INVALID", "scope": "encrypted disk-only boot screenshot discovery, not verified unlock"}
    proc = qmp = None
    with tempfile.TemporaryDirectory(prefix="supra-unlock-") as tmp:
        runtime = Path(tmp)
        try:
            cmd = installed.command_line(disk, out, runtime, "uefi", args.firmware_vars)
            (out / "qemu-command.json").write_text(json.dumps(cmd, indent=2))
            with (out / "qemu.log").open("w") as log:
                proc = subprocess.Popen(cmd, stdout=log, stderr=log)
                qmp = boot.connect_until(runtime / "qmp.sock", proc, time.monotonic()+30, True)
                report["kvm"] = qmp.call("query-kvm")
                if not all(report["kvm"].get(k) for k in ("enabled", "present")):
                    raise RuntimeError("KVM unavailable")
                report["status"] = "FAIL"
                report["frames"] = []
                start = time.monotonic()
                for target in (5, 10, 20, 30, 45, 60):
                    while time.monotonic()-start < target:
                        if proc.poll() is not None:
                            raise RuntimeError("Guest exited before screenshot")
                        time.sleep(0.5)
                    frame = out / f"boot-{target:02d}.ppm"
                    qmp.call("screendump", {"filename": str(frame)})
                    report["frames"].append({"seconds": target, **installed.visible_frame(frame)})
                # Only evidence collection is successful; no assertion about
                # prompt semantics or root unlock until screenshots are reviewed.
                report["status"] = "UNLOCK_DISCOVERY_READY"
        except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
            report["error"] = str(exc)
        finally:
            if qmp:
                qmp.close()
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
    (out / "result.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "UNLOCK_DISCOVERY_READY" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("disk", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--firmware-vars", type=Path, required=True)
    raise SystemExit(run(parser.parse_args()))
