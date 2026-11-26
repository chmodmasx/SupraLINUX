"""Independent candidate VM probes; no product or installed disk modification."""
import argparse
import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from package_smoke import wait_agent

MEMORY_MIB = (2048, 4096, 8192, 12288)
SCENARIOS = ("atomic-exchange", *(f"zram-{m}" for m in MEMORY_MIB))


def load_boot():
    spec = importlib.util.spec_from_file_location("boot_live", ROOT / "tools/ci/boot-live.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def command_line(boot, args, runtime, out):
    cmd = boot.command_line(args.iso.resolve(), out, runtime, "uefi")
    if args.scenario == "atomic-exchange":
        disk = runtime / "exchange.qcow2"
        subprocess.run(["qemu-img", "create", "-f", "qcow2", str(disk), "4G"], check=True)
        cmd += ["-drive", f"if=none,id=exchange,file={disk},format=qcow2",
                "-device", "virtio-blk-pci,drive=exchange,serial=SUPRAQA-EXCHANGE"]
    else:
        cmd[cmd.index("-m") + 1] = args.scenario.split("-")[1]
    return cmd


ZRAM_PROBE = r"""
import importlib.util, json
from pathlib import Path
spec = importlib.util.spec_from_file_location("contract", "/tmp/supra-qa-contract.py")
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)
result = contract.zram_policy(Path("/proc/meminfo").read_text(),
    Path("/sys/block/zram0/disksize").read_text(),
    Path("/sys/block/zram0/comp_algorithm").read_text(),
    Path("/proc/swaps").read_text())
result["meminfo"] = [line for line in Path("/proc/meminfo").read_text().splitlines()
                     if line.startswith(("MemTotal:", "MemAvailable:", "SwapTotal:", "SwapFree:"))]
print(json.dumps(result))
"""


def run(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {"scenario": args.scenario, "status": "INFRA_INVALID",
              "scope": "live guest probe, not installed-system or power-cut certification"}
    boot = load_boot()
    proc = qmp = agent = None
    with tempfile.TemporaryDirectory(prefix="supra-extra-") as tmp:
        runtime = Path(tmp)
        try:
            cmd = command_line(boot, args, runtime, out)
            (out / "qemu-command.json").write_text(json.dumps(cmd, indent=2))
            with (out / "qemu.log").open("w") as log:
                proc = subprocess.Popen(cmd, stdout=log, stderr=log)
                qmp = boot.connect_until(runtime / "qmp.sock", proc, time.monotonic()+30, True)
                report["kvm"] = qmp.call("query-kvm")
                if not all(report["kvm"].get(k) for k in ("present", "enabled")):
                    raise RuntimeError("KVM unavailable")
                report["status"] = "FAIL"
                agent = wait_agent(runtime / "qga.sock", proc, timeout=240)
                deadline = time.monotonic()+240
                consecutive = 0
                while time.monotonic() < deadline:
                    result = agent.execute("/bin/sh", ["-c", boot.CHECK], timeout=15)
                    consecutive = consecutive + 1 if result.get("exitcode") == 0 else 0
                    if consecutive >= 2:
                        break
                    time.sleep(5)
                else:
                    raise RuntimeError("Live desktop not ready")
                if args.scenario == "atomic-exchange":
                    script = (ROOT / "tools/qa/guest/atomic-exchange.sh").read_text()
                    result = agent.execute("/bin/sh", ["-c", script], timeout=180)
                else:
                    agent.put("/tmp/supra-qa-contract.py",
                              (ROOT / "tools/qa/installed-contract.py").read_bytes())
                    result = agent.execute("/usr/bin/python3", ["-c", ZRAM_PROBE], timeout=30)
                report["stdout"] = base64.b64decode(result.get("out-data", "")).decode(errors="replace")
                report["stderr"] = base64.b64decode(result.get("err-data", "")).decode(errors="replace")
                report["exitcode"] = result.get("exitcode")
                if report["exitcode"] != 0:
                    raise RuntimeError("Guest probe failed")
                if args.scenario == "atomic-exchange":
                    if "ATOMIC_EXCHANGE_PASS" not in report["stdout"]:
                        raise RuntimeError("Missing exchange evidence")
                else:
                    report["zram"] = json.loads(report["stdout"])
                qmp.call("screendump", {"filename": str(out / "screen.ppm")})
                report["status"] = "PASS"
        except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
            report["error"] = str(exc)
        finally:
            if agent:
                agent.close()
            if qmp:
                if report["status"] != "PASS":
                    try:
                        qmp.call("screendump", {"filename": str(out / "last.ppm")})
                    except (OSError, ValueError, RuntimeError) as exc:
                        report["screenshot_error"] = str(exc)
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
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scenario", choices=SCENARIOS, required=True)
    raise SystemExit(run(parser.parse_args()))
