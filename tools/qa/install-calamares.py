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
from installer_ui import click, key, field, page, crop_digest, welcome_ready

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


def prepare_welcome(qmp, agent, output):
    """Focus the real installer only after its asynchronous requirements finish."""
    wait_ready(agent, "grep -q 'All requirements have been checked' /tmp/supra-qa-calamares.log", 90)
    expect_page(qmp, output, "welcome", 90)
    # The first failed run showed plasma-welcome over Calamares. A neutral
    # area outside that window and all controls was verified in the artifacts.
    # Never click Next to acquire focus or when readiness is ambiguous.
    for attempt in range(1, 4):
        before = frame(qmp, output, f"welcome-before-focus-{attempt}")
        if page(before) != "welcome":
            raise RuntimeError("Unexpected page before installer focus")
        click(qmp, 1150, 100)
        time.sleep(2)
        after = frame(qmp, output, f"welcome-after-focus-{attempt}")
        if page(after) != "welcome":
            raise RuntimeError("Unexpected page after neutral focus click")
        if welcome_ready(after):
            time.sleep(2)
            if welcome_ready(frame(qmp, output, "welcome-ready")):
                return
    raise RuntimeError("Calamares welcome not visibly ready after bounded focus attempts")


def select_storage(qmp, agent, output, scenario):
    """Choose the reviewed storage controls on a disposable disk."""
    click(qmp, 206, 71)
    time.sleep(4)
    frame(qmp, output, "partition-selected")
    checked(agent, "grep -q 'InstallChoice Config::Erase' /tmp/supra-qa-calamares.log")
    if scenario == "ext4":
        # The pinned partition.conf lists exactly btrfs then ext4.
        click(qmp, 510, 128)
        time.sleep(1)
        frame(qmp, output, "filesystem-options")
        key(qmp, "end")
        key(qmp, "ret")
        time.sleep(3)
        frame(qmp, output, "partition-ext4")
    elif scenario == "luks2":
        click(qmp, 206, 550)
        time.sleep(3)
        frame(qmp, output, "partition-encryption")
        field(qmp, 450, 550, PASSWORD)
        field(qmp, 780, 550, PASSWORD)
        click(qmp, 1100, 510)
        time.sleep(2)
        frame(qmp, output, "partition-encryption-filled")


def install(args):
    boot = load_boot()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {"scope": "Calamares transaction", "scenario": args.scenario, "status": "INFRA_INVALID",
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
                prepare_welcome(qmp, agent, output)
                report["welcome_ready"] = True
                for step in ("location", "keyboard", "partition"):
                    click(qmp, 1136, 736)
                    expect_page(qmp, output, step)
                select_storage(qmp, agent, output, args.scenario)
                report["partition_disk"] = checked(agent, guard)
                click(qmp, 1136, 736)
                expect_page(qmp, output, "users")
                field(qmp, 300, 50, USER)
                field(qmp, 300, 110, USER)
                field(qmp, 300, 170, "supraqatest")
                field(qmp, 300, 230, PASSWORD)
                field(qmp, 500, 230, PASSWORD)
                click(qmp, 1100, 320)
                time.sleep(2)
                frame(qmp, output, "users-filled")
                click(qmp, 1136, 736)
                expect_page(qmp, output, "summary")
                report["summary_disk"] = checked(agent, guard)
                filesystem = "ext4" if args.scenario == "ext4" else "btrfs"
                checked(agent, "grep -A1 'mountPoint: :.*\"/\"' /tmp/supra-qa-calamares.log | grep -q 'fs: :.*\"" + filesystem + "\"'")
                report["planned_root_filesystem"] = filesystem
                if args.scenario == "luks2":
                    checked(agent, "grep -A1 'mountPoint: :.*\"/boot\"' /tmp/supra-qa-calamares.log | grep -q 'fs: :.*\"ext4\"'")
                    checked(agent, "grep -q 'fsName :.*\"luks2\"' /tmp/supra-qa-calamares.log")
                    report["planned_separate_boot"] = True
                    # Reviewed partition summary region excludes the panel clock.
                    if crop_digest(output / "summary.ppm", 235, 291, 1034, 337) != "fe6b90835b472a986fc54448a45fbfc210ba3507c25f20671a8e705a7649dd30":
                        raise RuntimeError("Encrypted partition summary differs from reviewed plan")
                before = crop_digest(output / "summary.ppm", 250, 150, 780, 480)
                click(qmp, 1136, 736)
                time.sleep(3)
                dialog = frame(qmp, output, "confirmation")
                if crop_digest(dialog, 250, 150, 780, 480) == before:
                    raise RuntimeError("No visible confirmation dialog transition")
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
                    report["installed_disk"] = checked(agent, "grep -q 'Installation finished. No error reported.' /tmp/supra-qa-calamares.log; sync; test -b /dev/vda1; test -b /dev/vda2; lsblk -o NAME,FSTYPE,SERIAL /dev/vda")
                    if args.scenario == "luks2":
                        report["luks_layout"] = checked(agent,
                            "test \"$(lsblk -dn -o FSTYPE /dev/vda1)\" = vfat && "
                            "test \"$(lsblk -dn -o FSTYPE /dev/vda2)\" = ext4 && "
                            "cryptsetup isLuks --type luks2 /dev/vda3 && "
                            "lsblk -o NAME,FSTYPE,SERIAL /dev/vda")
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
        if ready_for_boot and args.scenario == "luks2":
            result = subprocess.run([sys.executable, str(ROOT / "tools/qa/boot-encrypted-discovery.py"),
                str(disk), str(output / "unlock"), "--firmware-vars", str(runtime / "OVMF_VARS.fd")], check=False)
            report["unlock_discovery_exitcode"] = result.returncode
            report["status"] = "UNLOCK_DISCOVERY_READY" if result.returncode == 0 else "FAIL"
        elif ready_for_boot:
            result = subprocess.run([sys.executable, str(ROOT / "tools/qa/boot-installed.py"),
                str(disk), str(output / "installed"), "--mode", "uefi",
                "--firmware-vars", str(runtime / "OVMF_VARS.fd"), "--filesystem", filesystem,
                "--user", USER, "--live-machine-id", live_id, "--verify-greeter"], check=False)
            report["installed_exitcode"] = result.returncode
            report["status"] = "PASS" if result.returncode == 0 else "FAIL"
    (output / "result.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] in ("PREVIEW_READY", "UNLOCK_DISCOVERY_READY", "PASS") else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--confirm", nargs=7, metavar=("X", "Y", "LEFT", "TOP", "WIDTH", "HEIGHT", "SHA256"))
    parser.add_argument("--scenario", choices=["btrfs", "ext4", "luks2"], default="btrfs")
    args = parser.parse_args()
    raise SystemExit(install(args))
