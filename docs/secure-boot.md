# Secure Boot

## Alcance

SupraLINUX 1.0.0 arranca en BIOS y en UEFI. En UEFI con Secure Boot activo usa
la cadena firmada de Ubuntu; no mantiene una cadena de claves propia.

La ISO y el sistema instalado deben arrancar sin desactivar Secure Boot en
hardware que confíe en el certificado de Canonical. No se promete lo mismo en
firmware que sólo confía en claves del fabricante o que tiene una política
restringida.

## Cadena de confianza

```text
Firmware UEFI
└── Microsoft UEFI CA (db)
    └── shim de Canonical
        └── GRUB firmado por Canonical
            └── kernel de Ubuntu firmado por Canonical
                └── módulos del kernel firmados por Canonical
```

| Componente | Quién lo firma | Se modifica |
|---|---|---|
| `shimx64.efi` | Canonical / Microsoft UEFI CA | No |
| `grubx64.efi` | Canonical | No |
| `mmx64.efi` | Canonical | No |
| `vmlinuz` | Canonical | No |
| Módulos de Ubuntu | Canonical | No |
| Módulos NVIDIA de Ubuntu | Canonical | No |

Los binarios firmados se copian tal cual desde el rootfs. No se re-firman, no
se parchean y no se reemplazan por una compilación propia.

## ISO live

La ISO es híbrida: BIOS y UEFI desde el mismo medio.

- BIOS: `eltorito.img`, `boot_hybrid.img` y módulos `i386-pc` salen de
  `grub-pc-bin` dentro del rootfs.
- UEFI: se usa `shimx64.efi.signed.latest` como `EFI/BOOT/BOOTX64.EFI` y
  `gcdx64.efi.signed` como `grubx64.efi`, con `mmx64.efi` para MOK.
- Se copia el mismo conjunto bajo `EFI/ubuntu/`, porque el GRUB firmado
  resuelve su prefijo en `/EFI/ubuntu` sobre el dispositivo de arranque.
- `grub.cfg` se escribe tanto en la ESP como en el árbol ISO9660.
- `xorriso` compone la ISO con `--grub2-mbr`, `--grub2-boot-info`,
  `-append_partition`, `-appended_part_as_gpt`, `--mbr-force-bootable`,
  `-eltorito-alt-boot` y `-partition_offset 16`.
- `md5sum.txt` excluye `boot/grub/i386-pc/eltorito.img`, que xorriso parchea al
  insertar la información de arranque.

No se usa `grub-mkrescue` ni se lee `/boot/grub` del host. El payload sale del
rootfs de Ubuntu 26.04.

Verificación de la ISO:

```sh
sbverify --list /ruta/al/rootfs/usr/lib/shim/shimx64.efi.signed.latest
sbverify --list /ruta/al/rootfs/usr/lib/grub/x86_64-efi-signed/gcdx64.efi.signed
```

Los nombres exactos pueden variar según el packaging de Ubuntu; se toma la ruta
que declare el paquete y se registra en el manifiesto de la ISO.

## Sistema instalado

Calamares instala GRUB con `efiBootloaderId=supralinux`.

- La entrada UEFI `SupraLINUX` apunta a `\EFI\supralinux\shimx64.efi`.
- En `EFI/supralinux/` quedan `shimx64.efi`, `grubx64.efi`, `mmx64.efi` y
  `grub.cfg`.
- `EFI/BOOT/BOOTX64.EFI` conserva el fallback del shim firmado. Si
  `grub-install` deja un GRUB propio como fallback, se reemplaza por el shim
  firmado y se completan `grubx64.efi`, `mmx64.efi` y `grub.cfg`.
- No se pisa el arranque de otro sistema. `os-prober` agrega Windows y otras
  raíces Linux, y las entradas ajenas de la ESP se conservan.
- La ESP se monta con `umask=0077`; el firmware puede leerla y el usuario no
  necesita acceso directo.

El sistema instalado no conserva una entrada de recuperación propia. La
recuperación se hace desde el USB live, que también usa la cadena firmada.

## Kernel y módulos

- Se usa el kernel `linux-image-generic` de Ubuntu 26.04, firmado por Canonical.
- Los módulos de Ubuntu y los módulos NVIDIA que instala `ubuntu-drivers` están
  firmados por Canonical.
- No se compila un kernel propio para 1.0.0.
- Un módulo DKMS de terceros no está firmado por Canonical. Para cargarlo con
  Secure Boot activo hay que enrolar su clave con MOK (`mokutil --import`) y
  reiniciar para completar la inscripción.
- Un módulo sin firma o sin MOK se rechaza; no se debe desactivar Secure Boot
  para evitarlo.

## Verificación

En el sistema live o instalado:

```sh
mokutil --sb-state
cat /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c
efibootmgr -v
dmesg | grep -i -E 'secure boot|lockdown'
```

- `mokutil --sb-state` debe informar `SecureBoot enabled`.
- El efivar `SecureBoot` debe valer `1`.
- `efibootmgr -v` debe mostrar `SupraLINUX` apuntando al shim.
- `dmesg` no debe mostrar rechazos de firma de módulos necesarios.

En la ISO:

```sh
md5sum -c /cdrom/md5sum.txt
```

La comprobación de firmas de la ISO y del repositorio se hace en el host con
`sbverify`, `gpgv` y los hashes del manifiesto.

## Pruebas

| Caso | Criterio |
|---|---|
| BIOS/SeaBIOS | Arranca y llega al escritorio. |
| UEFI sin Secure Boot | Arranca con OVMF y `efibootmgr` coherente. |
| UEFI Secure Boot | Arranca con OVMF `OVMF_CODE_4M.secboot.fd`; efivar `SecureBoot=1`. |
| Instalación Secure Boot | El sistema instalado arranca con la entrada `SupraLINUX`. |
| Módulo sin firma | Se rechaza; no se desactiva Secure Boot para forzarlo. |
| MOK | La inscripción de una clave de prueba funciona y el módulo carga. |
| Dual-boot | Las entradas ajenas siguen arrancando. |
| Recuperación | La entrada Recovery del live arranca con Secure Boot activo. |

OVMF:

```sh
-drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd
-drive if=pflash,format=raw,file="$RUN/OVMF_VARS_4M.ms.fd"
```

Un fallo de OVMF, de la variable de firmware o del host es `INFRA_INVALID`; un
rechazo de firma del producto es `FAIL`.

## Límites

- No hay cadena Secure Boot propia en 1.0.0.
- No hay servicio de firma de kernels o módulos propios.
- No se garantiza el arranque en firmware que no confíe en el certificado de
  Canonical o que aplique una política más restrictiva.
- Las revisiones SBAT del firmware pueden revocar shims o GRUB antiguos. Se
  usan los binarios firmados vigentes de Ubuntu y se recomienda actualizar el
  firmware y el shim antes de reportar un fallo.
- En BIOS no existe Secure Boot; la verificación se limita a integridad del
  medio y del repositorio.
- La inscripción MOK es una acción del usuario y depende de la interfaz del
  firmware.
- No se prueba hardware real de forma exhaustiva; QEMU es la validación
  primaria y el hardware físico es best-effort.

## Claves

- La clave APT es independiente de Secure Boot. No firma binarios EFI.
- La clave privada de APT vive en `SUPRALINUX_SECRETS` y nunca se versiona.
- No se genera ni distribuye una clave UEFI propia en 1.0.0.
- Una futura cadena propia exigiría custodia de claves, revisión de seguridad,
  enrolamiento en firmware y, si corresponde, revisión de Microsoft. No forma
  parte de esta release.
