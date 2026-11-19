# Imagen live

## Alcance

La imagen live es la base del instalador y del entorno de recuperación. Se
construye desde Ubuntu 26.04 y el repositorio `testing` de SupraLINUX, y se
prueba en BIOS, UEFI y Secure Boot antes de publicarse.

## Requisitos

- `mmdebstrap`, `mksquashfs`, `xorriso`, `mtools` y `dosfstools`.
- En el rootfs: `grub-pc-bin`, `grub-efi-amd64-bin`, `grub-efi-amd64-signed`
  y `shim-signed`; de esos paquetes salen los binarios del live.
- Clave pública nueva del repositorio en
  `installer/keys/supralinux-archive-key.asc`. Sin ella, `setup-repo.sh`
  detiene el build.
- Clave pública de Mozilla en `installer/keys/packages.mozilla.org.asc`.
- Espacio para rootfs, squashfs e ISO.

```sh
WORKSPACE=${SUPRALINUX_WORKSPACE:-/mnt/RAID0/Proyectos/SupraLINUX-workspace}
REPO=${SUPRALINUX_REPO:-/mnt/RAID0/Proyectos/SupraLINUX}
LIVE=$WORKSPACE/live/1.0.0
ROOTFS=$LIVE/rootfs
export SUPRALINUX_APT_CHANNEL=testing
```

## Rootfs

`setup-repo.sh` instala las claves, las fuentes APT y el remoto de Flathub.
Elige `supralinux-testing.sources` o `supralinux-stable.sources` según
`SUPRALINUX_APT_CHANNEL`.

`SUPRALINUX_APT_BUILD_URL` permite instalar desde un mirror de staging, por
ejemplo el Aptly local en `http://127.0.0.1:18080/`. El rootfs usa esa URL
durante el build y, antes de sellarse, restaura la fuente pública de
`supralinux-*.sources`. La ISO no queda apuntando al mirror temporal.

`customize-rootfs.sh` instala el escritorio desde
`packages/desktop/desktop-packages.list`, configura SDDM, locale, teclado,
KWallet, red, RAID, los hooks de casper y la recuperación.

```sh
unshare --map-users=0:100000:65536 --map-groups=0:100000:65536 \
  --setuid=0 --setgid=0 \
  mmdebstrap --mode=unshare --variant=minbase \
  --components=main,universe,restricted,multiverse \
  --include=linux-image-generic,casper,squashfs-tools,systemd-sysv,initramfs-tools,sudo,dbus,polkitd,pkexec,fonts-dejavu-core,libgl1-mesa-dri,network-manager,ca-certificates,xkb-data,console-setup,keyboard-configuration,qemu-guest-agent \
  --setup-hook="$REPO/tools/live/setup-repo.sh" \
  --customize-hook="$REPO/tools/live/customize-rootfs.sh" \
  resolute "$ROOTFS"
```

La versión exacta del kernel se fija en el manifiesto del build. No se instala
`calamares-settings-kubuntu`; la configuración viene de
`supralinux-calamares-config` y la identidad de `supralinux-base-files`.

## Sellado

`seal-rootfs.sh` verifica la identidad instalada, limpia listas y cachés de APT,
borra homes y logs de build, deja los puntos de montaje vacíos y conserva
`/boot` cuando la ISO también lleva el instalador.

```sh
SUPRALINUX_LIVE_DIR="$LIVE" SUPRALINUX_KEEP_BOOT=1 \
  sh "$REPO/tools/live/seal-rootfs.sh" "$ROOTFS"
```

No se reescriben `os-release`, `lsb-release`, `issue` ni `legal`: los posee
`supralinux-base-files` con `dpkg-divert`. Si el paquete no está instalado, el
sellado falla.

## Squashfs e ISO

`build-iso.sh` copia kernel e initramfs, sella el rootfs, crea el squashfs y
compone la ISO híbrida con `xorriso`.

```sh
SUPRALINUX_LIVE_DIR="$LIVE" \
unshare --map-users=0:100000:65536 --map-groups=0:100000:65536 \
  --setuid=0 --setgid=0 \
  sh "$REPO/tools/live/build-iso.sh" "$ROOTFS"
```

Salida por defecto:

```text
$LIVE/build/supralinux-aurora-1.0.0-amd64.iso
$LIVE/build/supralinux-aurora-1.0.0-amd64.iso.sha256
```

`SUPRALINUX_ISO_NAME` permite un nombre de prueba. `SUPRALINUX_SIGNING_KEY`
firma el checksum. El squashfs usa `-all-time 0`, `-xattrs`, `zstd` y pseudo
nodos para `/dev`; no se usa `-all-root`.

El árbol `$LIVE/build/iso` conserva el tema GRUB, `casper/`, la ESP firmada y
`md5sum.txt`. `secureboot-efi.sh` recompone la ESP y la ISO desde ese árbol sin
rehacer el squashfs.

## Secure Boot

La ISO usa `shimx64.efi.signed.latest` y `gcdx64.efi.signed` de Ubuntu. No se
introduce una clave UEFI propia. El menú conserva una entrada normal, una de
safe graphics, una de recuperación y una de debug.

La cadena y las pruebas están en [secure-boot.md](secure-boot.md).

## Prueba

BIOS:

```sh
qemu-system-x86_64 -machine q35,accel=kvm -cpu host -m 6144 -smp 4 \
  -cdrom "$LIVE/build/supralinux-aurora-1.0.0-amd64.iso" -boot d -nic none \
  -vga virtio -display none \
  -chardev socket,id=qga0,path="$RUN/qga.sock",server=on,wait=off \
  -device virtio-serial-pci \
  -device virtserialport,chardev=qga0,name=org.qemu.guest_agent.0 \
  -monitor unix:"$RUN/monitor.sock",server=on,wait=off \
  -serial file:"$RUN/console.log" -no-reboot
```

UEFI Secure Boot:

```sh
qemu-system-x86_64 -machine q35,accel=kvm -cpu host -m 6144 -smp 4 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd \
  -drive if=pflash,format=raw,file="$RUN/OVMF_VARS_4M.ms.fd" \
  -cdrom "$LIVE/build/supralinux-aurora-1.0.0-amd64.iso" -boot d -nic none \
  -vga virtio -display none \
  -chardev socket,id=qga0,path="$RUN/qga.sock",server=on,wait=off \
  -device virtio-serial-pci \
  -device virtserialport,chardev=qga0,name=org.qemu.guest_agent.0 \
  -monitor unix:"$RUN/monitor.sock",server=on,wait=off \
  -serial file:"$RUN/console.log" -no-reboot
```

Comprobaciones:

- `md5sum -c /cdrom/md5sum.txt`.
- `mokutil --sb-state` y el efivar `SecureBoot` valen `1` en Secure Boot.
- Sesión `plasma.desktop` en Wayland, `kwin_wayland`, XWayland, `plasmashell`
  y `systemsettings`.
- `supralinux-base-files` presente y `ID=supralinux`.
- Firefox abre y tiene español.
- Calamares abre y ve los discos.
- La entrada Recovery arranca en multi-user y permite `supralinux-recover`.

La matriz completa y los estados están en [testing.md](testing.md).

## Estado en el repo nuevo

Las herramientas y la configuración están incorporadas. La ISO de 1.0.0 se
construye y valida cuando existan la clave nueva del repositorio, los paquetes
publicados en `testing` y la imagen base del builder. Hasta entonces no se
declara un PASS de ISO.
