"""Hard-stop the disposable KVM guest at a reviewed rollback boundary."""
import argparse
import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from package_smoke import wait_agent

GUEST = ROOT / "tools/qa/guest/rollback-cut.sh"
PHASES = ("before-exchange", "after-exchange", "before-backup-rename", "after-backup-rename")
HELPER_SHA256 = "4f54dc0f1ee0c3707656b63a6297be1f4a03658bb86ba1d765c705c153b73d1a"


def load_boot():
    spec = importlib.util.spec_from_file_location("boot_live", ROOT / "tools/ci/boot-live.py")
    boot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(boot)
    return boot


def command_line(boot, iso, disk, output, runtime):
    cmd = boot.command_line(iso, output, runtime, "uefi")
    return cmd + ["-drive", f"if=none,id=cutfixture,file={disk},format=raw,cache=none",
                  "-device", "virtio-blk-pci,drive=cutfixture,serial=SUPRAQA-CUT"]


def decode(result, key="out-data"):
    return base64.b64decode(result.get(key, "")).decode(errors="replace")


def checked(agent, script, timeout=60):
    result = agent.execute("/bin/sh", ["-c", script], timeout=timeout)
    if result.get("exitcode") != 0:
        raise RuntimeError(f"Guest assertion failed: {decode(result)} {decode(result, 'err-data')}")
    return decode(result)


@contextmanager
def vm(boot, iso, disk, output, runtime):
    output.mkdir()
    runtime.mkdir()
    proc = qmp = agent = None
    with (output / "qemu.log").open("w") as log:
        try:
            cmd = command_line(boot, iso, disk, output, runtime)
            (output / "qemu-command.json").write_text(json.dumps(cmd, indent=2))
            proc = subprocess.Popen(cmd, stdout=log, stderr=log)
            qmp = boot.connect_until(runtime / "qmp.sock", proc, time.monotonic()+30, True)
            kvm = qmp.call("query-kvm")
            if not (kvm.get("enabled") and kvm.get("present")):
                raise RuntimeError("KVM unavailable")
            agent = wait_agent(runtime / "qga.sock", proc, timeout=240)
            checked(agent, '. /etc/os-release; test "$ID" = supralinux && test -d /cdrom/casper')
            yield proc, qmp, agent
        finally:
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            if agent:
                agent.close()
            if qmp:
                qmp.close()


def wait_checkpoint(agent, pid, phase, timeout=90):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        result = agent.call("guest-exec-status", pid=pid)
        if result.get("exited"):
            raise RuntimeError("Recovery exited before checkpoint: "
                               + json.dumps({"exitcode": result.get("exitcode"),
                                             "stdout": decode(result), "stderr": decode(result, "err-data")}))
        marker = agent.execute("/bin/cat", ["/run/supra-qa-cut/checkpoint"], timeout=5)
        if marker.get("exitcode") == 0:
            if decode(marker).strip() != phase:
                raise RuntimeError("Unexpected checkpoint: " + decode(marker))
            return
        time.sleep(0.2)
    raise TimeoutError("Cut checkpoint not reached")


def run(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {"status": "INFRA_INVALID", "phase": args.phase,
              "scope": "abrupt QEMU process stop on synthetic fixture, not physical power-loss certification"}
    boot = load_boot()
    with tempfile.TemporaryDirectory(prefix="supra-cut-") as tmp:
        runtime = Path(tmp)
        disk = runtime / "fixture.raw"
        try:
            subprocess.run(["qemu-img", "create", "-f", "raw", str(disk), "4G"], check=True)
            with vm(boot, args.iso.resolve(), disk, out / "before", runtime / "first") as (proc, qmp, agent):
                report["status"] = "FAIL"
                report["helper_sha256"] = checked(agent,
                    "sha256sum /usr/local/sbin/supralinux-recover | cut -d ' ' -f1").strip()
                if report["helper_sha256"] != HELPER_SHA256:
                    raise RuntimeError("Packaged recovery helper differs from the validated source")
                agent.put("/tmp/supra-qa-cut.sh", GUEST.read_bytes())
                report["fixture"] = checked(agent, "/bin/sh /tmp/supra-qa-cut.sh prepare", 120)
                pid = agent.call("guest-exec", path="/bin/sh",
                    arg=["-x", "/tmp/supra-qa-cut.sh", "run", args.phase],
                    **{"capture-output": True})["pid"]
                try:
                    wait_checkpoint(agent, pid, args.phase)
                except (RuntimeError, TimeoutError):
                    for name in ("helper.log", "checkpoint"):
                        try:
                            data = agent.get("/run/supra-qa-cut/" + name, limit=1024*1024)
                            (out / ("failure-" + name)).write_bytes(data)
                            report[name] = data.decode(errors="replace")
                        except (OSError, RuntimeError, ValueError) as exc:
                            report[name + "_error"] = str(exc)
                    raise
                report["checkpoint"] = args.phase
                (out / "helper-before-cut.log").write_bytes(agent.get("/run/supra-qa-cut/helper.log", limit=1024*1024))
                # No QMP quit, guest shutdown, guest sync, or graceful termination.
                proc.kill()
                report["qemu_exitcode"] = proc.wait(timeout=15)
                if report["qemu_exitcode"] != -9:
                    raise RuntimeError("Expected SIGKILL of the exact disposable VM process")
            # A fresh VM mounts the same raw disk, allowing normal filesystem replay.
            with vm(boot, args.iso.resolve(), disk, out / "after", runtime / "second") as (_, qmp, agent):
                agent.put("/tmp/supra-qa-cut.sh", GUEST.read_bytes())
                report["verification"] = checked(agent, "/bin/sh /tmp/supra-qa-cut.sh verify " + args.phase, 120)
                if "CUT_PASS:" not in report["verification"]:
                    raise RuntimeError("Missing post-replay assertion")
                qmp.call("screendump", {"filename": str(out / "after" / "screen.ppm")})
                report["status"] = "PASS"
        except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
            report["error"] = str(exc)
    (out / "result.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--phase", choices=PHASES, required=True)
    raise SystemExit(run(parser.parse_args()))
