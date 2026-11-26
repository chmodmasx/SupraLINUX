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
printf '<snapshot><type>single</type><date>%s</date><description>QA baseline</description></snapshot>\n' "$(date -u +%F)" > "$mountpoint/@snapshots/1/info.xml"
printf 'changed\n' > "$mountpoint/@/root-marker"
sync
umount "$mountpoint"
helper=${SUPRA_QA_RECOVERY_HELPER:-/usr/local/sbin/supralinux-recover}
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
test -z "$(find "$mountpoint" -maxdepth 1 -name '@rollback-*' -print -quit)"
echo 'ROLLBACK_PASS: root restored, home unchanged, snapshot and prior root retained'
