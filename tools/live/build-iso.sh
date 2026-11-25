#!/bin/sh
# Build the signed SupraLINUX live/installer ISO from a prepared rootfs.
# The EFI image uses the shim and GRUB signed by Ubuntu/Microsoft; the ISO
# works with Secure Boot enabled or disabled.
# Run as mapped root with sudo, for example:
#   sudo env SUPRALINUX_LIVE_DIR=/path/to/live \
#       unshare --map-users=0:100000:65536 --map-groups=0:100000:65536 \
#       --setuid=0 --setgid=0 sh tools/live/build-iso.sh /path/to/rootfs
# sudo is required because AppArmor blocks unprivileged user namespaces.
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "build-iso.sh must run as root inside the subuid namespace" >&2
    exit 1
fi

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
. "$repo_root/tools/live/iso-lib.sh"

workspace=$(dirname -- "$repo_root")
live=${SUPRALINUX_LIVE_DIR:-$workspace/live/1.0.0}
root=${1:-$live/rootfs}
iso=$live/build/iso

test -d "$root"
if [ -n "${SUPRALINUX_ISO_NAME:-}" ]; then
    output=$SUPRALINUX_ISO_NAME
else
    output=$(iso_candidate_path "$root" "$repo_root" "$live/build")
fi
if [ "$(stat -c %u "$root")" -ne "$(id -u)" ] || [ "$(stat -c %g "$root")" -ne "$(id -g)" ]; then
    echo "Rootfs ownership does not match the current uid/gid." >&2
    echo "Run inside the documented unshare mapping, not as real root." >&2
    exit 1
fi
test -s "$root/boot/vmlinuz"
test -s "$root/boot/initrd.img"

# Reject missing or stale inventory binaries before modifying the rootfs.
python3 "$repo_root/tools/live/verify-packages.py" "$root"

rm -rf "$iso"
mkdir -p "$iso/casper" "$iso/boot/grub" "$iso/.disk"
mkdir -p "$iso/boot/grub/themes/supralinux"
cp -a "$repo_root/branding/grub/supralinux/." \
    "$iso/boot/grub/themes/supralinux/"
# Keep preserved ISOs and build logs untouched; the mapped root only needs
# write access to the working ISO tree and to the output directory itself.
build_mode=$(stat -c '%a' "$live/build")
restore_build_mode() {
    chmod "$build_mode" "$live/build" 2>/dev/null || true
}
trap restore_build_mode EXIT
chmod 0777 "$live/build"

cp "$root/boot/vmlinuz" "$iso/casper/vmlinuz"
cp "$root/boot/initrd.img" "$iso/casper/initrd.img"
chmod 0644 "$iso/casper/vmlinuz" "$iso/casper/initrd.img"

SUPRALINUX_LIVE_DIR="$live" SUPRALINUX_KEEP_BOOT=1 \
    sh "$repo_root/tools/live/seal-rootfs.sh" "$root"

# Casper runs its bottom scripts before init-bottom moves /dev into the live
# root.  The mmdebstrap root has an empty /dev, so /dev/null and the other
# basic nodes must exist in the squashfs for the chroot phase.  Device nodes
# cannot be created from the mapped-root build (mknod returns EPERM); add them
# as mksquashfs pseudo files instead.  The live system later mounts devtmpfs
# over /dev, so these nodes are only used by the initramfs chroot.
mksquashfs "$root" "$iso/casper/filesystem.squashfs" \
    -noappend -all-time 0 -xattrs -comp zstd -Xcompression-level 6 \
    -processors 4 \
    -p "dev/null c 666 0 0 1 3" \
    -p "dev/zero c 666 0 0 1 5" \
    -p "dev/full c 666 0 0 1 7" \
    -p "dev/random c 666 0 0 1 8" \
    -p "dev/urandom c 666 0 0 1 9" \
    -p "dev/tty c 666 0 5 5 0" \
    -p "dev/console c 600 0 5 5 1" \
    -p "dev/ptmx c 666 0 5 5 2" \
    -p "dev/pts d 755 0 0" \
    -p "dev/shm d 1777 0 0" \
    -e var/cache/apt/archives -e mnt -e media -e lost+found

stat -c '%s' "$iso/casper/filesystem.squashfs" > "$iso/casper/filesystem.size"
chroot "$root" dpkg-query -W -f='${Package}\t${Version}\n' \
    > "$iso/casper/filesystem.manifest"

cat > "$iso/boot/grub/grub.cfg" <<'GRUB'
set default=0
set timeout=5

# Under UEFI Secure Boot the signed GRUB only trusts modules and fonts
# embedded in its signed image.  Loading the external gfxmenu/gfxterm modules
# or the SupraLINUX fonts would print "prohibited by secure boot policy" and
# can leave the menu in an inconsistent state.  Keep the branded graphical
# menu for BIOS and non-Secure-Boot UEFI, and use the built-in text console
# when shim_lock is active.
if [ "$shim_lock" != "y" ]; then
    insmod gfxmenu
    insmod gfxterm
    insmod png
    # all_video loads the VBE/GOP driver. Without it, gfxmode=auto fails with
    # "no suitable video mode found" on some BIOS and UEFI firmware.
    insmod all_video
    loadfont /boot/grub/themes/supralinux/unifont-regular-16.pf2
    loadfont /boot/grub/themes/supralinux/unifont-bold-16.pf2
    set gfxmode=1920x1080,1600x900,1280x720,1024x768,800x600,640x480
    terminal_output gfxterm
    set theme=($root)/boot/grub/themes/supralinux/theme.txt
    export theme
fi

menuentry "SupraLINUX Aurora 1.0.0 Live" --class ubuntu --class gnu-linux --class os {
    linux /casper/vmlinuz boot=casper noswap quiet splash console=tty0 console=ttyS0,115200 ---
    initrd /casper/initrd.img
}
menuentry "SupraLINUX Aurora 1.0.0 Live (safe graphics)" --class ubuntu --class gnu-linux --class os {
    linux /casper/vmlinuz boot=casper noswap nomodeset quiet splash console=tty0 console=ttyS0,115200 ---
    initrd /casper/initrd.img
}
menuentry "SupraLINUX Aurora Recovery (Btrfs rollback)" --class recovery --class os {
    linux /casper/vmlinuz boot=casper noswap quiet splash supralinux.recovery=1 console=tty0 console=ttyS0,115200 ---
    initrd /casper/initrd.img
}
menuentry "SupraLINUX Aurora 1.0.0 Live (debug)" --class ubuntu --class gnu-linux --class os {
    linux /casper/vmlinuz boot=casper noswap debug systemd.log_level=debug console=tty0 console=ttyS0,115200 ---
    initrd /casper/initrd.img
}
GRUB

printf 'SupraLINUX Aurora 1.0.0 amd64 - Plasma 6.6.7\n' > "$iso/.disk/info"
printf 'https://supralinux.com/\n' > "$iso/.disk/release_notes_url"

# GRUB payloads come from the same packages the installed system will use.
# The host only supplies generic tools (xorriso, mkfs.vfat, mcopy).
iso_install_grub_bios "$root" "$iso"
iso_write_efi_stub "$iso"
iso_create_efi_signed "$root" "$iso"
iso_verify_grub_bios "$root" "$iso"
iso_make_md5sum "$iso"
iso_make_image "$iso" "$output"

# The checksum is part of the deliverable: keep only the file name so it can be
# verified from any directory, and never leave a stale signature behind.
(
    cd "$(dirname "$output")"
    sha256sum "$(basename "$output")" > "$(basename "$output").sha256"
)
rm -f "$output.sha256.asc"
if [ -n "${SUPRALINUX_SIGNING_KEY:-}" ]; then
    gpg --batch --yes --local-user "$SUPRALINUX_SIGNING_KEY" --armor \
        --detach-sign --output "$output.sha256.asc" "$output.sha256"
fi
cat "$output.sha256"
