"""Read-only discovery of the real Calamares UI in a disposable offline guest."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from package_smoke import Agent, wait_agent

# Reuse the validated QMP implementation from the exact ISO build source.
import importlib.util

def load_boot(path):
    spec = importlib.util.spec_from_file_location("candidate_boot", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decode(result, key):
    import base64
    return base64.b64decode(result.get(key, "")).decode(errors="replace")


def guest(agent, command, timeout=30):
    result = agent.execute("/bin/sh", ["-c", command], timeout=timeout)
    return {"exitcode": result.get("exitcode"), "stdout": decode(result, "out-data"),
            "stderr": decode(result, "err-data")}


SESSION = r"""
set -eu
. /etc/os-release
test "$ID" = supralinux
test "$VERSION_ID" = 26.04
test -d /cdrom/casper
pgrep -x plasmashell
pgrep -x kwin_wayland
"""
LAUNCH = r"""
set -eu
pid=$(pgrep -u supralinux -x plasmashell | head -n 1)
test -n "$pid"
python3 - "$pid" <<'PY'
import os, subprocess, sys
from pathlib import Path
data = Path('/proc/' + sys.argv[1] + '/environ').read_bytes().split(b'\0')
session = dict(item.decode(errors='surrogateescape').split('=', 1)
               for item in data if b'=' in item)
env = {**os.environ, **{key: session[key] for key in (
    'DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'XDG_RUNTIME_DIR',
    'DBUS_SESSION_BUS_ADDRESS', 'XDG_SESSION_TYPE', 'LANG') if key in session}}
env['QT_LINUX_ACCESSIBILITY_ALWAYS_ON'] = '1'
with open('/tmp/supra-qa-calamares.log', 'wb') as log:
    subprocess.Popen(['/usr/bin/calamares', '-d'], env=env,
                     stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                     start_new_session=True)
PY
"""
DISCOVER = r"""
set +e
echo '=== Calamares process ==='
pgrep -a -x calamares
echo '=== Automation tools ==='
for cmd in gdbus busctl xdotool xwininfo wmctrl; do command -v "$cmd"; done
python3 -c 'import pyatspi; print("pyatspi available")' 2>&1
echo '=== Session accessibility service ==='
uid=$(id -u supralinux)
runuser -u supralinux -- env XDG_RUNTIME_DIR=/run/user/"$uid" DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/"$uid"/bus gdbus call --session --dest org.a11y.Bus --object-path /org/a11y/bus --method org.a11y.Bus.GetAddress
echo '=== Installer log ==='
tail -n 100 /tmp/supra-qa-calamares.log
"""


def click(qmp, x, y, width=1280, height=800):
    """Absolute tablet input, with no input to the host desktop."""
    if not (0 <= x < width and 0 <= y < height):
        raise ValueError("Click outside expected framebuffer")
    qmp.call("input-send-event", {"events": [
        {"type": "abs", "data": {"axis": "x", "value": round(x * 32767 / (width - 1))}},
        {"type": "abs", "data": {"axis": "y", "value": round(y * 32767 / (height - 1))}},
        {"type": "btn", "data": {"down": True, "button": "left"}},
    ]})
    qmp.call("input-send-event", {"events": [
        {"type": "btn", "data": {"down": False, "button": "left"}},
    ]})


def verify_frame(path):
    with path.open("rb") as stream:
        if stream.readline().strip() != b"P6":
            raise ValueError("Expected binary PPM framebuffer")
        dimensions = stream.readline().split()
        if dimensions != [b"1280", b"800"]:
            raise ValueError(f"Unexpected framebuffer size: {dimensions}")


ACCESSIBILITY = r"""
set -eu
uid=$(id -u supralinux)
runuser -u supralinux -- env XDG_RUNTIME_DIR=/run/user/"$uid" DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/"$uid"/bus python3 - <<'PY'
import ast, subprocess
raw = subprocess.check_output(["gdbus", "call", "--session", "--dest", "org.a11y.Bus", "--object-path", "/org/a11y/bus", "--method", "org.a11y.Bus.GetAddress"], text=True)
address, = ast.literal_eval(raw.strip())
print(subprocess.check_output(["gdbus", "call", "--address", address, "--dest", "org.a11y.atspi.Registry", "--object-path", "/org/a11y/atspi/accessible/root", "--method", "org.a11y.atspi.Accessible.GetChildren"], text=True))
PY
"""

DISK_GUARD = r"""
set -eux
lsblk -o NAME,TYPE,SIZE,FSTYPE,SERIAL,MOUNTPOINTS
test -b /dev/disk/by-id/virtio-SUPRAQA-INSTALL
test "$(readlink -f /dev/disk/by-id/virtio-SUPRAQA-INSTALL)" = /dev/vda
# zram is reported as a disk by lsblk, but is not an installation target.
test "$(lsblk -dn -o NAME,TYPE | awk '$2 == "disk" && $1 !~ /^zram[0-9]+$/ {print $1}')" = vda
test "$(lsblk -bdn -o SIZE /dev/vda)" = 42949672960
test "$(lsblk -rn -o NAME /dev/vda | wc -l)" -eq 1
test -z "$(lsblk -dn -o FSTYPE /dev/vda)"
test "$(lsblk -dn -o SERIAL /dev/vda | tr -d ' ')" = SUPRAQA-INSTALL
if findmnt -rn -S /dev/vda; then exit 1; fi
"""



def run(args):
    boot = load_boot(args.boot_helper)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {"scope": "installer discovery only; no installation",
              "status": "INFRA_INVALID"}
    process = qmp = agent = None
    with tempfile.TemporaryDirectory(prefix="supra-inst-") as directory:
        runtime = Path(directory)
        try:
            disk = runtime / "target.qcow2"
            subprocess.run(["qemu-img", "create", "-f", "qcow2", str(disk), "40G"], check=True)
            cmd = boot.command_line(args.iso.resolve(), output, runtime, "uefi")
            cmd += ["-drive", f"if=none,id=target,format=qcow2,file={disk}",
                    "-device", "virtio-blk-pci,drive=target,serial=SUPRAQA-INSTALL",
                    "-device", "qemu-xhci", "-device", "usb-tablet"]
            with (output / "qemu.log").open("w") as log:
                process = subprocess.Popen(cmd, stdout=log, stderr=log)
                qmp = boot.connect_until(runtime / "qmp.sock", process, time.monotonic() + 30, True)
                report["kvm"] = qmp.call("query-kvm")
                if not all(report["kvm"].get(k) for k in ("present", "enabled")):
                    raise RuntimeError("KVM disabled")
                report["status"] = "FAIL"
                agent = wait_agent(runtime / "qga.sock", process, timeout=180)
                deadline = time.monotonic() + 180
                while time.monotonic() < deadline:
                    ready = guest(agent, SESSION)
                    if ready["exitcode"] == 0:
                        break
                    time.sleep(5)
                else:
                    raise RuntimeError("Live desktop not ready")
                report["launch"] = guest(agent, LAUNCH)
                if report["launch"]["exitcode"] != 0:
                    raise RuntimeError("Calamares launch failed")
                for index in range(3):
                    time.sleep(10)
                    qmp.call("screendump", {"filename": str(output / f"installer-{index}.ppm")})
                    report[f"probe_{index}"] = guest(agent, DISCOVER)
                if guest(agent, "pgrep -x calamares")["exitcode"] != 0:
                    raise RuntimeError("Calamares did not remain running")
                report["accessibility_registry"] = guest(agent, ACCESSIBILITY)
                # The exact welcome screenshot showed Next at (1136, 736).
                # Only advance three pages; never select or confirm partitioning.
                frame = output / "installer-2.ppm"
                verify_frame(frame)
                for index in range(1, 4):
                    click(qmp, 1136, 736)
                    time.sleep(4)
                    frame = output / f"navigation-{index}.ppm"
                    qmp.call("screendump", {"filename": str(frame)})
                    verify_frame(frame)
                    report[f"navigation_{index}"] = guest(agent, "tail -n 30 /tmp/supra-qa-calamares.log")
                report["disk_guard"] = guest(agent, DISK_GUARD)
                if report["disk_guard"]["exitcode"] != 0:
                    raise RuntimeError("Unexpected disk topology")
                click(qmp, 206, 71)
                time.sleep(4)
                qmp.call("screendump", {"filename": str(output / "partition-options.ppm")})
                report["partition_options_log"] = guest(agent, "tail -n 50 /tmp/supra-qa-calamares.log")
                report["status"] = "PASS"
        except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
            report["error"] = str(exc)
        finally:
            if agent is not None:
                agent.close()
            if qmp is not None:
                qmp.close()
            if process is not None:
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
    parser.add_argument("iso", type=Path)
    parser.add_argument("boot_helper", type=Path)
    parser.add_argument("output", type=Path)
    raise SystemExit(run(parser.parse_args()))
