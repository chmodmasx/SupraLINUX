"""Exercise the real Calamares installer on a single disposable disk.

Preview mode reaches and captures the final confirmation dialog; no writes
are authorized. Commit mode requires a reviewed button crop and coordinate,
then checks the actual target disk and runs the installed-system harness.
"""
import argparse
import base64
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from package_smoke import wait_agent
from installer_ui import click, key, field, page, crop_digest

ROOT = Path(__file__).resolve().parents[2]
GUEST = Path(__file__).resolve().parent / "guest"
USER = "supraqa"
PASSWORD = "qadisposable2026"


def load_boot():
    spec = importlib.util.spec_from_file_location("boot_live", ROOT / "tools/ci/boot-live.py")
    boot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(boot)
    return boot


def guest(agent, command, timeout=30):
    result = agent.execute("/bin/sh", ["-c", command], timeout=timeout)
    return {"exitcode": result.get("exitcode"),
            "stdout": base64.b64decode(result.get("out-data", "")).decode(errors="replace"),
            "stderr": base64.b64decode(result.get("err-data", "")).decode(errors="replace")}


def checked(agent, script):
    result = guest(agent, script)
    if result["exitcode"] != 0:
        raise RuntimeError(f"Guest assertion failed: {result}")
    return result["stdout"]


def frame(qmp, output, name):
    path = output / (name + ".ppm")
    qmp.call("screendump", {"filename": str(path)})
    return path


def expect_page(qmp, output, expected, seconds=30):
    deadline = time.monotonic() + seconds
    last = "no frame"
    while time.monotonic() < deadline:
        try:
            last = page(frame(qmp, output, expected))
            if last == expected:
                return
        except ValueError as exc:
            last = str(exc)
        time.sleep(2)
    raise RuntimeError(f"Expected page {expected}; observed {last}")


def wait_ready(agent, script, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if guest(agent, script)["exitcode"] == 0:
            return
        time.sleep(3)
    raise RuntimeError("Guest readiness timeout")


def install(args):
    boot = load_boot()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {"scope": "Calamares Btrfs transaction", "status": "INFRA_INVALID",
              "mode": "commit" if args.confirm else "preview"}
    proc = qmp = agent = None
    with tempfile.TemporaryDirectory(prefix="supra-install-") as tmp:
        runtime = Path(tmp)
        disk = runtime / "target.qcow2"
        live_id = None
        ready_for_boot = False
        try:
            subprocess.run(["qemu-img", "create", "-f", "qcow2", str(disk), "40G"], check=True)
            cmd = boot.command_line(args.iso.resolve(), output, runtime, "uefi")
            cmd += ["-drive", f"if=none,id=target,format=qcow2,file={disk}",
                    "-device", "virtio-blk-pci,drive=target,serial=SUPRAQA-INSTALL",
                    "-device", "qemu-xhci", "-device", "usb-tablet"]
            with (output / "qemu.log").open("w") as log:
                proc = subprocess.Popen(cmd, stdout=log, stderr=log)
                qmp = boot.connect_until(runtime / "qmp.sock", proc, time.monotonic()+30, True)
                report["kvm"] = qmp.call("query-kvm")
                if not all(report["kvm"].get(k) for k in ("enabled", "present")):
                    raise RuntimeError("KVM disabled")
                report["status"] = "FAIL"
                agent = wait_agent(runtime / "qga.sock", proc, timeout=180)
                wait_ready(agent, boot.CHECK, 180)
                live_id = checked(agent, "cat /etc/machine-id").strip()
                guard = (GUEST / "installer-disk-guard.sh").read_text()
                report["initial_disk"] = checked(agent, guard)
                checked(agent, (GUEST / "launch-calamares.sh").read_text())
                expect_page(qmp, output, "welcome", 90)
                for step in ("location", "keyboard", "partition"):
                    click(qmp, 1136, 736)
                    expect_page(qmp, output, step)
                click(qmp, 206, 71)
                time.sleep(4)
                frame(qmp, output, "partition-selected")
                checked(agent, "grep -q 'InstallChoice Config::Erase' /tmp/supra-qa-calamares.log")
                report["partition_disk"] = checked(agent, guard)
                click(qmp, 1136, 736)
                expect_page(qmp, output, "users")
                field(qmp, 300, 50, USER)
                field(qmp, 300, 110, USER)
                field(qmp, 300, 170, "supraqatest")
                field(qmp, 300, 230, PASSWORD)
                field(qmp, 500, 230, PASSWORD)
                click(qmp, 1136, 736)
                expect_page(qmp, output, "summary")
                report["summary_disk"] = checked(agent, guard)
                click(qmp, 1136, 736)
                time.sleep(3)
                dialog = frame(qmp, output, "confirmation")
                # Preserve the final confirmation for review, without committing.
                if not args.confirm:
                    report["preview_disk"] = checked(agent, guard)
                    report["status"] = "PREVIEW_READY"
                else:
                    x, y, left, top, width, height = map(int, args.confirm[:6])
                    expected = args.confirm[6]
                    if not (left <= x < left+width and top <= y < top+height):
                        raise ValueError("Confirmation click must be within reviewed crop")
                    if crop_digest(dialog, left, top, width, height) != expected:
                        raise RuntimeError("Confirmation dialog crop changed; refusing installation")
                    checked(agent, guard)
                    click(qmp, x, y)
                    expect_page(qmp, output, "install", 45)
                    expect_page(qmp, output, "finished", 1800)
                    # A completed GUI alone is insufficient; inspect the disk and boot it.
                    checked(agent, "sync; test -b /dev/vda1; test -b /dev/vda2; lsblk -o NAME,FSTYPE,SERIAL /dev/vda")
                    report["status"] = "INSTALL_FINISHED"
                    ready_for_boot = True
        except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
            report["error"] = str(exc)
        finally:
            if agent:
                try:
                    (output / "calamares.log").write_bytes(agent.get("/tmp/supra-qa-calamares.log", limit=8*1024*1024))
                except (OSError, RuntimeError, ValueError) as exc:
                    report["log_error"] = str(exc)
                agent.close()
            if qmp:
                try:
                    frame(qmp, output, "last")
                except (OSError, RuntimeError, ValueError) as exc:
                    report["frame_error"] = str(exc)
                qmp.close()
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        if ready_for_boot:
            result = subprocess.run([sys.executable, str(ROOT / "tools/qa/boot-installed.py"),
                str(disk), str(output / "installed"), "--mode", "uefi",
                "--firmware-vars", str(runtime / "OVMF_VARS.fd"), "--filesystem", "btrfs",
                "--user", USER, "--live-machine-id", live_id], check=False)
            report["installed_exitcode"] = result.returncode
            report["status"] = "PASS" if result.returncode == 0 else "FAIL"
    (output / "result.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] in ("PREVIEW_READY", "PASS") else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--confirm", nargs=7, metavar=("X", "Y", "LEFT", "TOP", "WIDTH", "HEIGHT", "SHA256"))
    args = parser.parse_args()
    raise SystemExit(install(args))
