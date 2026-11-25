"""Boot a testing ISO with KVM and check the live Plasma session over QGA."""
import argparse
import base64
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time


class Monitor:
    def __init__(self, path, qmp=False):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(10)
        try:
            self.sock.connect(str(path))
            self.stream = self.sock.makefile("rwb")
            if qmp:
                self.read()
                self.call("qmp_capabilities")
        except Exception:
            self.sock.close()
            raise

    def read(self):
        line = self.stream.readline()
        if not line:
            raise ConnectionError("Monitor disconnected")
        return json.loads(line)

    def call(self, name, arguments=None):
        request = {"execute": name, "id": "qa"}
        if arguments is not None:
            request["arguments"] = arguments
        self.stream.write(json.dumps(request).encode() + b"\n")
        self.stream.flush()
        while True:
            reply = self.read()
            if reply.get("id") != "qa":
                continue
            if "error" in reply:
                raise RuntimeError(f"{name}: {reply['error']}")
            return reply["return"]

    def close(self):
        self.stream.close()
        self.sock.close()


CHECK = r"""
set -eu
. /etc/os-release
test "$ID" = supralinux
test "$VERSION_ID" = 26.04
test -d /cdrom/casper
pgrep -x kwin_wayland
pgrep -x plasmashell
# A running shell and active login session can precede the visible desktop.
if pgrep -u supralinux -x ksplashqml >/dev/null; then exit 1; fi
uid=$(id -u supralinux)
runuser -u supralinux -- busctl --address="unix:path=/run/user/$uid/bus" \
    call org.kde.plasmashell /PlasmaShell org.freedesktop.DBus.Peer Ping
for session in $(loginctl list-sessions --no-legend | awk '{print $1}'); do
    if [ "$(loginctl show-session "$session" -p Type --value)" = wayland ] &&
       [ "$(loginctl show-session "$session" -p Name --value)" = supralinux ] &&
       [ "$(loginctl show-session "$session" -p Active --value)" = yes ]; then
        loginctl show-session "$session" -p Name -p Type -p Active
        exit 0
    fi
done
exit 1
"""


def command_line(iso, output, runtime, mode):
    command = [
        "qemu-system-x86_64", "-machine", "q35,accel=kvm", "-cpu", "host",
        "-m", "6144", "-smp", "4", "-cdrom", str(iso), "-boot", "d",
        "-nic", "none", "-vga", "virtio", "-display", "none", "-no-reboot",
        "-serial", f"file:{output / 'console.log'}",
        "-qmp", f"unix:{runtime / 'qmp.sock'},server=on,wait=off",
        "-chardev", f"socket,id=qga0,path={runtime / 'qga.sock'},server=on,wait=off",
        "-device", "virtio-serial-pci",
        "-device", "virtserialport,chardev=qga0,name=org.qemu.guest_agent.0",
    ]
    if mode == "uefi":
        code = Path("/usr/share/OVMF/OVMF_CODE_4M.fd")
        template = Path("/usr/share/OVMF/OVMF_VARS_4M.fd")
        if not code.is_file() or not template.is_file():
            raise OSError("OVMF 4M firmware unavailable")
        variables = runtime / "OVMF_VARS.fd"
        shutil.copyfile(template, variables)
        command += ["-drive", f"if=pflash,format=raw,readonly=on,file={code}",
                    "-drive", f"if=pflash,format=raw,file={variables}"]
    return command


def connect_until(path, process, deadline, qmp=False):
    while time.monotonic() < deadline and process.poll() is None:
        try:
            return Monitor(path, qmp=qmp)
        except (OSError, ValueError, ConnectionError):
            time.sleep(1)
    raise TimeoutError(f"Monitor unavailable: {path.name}; qemu status={process.poll()}")


def guest_check(agent):
    agent.call("guest-ping")
    pid = agent.call("guest-exec", {"path": "/bin/sh", "arg": ["-c", CHECK],
                                    "capture-output": True})["pid"]
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        result = agent.call("guest-exec-status", {"pid": pid})
        if result.get("exited"):
            decoded = {key: base64.b64decode(result.get(key, "")).decode(errors="replace")
                       for key in ("out-data", "err-data")}
            return result.get("exitcode") == 0, decoded
        time.sleep(1)
    raise TimeoutError("Guest check did not finish")


def run(iso, output, mode, timeout):
    output.mkdir(parents=True, exist_ok=False)
    report = {"status": "INFRA_INVALID", "mode": mode, "scope": "live desktop boot only"}
    process = qmp = agent = None
    with tempfile.TemporaryDirectory(prefix="supra-vm-") as tmp:
        runtime = Path(tmp)
        try:
            command = command_line(iso, output, runtime, mode)
            (output / "qemu-command.json").write_text(json.dumps(command, indent=2))
            with (output / "qemu.log").open("w") as log:
                process = subprocess.Popen(command, stdout=log, stderr=log)
                qmp = connect_until(runtime / "qmp.sock", process, time.monotonic() + 30, True)
                kvm = qmp.call("query-kvm")
                report["kvm"] = kvm
                if not (kvm.get("enabled") and kvm.get("present")):
                    raise RuntimeError("KVM not enabled")
                report["status"] = "FAIL"
                deadline = time.monotonic() + timeout
                last = "Guest agent not ready"
                consecutive = 0
                while time.monotonic() < deadline and process.poll() is None:
                    try:
                        if agent is None:
                            agent = Monitor(runtime / "qga.sock")
                        ok, last = guest_check(agent)
                        report["guest"] = last
                        consecutive = consecutive + 1 if ok else 0
                        if consecutive >= 2:
                            report["status"] = "PASS"
                            report["desktop_ready_samples"] = consecutive
                            break
                    except (OSError, ValueError, RuntimeError, ConnectionError, TimeoutError) as exc:
                        last = str(exc)
                        consecutive = 0
                        if agent is not None:
                            agent.close()
                            agent = None
                    time.sleep(5)
                if report["status"] != "PASS":
                    report["error"] = str(last)
        except (OSError, ValueError, RuntimeError, TimeoutError, ConnectionError) as exc:
            report["error"] = str(exc)
        finally:
            if agent is not None:
                agent.close()
            if qmp is not None:
                try:
                    qmp.call("screendump", {"filename": str(output / "screen.ppm")})
                except (OSError, RuntimeError, ValueError, ConnectionError) as exc:
                    report["screenshot_error"] = str(exc)
                    if report["status"] == "PASS":
                        report["status"] = "INFRA_INVALID"
                qmp.close()
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                report["qemu_exit"] = process.returncode
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--mode", choices=["bios", "uefi"], required=True)
    parser.add_argument("--timeout", type=int, default=420)
    args = parser.parse_args()
    if not args.iso.is_file() or args.timeout <= 0:
        parser.error("Expected existing ISO and positive timeout")
    raise SystemExit(run(args.iso.resolve(), args.output.resolve(), args.mode, args.timeout))


if __name__ == "__main__":
    main()
