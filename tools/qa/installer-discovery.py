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
            cmd += ["-drive", f"if=virtio,format=qcow2,file={disk}"]
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
