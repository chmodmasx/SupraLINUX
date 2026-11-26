set -eux
lsblk -o NAME,TYPE,SIZE,FSTYPE,SERIAL,MOUNTPOINTS
test -b /dev/disk/by-id/virtio-SUPRAQA-INSTALL
test "$(readlink -f /dev/disk/by-id/virtio-SUPRAQA-INSTALL)" = /dev/vda
# zram is reported as a disk by lsblk, but is not an installation target.
test "$(lsblk -dn -o NAME,TYPE | awk '$2 == "disk" && $1 !~ /^zram[0-9]+$/ {print $1}')" = vda
test "$(lsblk -bdn -o SIZE /dev/vda)" = 42949672960
test "$(lsblk -rn -o NAME /dev/vda | wc -l)" -eq 1
test -z "$(lsblk -dn -o FSTYPE /dev/vda)"
test "$(lsblk -dn -o SERIAL /dev/vda | tr -d ' ')" = SUPRAQA-INSTALL
if findmnt -rn -S /dev/vda; then exit 1; fi
