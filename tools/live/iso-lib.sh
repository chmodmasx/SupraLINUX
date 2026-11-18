#!/bin/sh
# Shared live-ISO GRUB assembly helpers.
#
# Every GRUB payload copied into the ISO comes from the rootfs packages that
# will be installed (grub-pc-bin, grub-efi-amd64-bin, grub-efi-amd64-signed,
# shim-signed).  The build host only provides generic tools such as xorriso,
# mcopy and mkfs.vfat.  Never read /boot/grub or /usr/lib/grub from the host.

iso_install_grub_bios() {
    root=$1
    iso=$2
    grubdir=$root/usr/lib/grub/i386-pc

    test -f "$grubdir/eltorito.img"
    test -f "$grubdir/boot_hybrid.img"

    install -d -m 0755 "$iso/boot/grub/i386-pc"
    for pattern in '*.mod' '*.lst' '*.o'; do
        for file in "$grubdir"/$pattern; do
            [ -e "$file" ] || continue
            cp -a "$file" "$iso/boot/grub/i386-pc/"
        done
    done
    cp -a "$grubdir/eltorito.img" "$grubdir/boot_hybrid.img" \
        "$iso/boot/grub/i386-pc/"
    chmod -R u+w "$iso/boot/grub/i386-pc"
}

iso_write_efi_stub() {
    iso=$1

    install -d -m 0755 "$iso/EFI/BOOT" "$iso/EFI/ubuntu"
    cat > "$iso/EFI/BOOT/grub.cfg" <<'GRUB'
search --file --set=root /casper/vmlinuz
set prefix=($root)/boot/grub
configfile ($root)/boot/grub/grub.cfg
GRUB
    cp "$iso/EFI/BOOT/grub.cfg" "$iso/EFI/ubuntu/grub.cfg"
}

iso_create_efi_signed() {
    root=$1
    iso=$2
    efi=$iso/efi.img
    shim=$root/usr/lib/shim/shimx64.efi.signed.latest
    grub=$root/usr/lib/grub/x86_64-efi-signed/gcdx64.efi.signed
    mm=$root/usr/lib/shim/mmx64.efi
    gcd=$root/usr/lib/grub/x86_64-efi-signed/gcdx64.efi.signed

    if [ ! -s "$shim" ]; then
        rel=$(chroot "$root" readlink -f /usr/lib/shim/shimx64.efi.signed)
        shim=$root$rel
    fi
    [ -s "$grub" ] || grub=$root/usr/lib/grub/x86_64-efi-signed/grubx64.efi.signed
    test -s "$shim"
    test -s "$grub"
    test -s "$mm"

    rm -f "$efi"
    dd if=/dev/zero of="$efi" bs=1M count=16 status=none
    mkfs.vfat -F 16 -n SUPRAEFI "$efi" >/dev/null
    mmd -i "$efi" ::EFI ::EFI/BOOT ::EFI/ubuntu

    mcopy -o -i "$efi" "$shim" ::EFI/BOOT/BOOTX64.EFI
    mcopy -o -i "$efi" "$grub" ::EFI/BOOT/grubx64.efi
    mcopy -o -i "$efi" "$mm" ::EFI/BOOT/mmx64.efi
    mcopy -o -i "$efi" "$iso/EFI/BOOT/grub.cfg" ::EFI/BOOT/grub.cfg

    mcopy -o -i "$efi" "$shim" ::EFI/ubuntu/shimx64.efi
    mcopy -o -i "$efi" "$grub" ::EFI/ubuntu/grubx64.efi
    mcopy -o -i "$efi" "$mm" ::EFI/ubuntu/mmx64.efi
    mcopy -o -i "$efi" "$iso/EFI/ubuntu/grub.cfg" ::EFI/ubuntu/grub.cfg
    if [ -s "$gcd" ]; then
        mcopy -o -i "$efi" "$gcd" ::EFI/ubuntu/gcdx64.efi
    fi
}

iso_verify_grub_bios() {
    root=$1
    iso=$2

    for file in eltorito.img boot_hybrid.img; do
        cmp "$iso/boot/grub/i386-pc/$file" \
            "$root/usr/lib/grub/i386-pc/$file"
    done
    for pattern in '*.mod' '*.lst' '*.o'; do
        for file in "$root/usr/lib/grub/i386-pc"/$pattern; do
            [ -e "$file" ] || continue
            cmp "$iso/boot/grub/i386-pc/$(basename "$file")" "$file"
        done
    done
}

iso_make_md5sum() {
    iso=$1

    (
        cd "$iso"
        find . -type f ! -name md5sum.txt \
            ! -path './boot/grub/i386-pc/eltorito.img' -print0 |
            sort -z | xargs -0 md5sum > md5sum.txt
    )
}

iso_make_image() {
    iso=$1
    output=$2

    cd "$iso"
    xorriso -as mkisofs -r -J -joliet-long -l -V SUPRALINUX -iso-level 3 \
        -b boot/grub/i386-pc/eltorito.img \
        -no-emul-boot -boot-load-size 4 -boot-info-table --grub2-boot-info \
        --grub2-mbr boot/grub/i386-pc/boot_hybrid.img \
        -append_partition 2 0xef efi.img \
        -appended_part_as_gpt --mbr-force-bootable \
        -eltorito-alt-boot -e --interval:appended_partition_2:all:: \
        -no-emul-boot -partition_offset 16 \
        -o "$output" .
}
