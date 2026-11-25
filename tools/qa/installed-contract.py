"""Read-only first-boot checks, intended for an installed disposable QA VM."""
import argparse
import json
import os
from pathlib import Path
import pwd
import re
import subprocess


MIB = 1024 * 1024
LIVE_PACKAGES = ("supralinux-recovery-gui", "supralinux-calamares-config",
                 "calamares", "calamares-data", "libcalamaresui3.3", "casper")
LIVE_PATHS = ("/etc/polkit-1/rules.d/49-supralinux-recovery.rules",
              "/usr/share/polkit-1/actions/com.supralinux.recovery.policy",
              "/usr/libexec/supralinux-recovery-helper",
              "/usr/local/sbin/supralinux-recover",
              "/etc/xdg/autostart/supralinux-recovery.desktop",
              "/usr/share/applications/supralinux-recovery.desktop",
              "/usr/share/applications/kubuntu-calamares.desktop")


def command(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE, timeout=30,
                                   env={**os.environ, "LC_ALL": "C"}).strip()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def zram_policy(meminfo, disksize, algorithms, swaps):
    match = re.search(r"^MemTotal:\s+(\d+)\s+kB$", meminfo, re.M)
    require(match is not None, "MemTotal missing")
    expected = min(int(match.group(1)) * 1024 / 2, 8192 * MIB)
    actual = int(disksize.strip())
    require(abs(expected - actual) <= 2 * MIB,
            f"Unexpected ZRAM capacity: {actual}, expected approximately {int(expected)}")
    require("[lz4]" in algorithms.split(), "LZ4 is not the selected ZRAM algorithm")
    rows = [line.split() for line in swaps.splitlines()[1:]]
    zram = [row for row in rows if row and row[0] == "/dev/zram0"]
    require(len(zram) == 1 and len(zram[0]) == 5 and int(zram[0][4]) == 100,
            "ZRAM swap missing or priority differs from 100")
    return {"capacity_bytes": actual, "expected_bytes": int(expected), "priority": 100}


def package_status(name):
    try:
        value = command("dpkg-query", "-W", "-f=${db:Status-Status}\t${Version}", name)
    except subprocess.CalledProcessError as exc:
        if exc.returncode == 1 and "no packages found" in exc.stderr:
            return "not-installed", ""
        raise
    return tuple(value.split("\t", 1))


def check(args):
    results = {}

    def run(name, fn):
        try:
            detail = fn()
            results[name] = {"status": "PASS", "detail": detail}
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
            results[name] = {"status": "FAIL", "error": str(exc)}

    def identity():
        values = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines()
                      if "=" in line and not line.startswith("#"))
        require(values.get("ID", "").strip('"') == "supralinux", "Wrong distribution")
        require(values.get("VERSION_ID", "").strip('"') == "26.04", "Ubuntu compatibility changed")
        require("boot=casper" not in Path("/proc/cmdline").read_text().split(), "Still in live boot")
        machine = Path("/etc/machine-id").read_text().strip()
        require(re.fullmatch(r"[0-9a-f]{32}", machine) and machine != "0" * 32, "Invalid machine-id")
        if args.live_machine_id:
            require(machine != args.live_machine_id, "Live and installed machine-id are identical")
        return {"machine_id": machine}

    def packages():
        require(not command("dpkg", "--audit"), "dpkg reports unfinished package operations")
        for name, version in args.expected:
            state, actual = package_status(name)
            require((state, actual) == ("installed", version),
                    f"{name}: expected installed {version}, got {state} {actual}")
        for name in LIVE_PACKAGES:
            state, _ = package_status(name)
            require(state in ("not-installed", "config-files"), f"Live-only package remains: {name}")
        for name in LIVE_PATHS:
            path = Path(name)
            require(not (path.exists() or path.is_symlink()), f"Live-only path remains: {name}")
        return dict(args.expected)

    def storage():
        root = command("findmnt", "-n", "-o", "FSTYPE,FSROOT", "--mountpoint", "/").split()
        require(root and root[0] == args.filesystem, f"Unexpected root filesystem: {root}")
        if args.filesystem == "btrfs":
            require(root == ["btrfs", "/@"], f"Unexpected root subvolume: {root}")
            for mount, subvol in (("/home", "/@home"), ("/.snapshots", "/@snapshots")):
                actual = command("findmnt", "-n", "-o", "FSTYPE,FSROOT", "--mountpoint", mount).split()
                require(actual == ["btrfs", subvol], f"Unexpected mount {mount}: {actual}")
            require(Path("/etc/snapper/configs/root").is_file(), "Missing Snapper root configuration")
            require(Path("/etc/apt/apt.conf.d/80snapper").is_file(), "Missing APT snapshot hook")
        efi = Path("/sys/firmware/efi").is_dir()
        require(efi == (args.mode == "uefi"), "Boot firmware differs from requested mode")
        if efi:
            require(command("findmnt", "-n", "-o", "FSTYPE", "--mountpoint", "/boot/efi") == "vfat",
                    "ESP not mounted as vfat")
            for name in ("shimx64.efi", "grubx64.efi", "grub.cfg"):
                path = Path("/boot/efi/EFI/supralinux") / name
                require(path.is_file() and path.stat().st_size > 0, f"Missing EFI file: {name}")
        kernel = command("uname", "-r")
        for prefix in ("vmlinuz-", "initrd.img-"):
            path = Path("/boot") / (prefix + kernel)
            require(path.is_file() and path.stat().st_size > 0, f"Missing boot file: {path}")
        command("grub-script-check", "/boot/grub/grub.cfg")
        return {"root": root, "firmware": args.mode, "running_kernel": kernel}

    def user():
        entry = pwd.getpwnam(args.user)
        require(entry.pw_uid >= 1000 and entry.pw_uid != 65534, "Invalid QA user UID")
        home = Path(entry.pw_dir)
        require(home.is_dir() and home.stat().st_uid == entry.pw_uid and home.stat().st_gid == entry.pw_gid,
                "QA user home ownership is incorrect")
        require("sudo" in command("id", "-nG", args.user).split(), "QA user missing sudo group")
        return {"uid": entry.pw_uid, "home": str(home)}

    def services():
        for unit in ("sddm.service", "systemd-resolved.service", "NetworkManager.service"):
            require(command("systemctl", "is-enabled", unit) == "enabled", f"{unit} not enabled")
            require(command("systemctl", "is-active", unit) == "active", f"{unit} not active")

    def archive():
        source = Path("/etc/apt/sources.list.d/supralinux.sources").read_text()
        require(re.search(r"^Suites:\s+testing\s*$", source, re.M), "Not the testing suite")
        require(re.search(r"^URIs:\s+https://repo\.supralinux\.com/\s*$", source, re.M),
                "Wrong archive URI (possible staging URL)")
        command("apt-cache", "policy")

    run("identity", identity)
    run("packages", packages)
    run("storage_and_boot", storage)
    run("user", user)
    run("services", services)
    run("archive", archive)
    run("zram", lambda: zram_policy(Path("/proc/meminfo").read_text(),
        Path("/sys/block/zram0/disksize").read_text(),
        Path("/sys/block/zram0/comp_algorithm").read_text(), Path("/proc/swaps").read_text()))
    return results


def expected_package(value):
    package, separator, version = value.partition("=")
    if not separator or not package or not version:
        raise argparse.ArgumentTypeError("Expected PACKAGE=VERSION")
    return package, version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["bios", "uefi"], required=True)
    parser.add_argument("--filesystem", choices=["btrfs", "ext4"], required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--live-machine-id")
    parser.add_argument("--expected", type=expected_package, action="append", required=True)
    args = parser.parse_args()
    names = [name for name, _ in args.expected]
    if len(names) != len(set(names)) or not {"supralinux-defaults", "supralinux-kdeconnect-sftp"} <= set(names):
        parser.error("Expected unique package versions including defaults and KDE Connect SFTP")
    results = check(args)
    success = all(result["status"] == "PASS" for result in results.values())
    print(json.dumps({"scope": "installed guest first boot", "status": "PASS" if success else "FAIL",
                      "checks": results}, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
