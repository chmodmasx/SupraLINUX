#!/bin/sh
# Rebuild the signed EFI image and ISO from an existing build/iso tree.
# build-iso.sh already produces the signed ISO; this helper is only for
# repairs or for rebuilding the EFI image without redoing the squashfs.
# Run as mapped root:
#   unshare --map-users=0:100000:65536 --map-groups=0:100000:65536 \
#       --setuid=0 --setgid=0 sh tools/live/secureboot-efi.sh \
#       /path/to/rootfs [/path/to/output.iso]
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
. "$repo_root/tools/live/iso-lib.sh"

root=${1:?rootfs}
workspace=$(dirname -- "$repo_root")
live=${SUPRALINUX_LIVE_DIR:-$workspace/live/1.0.0}
iso_tree=$live/build/iso
output=${2:-${SUPRALINUX_ISO_NAME:-$live/build/supralinux-aurora-1.0.0-amd64.iso}}

test -d "$root"
if [ "$(stat -c %u "$root")" -ne "$(id -u)" ] || [ "$(stat -c %g "$root")" -ne "$(id -g)" ]; then
    echo "Rootfs ownership does not match the current uid/gid." >&2
    echo "Run inside the documented unshare mapping, not as real root." >&2
    exit 1
fi
test -d "$iso_tree"
test -f "$iso_tree/boot/grub/grub.cfg"

chmod 0777 "$live/build"

iso_install_grub_bios "$root" "$iso_tree"
iso_write_efi_stub "$iso_tree"
iso_create_efi_signed "$root" "$iso_tree"
iso_verify_grub_bios "$root" "$iso_tree"
iso_make_md5sum "$iso_tree"
iso_make_image "$iso_tree" "$output"
(
    cd "$(dirname "$output")"
    sha256sum "$(basename "$output")" > "$(basename "$output").sha256"
)
rm -f "$output.sha256.asc"
cat "$output.sha256"
