# Herramientas del host

Lista de lo necesario para construir y validar SupraLINUX desde un equipo Linux.
No se instala nada automáticamente: `tools/check-host.sh` sólo informa.

## Instalación

Con autorización explícita para el host:

```sh
sudo apt install \
  qemu-system-x86 qemu-utils ovmf \
  mmdebstrap squashfs-tools xorriso mtools dosfstools \
  dpkg-dev gnupg gpgv e2fsprogs util-linux rsync \
  imagemagick fonts-dejavu-core gettext \
  python3 git curl openssh-client xz-utils zstd ca-certificates
```

Añadir `shellcheck` si se quieren revisar los scripts. El usuario que ejecute
QEMU debe pertenecer al grupo `kvm`.

## Grupos

| Grupo | Herramientas | Uso |
|---|---|---|
| Virtualización | `qemu-system-x86_64`, `qemu-img`, `ovmf` | Builds y pruebas BIOS/UEFI/Secure Boot. |
| Rootfs live | `mmdebstrap`, `apt`, `dpkg` | Construir el rootfs desde Ubuntu y el repositorio. |
| ISO | `mksquashfs`, `xorriso`, `mtools`, `dosfstools` | Squashfs, ISO híbrida y ESP. |
| Firma | `gpg`, `gpgv` | Firmar y verificar el repositorio. |
| Empaquetado | `dpkg-source`, `dpkg-deb`, `dpkg-scanpackages`, `dpkg-query` | Fuentes, binarios e índices. |
| Validación | `qemu`, `convert`, `fonts-dejavu-core` | Capturas y evidencia. |
| Traducciones | `msgfmt` | Catálogos de Calamares y de la app de controladores. |
| Red | `curl`, `ssh`, `rsync` | Descargas y administración del servidor. |

El payload de arranque sale del rootfs (`grub-pc-bin`, `grub-efi-amd64-bin`,
`grub-efi-amd64-signed`, `shim-signed`), no del host.

## Qué no hace falta en el host

- `grub-mkrescue` ni los paquetes de GRUB del host.
- `sbuild`, `debhelper`, `devscripts` ni el compilador: viven en la imagen base
  de build.
- `xdotool`: sólo se usa dentro de la VM live para automatizar Calamares.
- `docker`: sólo en el servidor que ejecuta Aptly.

## Comprobación

```sh
sh tools/check-host.sh
make check
```

`check-host.sh` avisa de comandos ausentes, `/dev/kvm` y OVMF. No instala,
no configura servicios y no modifica la red del host.

## Workspace

```sh
export SUPRALINUX_WORKSPACE=/mnt/RAID0/Proyectos/SupraLINUX-workspace
```

El workspace guarda artifacts, evidencia, imágenes KVM y rootfs. Queda fuera de
Git. Ver [desarrollo](development.md).
