#!/bin/sh
# Check the host commands needed by the SupraLINUX build and validation flow.
set -u

missing=0

check_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        printf 'Falta: %-24s (%s)\n' "$1" "$2"
        missing=1
    fi
}

check_command qemu-system-x86_64 "qemu-system-x86"
check_command qemu-img "qemu-utils"
check_command mmdebstrap "mmdebstrap"
check_command mksquashfs "squashfs-tools"
check_command xorriso "xorriso"
check_command mkfs.vfat "dosfstools"
check_command mmd "mtools"
check_command mcopy "mtools"
check_command dpkg-source "dpkg-dev"
check_command dpkg-deb "dpkg-dev"
check_command dpkg-scanpackages "dpkg-dev"
check_command gpg "gnupg"
check_command gpgv "gpgv"
check_command mkfs.ext4 "e2fsprogs"
check_command e2fsck "e2fsprogs"
check_command convert "imagemagick"
check_command msgfmt "gettext"
check_command git "git"
check_command python3 "python3"
check_command rsync "rsync"
check_command ssh "openssh-client"
check_command curl "curl"
check_command unshare "util-linux"

if [ ! -r /dev/kvm ]; then
    echo "Falta: /dev/kvm (usuario en el grupo kvm y virtualización habilitada)"
    missing=1
fi

if [ ! -r /usr/share/OVMF/OVMF_CODE_4M.fd ]; then
    echo "Falta: /usr/share/OVMF/OVMF_CODE_4M.fd (paquete ovmf)"
    missing=1
fi
if [ ! -r /usr/share/OVMF/OVMF_CODE_4M.secboot.fd ]; then
    echo "Falta: /usr/share/OVMF/OVMF_CODE_4M.secboot.fd (paquete ovmf)"
    missing=1
fi

if [ "$missing" -eq 0 ]; then
    echo "Host listo para construir y validar SupraLINUX."
fi
exit "$missing"
