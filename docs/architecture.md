# Arquitectura

## Layout del repositorio

```text
packages/
  kde/            KDE Frameworks 6.24
  plasma/         Plasma 6.6.7
  gear/           KDE Gear 25.12.3
  gear-extras/    Extras de completitud KDE
  desktop/        Integración SupraLINUX: base, branding, defaults, tema, hardware
  apps/           Apps propias
  system/         casper y hardware específico
  fonts/          Fuentes empaquetadas
branding/         Assets de marca, GRUB, Plymouth y wallpapers
installer/        Fuentes APT, claves y recuperación
tools/            Importación, build limpio, smoke tests y live
tests/            Pruebas y fixtures
docs/             Documentación
manifests/        Registros de build y release
```

## Componentes

| Componente | Responsabilidad |
|---|---|
| `supralinux-base-files` | Identidad del sistema, `os-release`, `lsb-release`, `issue`, `legal` |
| `supralinux-defaults` | Defaults del escritorio, servicios, locale y ajustes |
| `supralinux-theme` | Tema Aurora, Breeze derivado, SDDM y sonidos |
| `supralinux-branding` | Logos, wallpapers, GRUB, Plymouth y branding |
| `supralinux-hardware-support` | Meta de firmware y soporte de hardware |
| `supralinux-drivers` | App de controladores sobre UbuntuDrivers |
| `supralinux-calamares-config` | Configuración de Calamares en `/etc/calamares` |
| `casper` | Arranque live y soporte `noswap` |
| `gear`/`gear-extras` | Aplicaciones y utilidades KDE |

## Pipeline de build

1. **Fuente**: tarball upstream o packaging Ubuntu 26.04 revisado, con SHA-256.
2. **Importación**: se conserva el packaging Debian, se retiran metadatos internos y se documentan los parches.
3. **Build limpio**: `sbuild`/`unshare` sobre un rootfs retenido, sin SDKs preinstalados.
4. **Registro**: manifiesto con fuentes, dependencias, checksums y resultado.
5. **Repositorio**: paquetes y fuentes se publican en Aptly, firmados.
6. **Rootfs live**: `mmdebstrap` bajo `unshare`, con el perfil de escritorio.
7. **Squashfs**: `mksquashfs` determinista.
8. **ISO**: `xorriso` con BIOS/UEFI, shim y GRUB firmados por Ubuntu.
9. **Pruebas**: BIOS, UEFI, Secure Boot, instalación, primer arranque y recuperación.
10. **Release**: snapshot `stable`, tag, checksums y firma.

## Identidad y compatibilidad

- `ID=supralinux`, `ID_LIKE="ubuntu debian"`.
- `VERSION_ID=26.04`, `VERSION_CODENAME=resolute`, `UBUNTU_CODENAME=resolute`.
- `VERSION=1.0.0 (Aurora)`, `PRETTY_NAME="SupraLINUX Aurora 1.0.0"`.
- `SUPRALINUX_VERSION` y `SUPRALINUX_CODENAME` llevan la versión del producto.
- `supralinux-base-files` usa `dpkg-divert` para poseer los archivos de identidad sin reemplazar `base-files`.
- Las herramientas que necesitan la base leen `VERSION_ID`/`UBUNTU_CODENAME`; las que muestran el producto leen `PRETTY_NAME`/`VERSION`.

## Instalador

- La configuración vive en un paquete propio, no se copia a mano al rootfs.
- Calamares no se parchea; se configura.
- El paquete depende de `calamares` y no instala `calamares-settings-kubuntu`.
- El particionado, Btrfs, LUKS, RAID, locale, teclado, usuario y GRUB se prueban en BIOS y UEFI.

## Repositorio APT

- Aptly con `testing` y `stable`.
- Componente `main`, arquitecturas `amd64` y `source`.
- Publicación firmada con clave Ed25519.
- `testing` para QA; `stable` apunta a la release.
- Snapshots inmutables y retención del anterior.
- Los paquetes modificados publican su fuente en `deb-src`.

## Workspace

Las rutas se pasan por variables de entorno. Valores de ejemplo del entorno
actual:

```sh
SUPRALINUX_REPO=/mnt/RAID0/Proyectos/SupraLINUX
SUPRALINUX_WORKSPACE=/mnt/RAID0/Proyectos/SupraLINUX-workspace
SUPRALINUX_SECRETS=/mnt/RAID0/Proyectos/SupraLINUX-secrets
```

- `SUPRALINUX_WORKSPACE` guarda artifacts, evidencia y KVM fuera de Git.
- `SUPRALINUX_SECRETS` guarda claves y credenciales, fuera de Git.
- Los scripts no fijan rutas del host.
- Las bases/checkpoints KVM son inmutables para sus consumidores.

## Seguridad de la cadena

- La ISO usa shim y GRUB firmados por Canonical/Microsoft y el kernel de Ubuntu.
- La cadena es Microsoft → Canonical → GRUB/kernel.
- SupraLINUX no afirma una cadena Secure Boot propia en 1.0.0.
- Un kernel o módulo propio requiere firma con MOK o clave propia.
- Los binarios firmados no se modifican.

## Principios

- Un solo stack: no quedan paquetes de una campaña anterior en el runtime.
- Cada release se reconstruye desde inputs limpios.
- La evidencia se conserva fuera del repo.
- No se modifica ninguna distribución instalada.
- Los cambios de comportamiento se documentan y se prueban.
