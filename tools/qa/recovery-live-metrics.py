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


RECOVERY = r"""
set -eu
. /etc/os-release
test "$ID" = supralinux
test -d /cdrom/casper
# Refuse to operate on anything other than the dedicated empty QA disk.
dev=/dev/disk/by-id/virtio-SUPRAQA-ROLLBACK
test -b "$dev"
test "$(lsblk -dn -o SERIAL "$dev" | tr -d ' ')" = SUPRAQA-ROLLBACK
test "$(lsblk -rn -o NAME "$dev" | wc -l)" -eq 1
test -z "$(lsblk -dn -o FSTYPE "$dev")"
if findmnt -rn -S "$(readlink -f "$dev")" >/dev/null; then exit 1; fi
mkfs.btrfs -q "$dev"
mountpoint=$(mktemp -d /run/supra-qa.XXXXXX)
trap 'umount "$mountpoint" 2>/dev/null || true; rmdir "$mountpoint" 2>/dev/null || true' EXIT
mount -o subvolid=5 "$dev" "$mountpoint"
btrfs subvolume create "$mountpoint/@"
btrfs subvolume create "$mountpoint/@home"
btrfs subvolume create "$mountpoint/@snapshots"
printf 'original\n' > "$mountpoint/@/root-marker"
printf 'unchanged\n' > "$mountpoint/@home/home-marker"
mkdir "$mountpoint/@snapshots/1"
btrfs subvolume snapshot -r "$mountpoint/@" "$mountpoint/@snapshots/1/snapshot"
printf '<snapshot><type>single</type><date>2026-11-25</date><description>QA baseline</description></snapshot>\n' > "$mountpoint/@snapshots/1/info.xml"
printf 'changed\n' > "$mountpoint/@/root-marker"
sync
umount "$mountpoint"
helper=/usr/local/sbin/supralinux-recover
test -x "$helper"
"$helper" --device "$dev" --list-tsv
"$helper" --device "$dev" --snapshot 1 --yes --progress=json
mount -o subvolid=5 "$dev" "$mountpoint"
test "$(cat "$mountpoint/@/root-marker")" = original
test "$(cat "$mountpoint/@home/home-marker")" = unchanged
test "$(cat "$mountpoint/@snapshots/1/snapshot/root-marker")" = original
set -- "$mountpoint"/@pre-rollback-*
test "$#" -eq 1
test "$(cat "$1/root-marker")" = changed
echo 'ROLLBACK_PASS: root restored, home unchanged, snapshot and prior root retained'
"""


METRICS = r"""
set -eu
. /etc/os-release
test "$ID" = supralinux
test -d /cdrom/casper
echo '=== uptime ==='
cat /proc/uptime
echo '=== memory ==='
grep -E '^(MemTotal|MemAvailable|SwapTotal|SwapFree):' /proc/meminfo
echo '=== boot ==='
systemd-analyze time || true
echo '=== load ==='
cat /proc/loadavg
echo '=== swap ==='
cat /proc/swaps
echo '=== largest RSS processes ==='
ps -eo pid,comm,rss --sort=-rss | head -n 21
echo '=== zram ==='
if test -d /sys/block/zram0; then
    cat /sys/block/zram0/disksize /sys/block/zram0/comp_algorithm
fi
"""


def run(args):
    spec = importlib.util.spec_from_file_location("candidate_boot", args.boot_helper)
    boot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(boot)
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
                result = agent.execute("/bin/sh", ["-c", RECOVERY if args.mode == "recovery" else METRICS], timeout=180)
                for key in ("out-data", "err-data"):
                    report[key] = base64.b64decode(result.get(key, "")).decode(errors="replace")
                report["exitcode"] = result.get("exitcode")
                if result.get("exitcode") != 0:
                    raise RuntimeError("Guest checks failed")
                if args.mode == "recovery" and "ROLLBACK_PASS:" not in report["out-data"]:
                    raise RuntimeError("Missing rollback assertion")
                report["status"] = "PASS"
                qmp.call("screendump", {"filename": str(out / "screen.ppm")})
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
    parser.add_argument("boot_helper", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--mode", choices=["recovery", "metrics"], required=True)
    raise SystemExit(run(parser.parse_args()))
