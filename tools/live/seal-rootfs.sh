#!/bin/sh
# Finalize the live rootfs before squashfs creation. Run as mapped root when
# the rootfs is owned by a subuid range (mmdebstrap --mode=unshare).
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
workspace=$(dirname -- "$repo_root")
live=${SUPRALINUX_LIVE_DIR:-$workspace/live/1.0.0}
root=${1:-$live/rootfs}
host=${SUPRALINUX_LIVE_HOST:-supralinux}

# QGA starts on demand from 60-qemu-guest-agent.rules when the virtio port
# exists. Keep it out of multi-user.target.wants: on bare metal BindsTo= points
# at a device that never appears and the target waits DefaultDeviceTimeoutSec
# (90 s), which delayed power-profiles-daemon and the desktop session.
rm -f "$root/etc/systemd/system/multi-user.target.wants/qemu-guest-agent.service"

# The identity comes from supralinux-base-files. Do not rewrite it here:
# that package owns the files and keeps base-files diverted.
test -s "$root/usr/lib/os-release"
grep -qx 'ID=supralinux' "$root/usr/lib/os-release"
grep -qx 'VERSION_ID="26.04"' "$root/usr/lib/os-release"
test -s "$root/etc/lsb-release"
test -L "$root/etc/os-release"
test -x "$root/etc/update-motd.d/10-help-text"

# A lost setuid bit breaks pkexec, sudo and the live installer. These tools
# must keep the modes shipped by their packages.
for path in usr/bin/pkexec usr/bin/sudo.ws usr/bin/su \
            usr/bin/mount usr/bin/umount usr/bin/passwd; do
    [ -e "$root/$path" ] || continue
    mode=$(stat -c '%a' "$root/$path")
    case "$mode" in
        4755) ;;
        *)
            echo "ERROR: $path has mode $mode; expected 4755." >&2
            exit 1
            ;;
    esac
done

# Do not let a login fetch Ubuntu's motd news in the live image.
rm -f "$root/etc/update-motd.d/50-motd-news"
chroot "$root" systemctl disable motd-news.timer >/dev/null 2>&1 || true
rm -f "$root/etc/systemd/system/timers.target.wants/motd-news.timer"

# Fresh identity on every live boot.
: > "$root/etc/machine-id"
rm -f "$root/var/lib/dbus/machine-id" "$root/var/lib/systemd/random-seed"
rm -rf "$root/var/lib/apt/lists"/* "$root/var/cache/apt/archives"/* "$root/var/cache/apt"/*.bin
rm -rf "$root/tmp"/* "$root/var/tmp"/*
find "$root/var/log" -mindepth 1 -maxdepth 1 ! -name journal -exec rm -rf {} + 2>/dev/null || true
# samba does not create its log directory; smbd/nmbd fail to log without it.
install -d -m 0770 "$root/var/log/samba"
rm -f "$root/root/.bash_history"
rm -rf "$root/root/.cache" "$root/root/.config" "$root/root/.local"
# Live user homes are created by casper at boot. Do not ship build-user or
# host homes (for example the user that ran chroot or Calamares checks).
if [ -d "$root/home" ]; then
    find "$root/home" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
fi

# The squashfs must contain the empty mount points; casper mounts /dev,
# /proc, /sys and /run over them during early boot. /boot is preserved when
# the image also carries the installer, because the installed system needs a
# kernel and initramfs.
for directory in proc sys dev run tmp var/tmp; do
    mkdir -p "$root/$directory"
    find "$root/$directory" -mindepth 1 -delete 2>/dev/null || true
done
if [ "${SUPRALINUX_KEEP_BOOT:-0}" = 1 ]; then
    test -s "$root/boot/vmlinuz"
    test -s "$root/boot/initrd.img"
else
    mkdir -p "$root/boot"
    find "$root/boot" -mindepth 1 -delete 2>/dev/null || true
fi
mkdir -p "$root/var/cache/apt/archives/partial" "$root/var/lib/apt/lists/partial"

chroot "$root" dpkg-query -W -f='${Package}\t${Version}\n' \
    sddm plasma-session-wayland plasma-desktop plasma-workspace \
    kwin-wayland systemsettings breeze kf6-breeze-icon-theme \
    qemu-guest-agent pipewire pipewire-pulse wireplumber \
    libspa-0.2-modules calamares supralinux-calamares-config supralinux-base-files \
    grub-efi-amd64-signed shim-signed grub-pc-bin btrfs-progs snapper \
    rsync sddm-theme-breeze \
    > "$root/var/lib/supralinux-live-packages.txt"

cat "$root/var/lib/supralinux-live-packages.txt"
du -sh "$root"
ls -l "$root/usr/share/wayland-sessions/plasma.desktop" \
      "$root/usr/bin/startplasma-wayland" "$root/usr/bin/kwin_wayland"
