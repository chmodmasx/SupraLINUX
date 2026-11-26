set -eu
. /etc/os-release
test "$ID" = supralinux
test -d /cdrom/casper
# Synthetic fixture only: do not mount, format or modify any other disk.
dev=/dev/disk/by-id/virtio-SUPRAQA-EXCHANGE
test -b "$dev"
test "$(readlink -f "$dev")" = /dev/vda
test "$(lsblk -dn -o SERIAL "$dev" | tr -d ' ')" = SUPRAQA-EXCHANGE
test "$(lsblk -bdn -o SIZE "$dev")" = 4294967296
test "$(lsblk -rn -o NAME "$dev" | wc -l)" -eq 1
test -z "$(lsblk -dn -o FSTYPE "$dev")"
test "$(lsblk -dn -o NAME,TYPE | awk '$2 == "disk" && $1 !~ /^zram[0-9]+$/ {print $1}')" = vda
if findmnt -rn -S /dev/vda >/dev/null; then exit 1; fi
mkfs.btrfs -q "$dev"
top=$(mktemp -d /run/supra-exchange.XXXXXX)
trap 'umount "$top" 2>/dev/null || true; rmdir "$top" 2>/dev/null || true' EXIT
mount -o subvolid=5 "$dev" "$top"
btrfs subvolume create "$top/@"
btrfs subvolume create "$top/@home"
btrfs subvolume create "$top/@snapshots"
printf 'original\n' > "$top/@/root-marker"
printf 'unchanged\n' > "$top/@home/home-marker"
mkdir "$top/@snapshots/1"
btrfs subvolume snapshot -r "$top/@" "$top/@snapshots/1/snapshot"
printf 'changed\n' > "$top/@/root-marker"
btrfs subvolume snapshot "$top/@snapshots/1/snapshot" "$top/@rollback-fixture"
sync
# Probe Linux renameat2(RENAME_EXCHANGE) support on sibling Btrfs subvolumes.
# No fallback to the known two-rename gap. This is not the recovery backend.
python3 - "$top" <<'PY'
import ctypes, os, sys
libc = ctypes.CDLL(None, use_errno=True)
exchange = libc.renameat2
exchange.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
exchange.restype = ctypes.c_int
fd = os.open(sys.argv[1], os.O_RDONLY | os.O_DIRECTORY)
try:
    if exchange(fd, b"@", fd, b"@rollback-fixture", 2) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err))
    os.fsync(fd)
finally:
    os.close(fd)
PY
btrfs filesystem sync "$top"
umount "$top"
mount -o subvolid=5 "$dev" "$top"
# A clean remount after exchange, before naming the old root: both roots survive.
test "$(cat "$top/@/root-marker")" = original
test "$(cat "$top/@rollback-fixture/root-marker")" = changed
test "$(cat "$top/@home/home-marker")" = unchanged
test "$(cat "$top/@snapshots/1/snapshot/root-marker")" = original
mv "$top/@rollback-fixture" "$top/@pre-rollback-fixture"
btrfs filesystem sync "$top"
umount "$top"
mount -o subvolid=5 "$dev" "$top"
test "$(cat "$top/@/root-marker")" = original
test "$(cat "$top/@pre-rollback-fixture/root-marker")" = changed
test "$(cat "$top/@home/home-marker")" = unchanged
echo 'ATOMIC_EXCHANGE_PASS: sibling subvolumes exchanged, both roots and home survive clean remount'
