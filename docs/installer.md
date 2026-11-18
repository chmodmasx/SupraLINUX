# Instalador

## Calamares

La ISO incluye Calamares 3.3.14 de Ubuntu. La configuración de SupraLINUX vive
en `supralinux-calamares-config` y se instala en `/etc/calamares`; Calamares no
se parchea.

El paquete instala:

- `settings.conf` con la secuencia de módulos.
- `modules/*.conf` para particionado, usuarios, locale, teclado, mount,
  unpackfs, bootloader, displaymanager y los `shellprocess` propios.
- `branding/supralinux/` con logo, icono, portada, diapositivas, estilos y
  catálogos en inglés y francés.
- `kubuntu-calamares.desktop` como lanzador del live. El nombre se conserva
  por compatibilidad con casper; el texto visible es «Install SupraLINUX».
- El catálogo es_AR de Calamares compilado en `/usr/share/locale`.

No se instala `calamares-settings-kubuntu` ni `calamares-settings-ubuntu-common`.
El paquete declara `Conflicts`/`Replaces` con ambos.

## Secuencia

La instalación es offline-first:

1. Bienvenida, locale, teclado, particionado, usuario y resumen.
2. Particionado, montaje y `unpackfs` del squashfs.
3. Limpieza del sistema destino: retira Calamares, casper, la configuración del
   instalador y `cifs-utils`.
4. Metadata local de AppStream y actualización acotada de APT si hay red.
5. RAID, machine-id, fstab, locale, teclado y usuarios.
6. Display manager, red, reloj, initramfs, GRUB y bootloader.
7. Limpieza final, KWallet y apagado del instalador.

`packages` no ejecuta `apt-get update`; el sistema se instala sin red. Los
paquetes de idioma ya están en el squashfs y los `try_install` son best-effort
para otros locales.

## Particionado

El default es Btrfs:

- `supralinux_root` ocupa el 100 %.
- Subvolúmenes `@`, `@home`, `@snapshots` y `@swap`.
- Montaje `defaults,noatime,compress=zstd:3`.
- EXT4 disponible como alternativa.

Con LUKS2 se agrega `supralinux_boot` de 4 GiB ext4 sin cifrar. El GRUB firmado
de Ubuntu no incluye `argon2`; el initramfs desbloquea la raíz LUKS2.

Swap:

- `none`: sin swap.
- `file`: swapfile de 512 MiB en `@swap` (NOCOW, sin compresión).
- `small`: partición de hasta 4 GiB.
- `suspend`: partición >= RAM y `resume=UUID=...` en el kernel.

No se promete reanudación desde hibernación; sólo se probó la creación y el
parámetro `resume`.

## RAID y dual-boot

`mdadm`, `lvm2` y `ntfs-3g` están en el live. Los arrays se ocultan del
instalador para que no se ofrezcan como disco de borrado. El target recibe
`/etc/mdadm/mdadm.conf` y `mdmonitor`; el SO no se instala sobre RAID en el
flujo automático.

`os-prober` detecta Windows y otras raíces Linux. El instalador conserva las
entradas ajenas de la ESP y no pisa su arranque. Secure Boot usa la cadena de
Ubuntu; ver [secure-boot.md](secure-boot.md).

## Usuarios

Calamares crea el usuario con los grupos:

`adm`, `audio`, `bluetooth`, `cdrom`, `dip`, `gamemode`, `i2c`, `lpadmin`,
`netdev`, `plugdev`, `render`, `sambashare`, `scanner`, `sudo`, `video`.

El rootfs ejecuta `systemd-sysusers` antes del sellado para materializar grupos
declarados sólo en `/usr/lib/sysusers.d`. El autologin está desmarcado por
defecto.

## Locale y teclado

- El locale elegido se genera en el target.
- `/etc/default/locale` y `/etc/locale.conf` se normalizan a UTF-8.
- La consola usa `/etc/default/keyboard`.
- Plasma Wayland recibe `~/.config/kxkbrc` y `/etc/skel/.config/kxkbrc`.
- Las carpetas XDG se crean con el locale elegido.

## Identidad

`supralinux-base-files` instala `os-release`, `lsb-release`, `issue`,
`issue.net`, `legal` y el MOTD con `dpkg-divert`. La instalación no escribe
estos archivos a mano.

## Recuperación

La instalación Btrfs crea una instantánea base y un hook APT que toma una
instantánea PRE antes de cada operación de dpkg. `@home` es un subvolumen
separado y no se revierte.

El sistema instalado no conserva una entrada de recuperación propia. Se arranca
el live, se elige **SupraLINUX Aurora Recovery** y se ejecuta:

```sh
sudo supralinux-recover
```

El script lista las instantáneas, crea un `@` nuevo desde la elegida y conserva
la raíz anterior como `@pre-rollback-<fecha>`. Se retienen las tres raíces
previas más recientes. Ver [compatibility.md](compatibility.md).

## Límites

- No se ofrece instalación del SO sobre RAID en el flujo automático.
- No se probó la reanudación desde hibernación.
- El hardware físico se prueba best-effort; QEMU es la validación primaria.
- La matriz de instalación se ejecuta sobre discos desechables.
- No hay SLA ni soporte comercial.

## Estado en el repo nuevo

La configuración está empaquetada y validada con `dpkg-source`, `bash -n` y la
compilación del catálogo es_AR. El build binario y la matriz de instalación se
ejecutan cuando el repositorio nuevo y la ISO estén disponibles; hasta entonces
no se declara un PASS de instalación.
