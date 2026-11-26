#!/bin/sh
# Compose one testing candidate using the existing mapped-root live builder.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
if [ "$#" -ne 2 ]; then
    echo "Usage: sh tools/live/build-testing-iso.sh NEW_LIVE_DIR STAGED_DEB_DIR" >&2
    exit 2
fi
live=$(realpath -m "$1")
stage=$(realpath "$2")
case "$live:$stage" in *[[:space:]]*) echo "Paths must not contain whitespace" >&2; exit 2;; esac
test ! -e "$live"
test -f "$stage/overlays.json"
test "$(uname -m)" = x86_64
for cmd in mmdebstrap mksquashfs xorriso mcopy mkfs.vfat unshare python3 dpkg-query setpriv; do
    command -v "$cmd" >/dev/null
done
# Only create a fresh output directory. Never reuse/delete an existing rootfs.
mkdir -p "$(dirname "$live")"
free=$(df -Pk "$(dirname "$live")" | awk 'NR==2 {print $4}')
if [ "$free" -lt 23068672 ]; then
    echo "INFRA_INVALID: at least 22 GiB free is required for live build" >&2
    exit 1
fi
debs=
for deb in "$stage"/*.deb; do
    test -r "$deb"
    debs="$debs $deb"
done
# Do not change permissions on the runner's home or other host directories.
# Test traversal using the exact mapped uid/gid before entering the namespace.
cd "$repo"
mapped_test() {
    sudo setpriv --reuid=100000 --regid=100000 --clear-groups -- test "$@"
}
if ! mapped_test -x "$repo" || ! mapped_test -r "$repo/tools/live/setup-repo.sh" ||
   ! mapped_test -x "$(dirname "$live")" || ! mapped_test -r "$stage/overlays.json"; then
    echo "INFRA_INVALID: namespace uid/gid 100000 cannot access source or workspace" >&2
    exit 1
fi
for deb in "$stage"/*.deb; do
    if ! mapped_test -r "$deb"; then
        echo "INFRA_INVALID: mapped uid cannot read overlay: $deb" >&2
        exit 1
    fi
done
sudo install -d -o 100000 -g 100000 -m 0755 "$live"
sudo env HOME=/tmp SUPRALINUX_LIVE_DIR="$live" SUPRALINUX_APT_CHANNEL=testing \
    SUPRALINUX_LOCAL_DEBS="$debs" SUPRALINUX_REQUIRE_RECOVERY_GUI=1 \
    unshare --map-users=0:100000:65536 --map-groups=0:100000:65536 \
    --setuid=0 --setgid=0 \
    mmdebstrap --mode=unshare --variant=minbase \
    --components=main,universe,restricted,multiverse \
    --include=linux-image-generic=7.0.0-44.44,casper,squashfs-tools,systemd-sysv,initramfs-tools,sudo,dbus,polkitd,pkexec,fonts-dejavu-core,libgl1-mesa-dri,network-manager,ca-certificates,xkb-data,console-setup,keyboard-configuration,qemu-guest-agent \
    --setup-hook="$repo/tools/live/setup-repo.sh" \
    --customize-hook="$repo/tools/live/customize-rootfs.sh" \
    resolute "$live/rootfs" \
    "deb http://archive.ubuntu.com/ubuntu resolute main universe restricted multiverse" \
    "deb http://archive.ubuntu.com/ubuntu resolute-updates main universe restricted multiverse" \
    "deb http://security.ubuntu.com/ubuntu resolute-security main universe restricted multiverse"
sudo env HOME=/tmp SUPRALINUX_LIVE_DIR="$live" SUPRALINUX_APT_CHANNEL=testing \
    unshare --map-users=0:100000:65536 --map-groups=0:100000:65536 \
    --setuid=0 --setgid=0 sh "$repo/tools/live/build-iso.sh" "$live/rootfs"
