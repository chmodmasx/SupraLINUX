"""Boot a disposable installed disk without ISO and run the installed guest contract."""
import argparse
import base64
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from package_smoke import wait_agent

ROOT = Path(__file__).resolve().parents[2]


def verify_disk(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("Expected a regular disposable qcow2 file")
    info = json.loads(subprocess.check_output(
        ["qemu-img", "info", "--output=json", str(path)], text=True, timeout=30))
    if info["format"] != "qcow2" or info.get("backing-filename"):
        raise ValueError("Only standalone qcow2 test disks are accepted")
    return info


def command_line(disk, output, runtime, mode, firmware_vars=None):
    if any("," in str(path) or "\n" in str(path) for path in (disk, output, runtime)):
        raise ValueError("Invalid QEMU path")
    command = [
        "qemu-system-x86_64", "-machine", "q35,accel=kvm", "-cpu", "host",
        "-m", "6144", "-smp", "4", "-nic", "none", "-vga", "virtio",
        "-display", "none", "-no-reboot", "-boot", "c", "-snapshot",
        "-drive", f"if=virtio,format=qcow2,file={disk}",
        "-serial", f"file:{output / 'console.log'}",
        "-chardev", f"socket,id=qga0,path={runtime / 'qga.sock'},server=on,wait=off",
        "-device", "virtio-serial-pci",
        "-device", "virtserialport,chardev=qga0,name=org.qemu.guest_agent.0",
        "-qmp", f"unix:{runtime / 'qmp.sock'},server=on,wait=off",
    ]
    if mode == "uefi":
        code = Path("/usr/share/OVMF/OVMF_CODE_4M.fd")
        if firmware_vars is None or not firmware_vars.is_file() or not code.is_file():
            raise OSError("UEFI first boot requires the variable store retained from installation")
        variables = runtime / "OVMF_VARS.fd"
        shutil.copyfile(firmware_vars, variables)
        command += ["-drive", f"if=pflash,format=raw,readonly=on,file={code}",
                    "-drive", f"if=pflash,format=raw,file={variables}"]
    return command


def contract_arguments(mode, filesystem, user, live_machine_id, inventory):
    args = ["--mode", mode, "--filesystem", filesystem, "--user", user,
            "--live-machine-id", live_machine_id]
    names = {"supralinux-defaults", "supralinux-kdeconnect-sftp"}
    versions = {entry["source"]: entry["version"] for entry in inventory["packages"]
                if entry["source"] in names}
    if set(versions) != names:
        raise ValueError("Missing installed overlay versions from source inventory")
    for name, version in sorted(versions.items()):
        args += ["--expected", f"{name}={version}"]
    return args


def visible_frame(path):
    """Conservative evidence: reject blank or near-uniform PPM framebuffers."""
    with path.open("rb") as f:
        if f.readline().strip() != b"P6":
            raise ValueError("Expected binary PPM screenshot")
        width, height = map(int, f.readline().split())
        if not (320 <= width <= 8192 and 200 <= height <= 8192):
            raise ValueError("Invalid screen dimensions")
        if f.readline().strip() != b"255":
            raise ValueError("Unsupported PPM depth")
        data = f.read()
    if len(data) != width * height * 3:
        raise ValueError("Truncated screenshot")
    # Require color variation across the framebuffer, not merely a cursor.
    stride = max(1, width * height // 4096)
    samples = [data[i:i+3] for i in range(0, len(data), stride * 3)]
    distinct = len(set(samples))
    bright = sum(max(pixel) >= 24 for pixel in samples)
    return {"width": width, "height": height, "distinct_samples": distinct,
            "visible_samples": bright, "sample_count": len(samples),
            "nonblank": distinct >= 16 and bright >= max(1, len(samples) // 20)}


GREETER_CHECK = r"""
set -eu
systemctl is-active --quiet sddm.service
pgrep -f '^(/[^ ]*/)?sddm-greeter(-qt6)?( |$)' >/dev/null
for session in $(loginctl list-sessions --no-legend | awk '{print $1}'); do
    if [ "$(loginctl show-session "$session" -p Class --value)" = greeter ] &&
       [ "$(loginctl show-session "$session" -p Active --value)" = yes ]; then
        loginctl show-session "$session" -p Class -p Type -p Active -p State
        exit 0
    fi
done
exit 1
"""


def collect_greeter(agent, qmp, output, timeout=120):
    """Require an active SDDM greeter and two nonblank guest framebuffer samples."""
    deadline = time.monotonic() + timeout
    consecutive = 0
    samples = []
    while time.monotonic() < deadline:
        probe = agent.execute("/bin/sh", ["-c", GREETER_CHECK], timeout=15)
        qmp.call("screendump", {"filename": str(output / "greeter-latest.ppm")})
        frame = visible_frame(output / "greeter-latest.ppm")
        frame["greeter_active"] = probe.get("exitcode") == 0
        frame["session"] = base64.b64decode(probe.get("out-data", "")).decode(errors="replace")
        samples.append(frame)
        consecutive = consecutive + 1 if frame["nonblank"] and frame["greeter_active"] else 0
        if consecutive >= 2:
            shutil.copyfile(output / "greeter-latest.ppm", output / "greeter-ready.ppm")
            return {"status": "PASS", "scope": "visible greeter readiness, not login", "samples": samples}
        time.sleep(5)
    return {"status": "FAIL", "scope": "visible greeter readiness, not login", "samples": samples}


def run(args):
    # Import QMP implementation only when executing, not during unit tests.
    import importlib.util
    spec = importlib.util.spec_from_file_location("live_boot", ROOT / "tools/ci/boot-live.py")
    if spec is None or not Path(spec.origin).is_file():
        raise OSError("Requires the validated ISO boot helper from PR #13")
    boot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(boot)
    disk = args.disk.absolute()
    verify_disk(disk)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {"scope": "first boot of a disposable unencrypted installed VM",
              "status": "INFRA_INVALID"}
    process = qmp = agent = None
    with tempfile.TemporaryDirectory(prefix="supra-target-") as directory:
        runtime = Path(directory)
        try:
            command = command_line(disk, output, runtime, args.mode, args.firmware_vars)
            (output / "qemu-command.json").write_text(json.dumps(command, indent=2))
            started = time.monotonic()
            with (output / "qemu.log").open("w") as log:
                process = subprocess.Popen(command, stdout=log, stderr=log)
                qmp = boot.connect_until(runtime / "qmp.sock", process, time.monotonic() + 30, True)
                report["kvm"] = qmp.call("query-kvm")
                if not all(report["kvm"].get(key) for key in ("present", "enabled")):
                    raise RuntimeError("KVM disabled")
                report["status"] = "FAIL"
                agent = wait_agent(runtime / "qga.sock", process, timeout=240)
                probe = agent.execute("/bin/sh", ["-c",
                    '. /etc/os-release; test "$ID" = supralinux && test "$VERSION_ID" = 26.04 && ! grep -qw boot=casper /proc/cmdline'], timeout=15)
                if probe.get("exitcode") != 0:
                    raise RuntimeError("Guest is not an installed SupraLINUX target")
                report["guest_agent_ready_seconds"] = round(time.monotonic() - started, 2)
                # Wait for the graphical target and ZRAM units before reading the contract.
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    probe = agent.execute("/bin/sh", ["-c",
                        "systemctl is-active --quiet graphical.target && test -e /sys/block/zram0/disksize && grep -q /dev/zram0 /proc/swaps"], timeout=15)
                    if probe.get("exitcode") == 0:
                        break
                    time.sleep(5)
                source = ROOT / "tools/qa/installed-contract.py"
                inventory = json.loads((ROOT / "manifests/packages-1.0.0.json").read_text())
                contract = contract_arguments(args.mode, args.filesystem, args.user,
                                              args.live_machine_id, inventory)
                agent.put("/tmp/supra-qa-installed-contract.py", source.read_bytes())
                result = agent.execute("/usr/bin/python3", ["/tmp/supra-qa-installed-contract.py", *contract], timeout=180)
                stdout = base64.b64decode(result.get("out-data", "")).decode(errors="replace")
                stderr = base64.b64decode(result.get("err-data", "")).decode(errors="replace")
                (output / "installed-contract.json").write_text(stdout)
                (output / "installed-contract.stderr").write_text(stderr)
                evidence = json.loads(stdout)
                report["installed_contract"] = evidence
                report["status"] = "PASS" if result.get("exitcode") == 0 and evidence.get("status") == "PASS" else "FAIL"
                if args.verify_greeter and report["status"] == "PASS":
                    report["greeter"] = collect_greeter(agent, qmp, output)
                    if report["greeter"]["status"] != "PASS":
                        report["status"] = "FAIL"
                if args.verify_greeter:
                    diagnostic = agent.execute("/bin/sh", ["-c",
                        "loginctl list-sessions; systemctl --no-pager status sddm.service; "
                        "journalctl -b -u sddm.service --no-pager -n 100"], timeout=30)
                    (output / "sddm-diagnostics.txt").write_text(
                        base64.b64decode(diagnostic.get("out-data", "")).decode(errors="replace") +
                        base64.b64decode(diagnostic.get("err-data", "")).decode(errors="replace"))
        except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
            report["error"] = str(exc)
        finally:
            if agent:
                agent.close()
            if qmp:
                try:
                    qmp.call("screendump", {"filename": str(output / "screen.ppm")})
                except (OSError, RuntimeError, ValueError) as exc:
                    report["screenshot_error"] = str(exc)
                qmp.close()
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("disk", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--mode", choices=["bios", "uefi"], required=True)
    parser.add_argument("--firmware-vars", type=Path)
    parser.add_argument("--filesystem", choices=["btrfs", "ext4"], required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--live-machine-id", required=True)
    parser.add_argument("--verify-greeter", action="store_true",
                        help="Also require active greeter and nonblank framebuffer evidence")
    args = parser.parse_args()
    raise SystemExit(run(args))
