# Compatibilidad con la base

## Contrato de identidad

SupraLINUX se presenta como una distribución basada en Ubuntu 26.04 LTS, pero
conserva los campos que APT y las herramientas de la base necesitan:

```text
NAME="SupraLINUX"
ID=supralinux
ID_LIKE="ubuntu debian"
VERSION="1.0.0 (Aurora)"
VERSION_ID="26.04"
VERSION_CODENAME=resolute
UBUNTU_CODENAME=resolute
PRETTY_NAME="SupraLINUX Aurora 1.0.0"
SUPRALINUX_VERSION="1.0.0"
SUPRALINUX_CODENAME="aurora"
SUPRALINUX_BASE="Ubuntu 26.04 LTS"
```

| Consumidor | Campo que usa | Resultado |
|---|---|---|
| APT y `sources.list` | `VERSION_ID`, `VERSION_CODENAME`; `add-apt-repository` usa `ID` + `VERSION_CODENAME` + `supralinux.info` | Resuelve `resolute` como Ubuntu 26.04 y agrega PPAs con la suite correcta. |
| `lsb_release` | `DISTRIB_ID`, `DISTRIB_RELEASE`, `DISTRIB_CODENAME` | Informa SupraLINUX Aurora 1.0.0 y la base. |
| Herramientas de base | `ID_LIKE`, `VERSION_ID` | Conservan el comportamiento de Ubuntu/Debian. |
| UI y `fastfetch` | `PRETTY_NAME`, `VERSION` | Muestran el producto. |
| Scripts propios | `SUPRALINUX_*` | Diferencian producto y base. |

No se usa `ID=ubuntu` para ocultar la identidad. Un programa que exija
exactamente `ID=ubuntu` puede requerir configuración o un parche; se documenta
como limitación, no se falsifica el archivo.

## APT

- Las fuentes de Ubuntu apuntan a `resolute` y a los componentes
  `main, universe, restricted, multiverse`.
- El repositorio SupraLINUX publica `main` para `amd64` y `source`.
- `testing` y `stable` usan prioridad alta y `NotAutomatic: yes` en el canal de
  QA, para que una instalación explícita funcione sin que un `apt upgrade`
  ordinario salte a paquetes no probados.
- Las fuentes propias declaran `Architectures: amd64`; no se publican índices
  `i386`.
- Los paquetes modificados publican `deb-src`.
- Las claves se instalan en `/etc/apt/keyrings/` y se referencian con
  `Signed-By`. No se usa `apt-key`.

La base conserva la autoridad sobre kernel, firmware, drivers, Qt, bibliotecas
de plataforma y servicios. SupraLINUX no reemplaza esos paquetes salvo el
packaging propio documentado.

## Kubuntu y packaging

- No se instala `calamares-settings-kubuntu`. La configuración vive en
  `supralinux-calamares-config`.
- No se usan los metapaquetes de Kubuntu para definir el escritorio.
- `casper` se empaqueta con el parche necesario para `noswap` y el arranque
  live; se documenta en su `debian/patches`.
- Los defaults, el tema, el branding y la identidad son paquetes propios.
- Los paquetes de KDE se construyen desde upstream contra el Qt de Ubuntu; no
  se mezclan con los de Kubuntu.

## Snap

La release 1.0.0 no incluye `snapd`.

Consecuencias:

- `snap` no está disponible por defecto.
- El paquete transicional de Firefox de Ubuntu no se usa; Firefox viene del
  repositorio de Mozilla.
- Las aplicaciones que sólo se distribuyen como snap no forman parte del
  producto. Se puede usar Flatpak/Flathub o instalar snap por decisión del
  usuario, fuera de la configuración soportada.
- `ubuntu-drivers` y el gestor de controladores usan APT, no snap.

## Firefox y Mozilla

- Fuente oficial: `https://packages.mozilla.org/apt`, componente `mozilla`.
- Clave de Mozilla en `/etc/apt/keyrings/`.
- Paquetes: `firefox`, `firefox-l10n-es-ar`, `firefox-l10n-es-es`,
  `firefox-l10n-es-mx`. El inglés está incorporado.
- Se bloquea el paquete de Firefox de Ubuntu para que no reemplace al de
  Mozilla ni instale el transicional de snap.
- No hay mirror propio ni cron de sincronización.
- El lanzador se genera con la ruta real de `firefox-bin`; un hook de APT lo
  regenera después de cada actualización.
- La política de «no preguntar para ser el navegador por defecto» evita que el
  asistente inicial se repita.

Thunderbird no forma parte de 1.0.0. Si se necesita, se ofrece por Flathub; no
se empaqueta en esta release.

## Kernel, drivers y Secure Boot

- Kernel `linux-image-generic` de Ubuntu 26.04, firmado por Canonical.
- Drivers NVIDIA mediante el meta de Ubuntu y `ubuntu-drivers`, con módulos
  firmados por Canonical.
- No se compila un kernel propio.
- Un módulo DKMS de terceros requiere MOK con Secure Boot activo.
- La cadena Secure Boot es la de Ubuntu; ver [secure-boot.md](secure-boot.md).
- En BIOS no hay Secure Boot; la integridad se limita al medio y al repositorio.

## Escritorio

- Sesión de usuario Wayland; XWayland para apps X11.
- SDDM usa Xorg sólo para el greeter.
- Plasma, KWin, System Settings, portales y KCMs se prueban en Wayland.
- PipeWire/WirePlumber para audio; NetworkManager para red.
- KWallet/Secret Service por usuario.
- No se instala `evolution-data-server`, para no desplazar la cartera con
  `gnome-keyring`. La sincronización PBAP de contactos por Bluetooth queda como
  limitación.
- `fastfetch` no lleva parche de `os-release`; su salida es cosmética y puede
  mostrar una variante genérica.

## Instalación y disco

- Btrfs por defecto con `@`, `@home`, `@snapshots` y `@swap` para swapfile.
- LUKS2 con `/boot` ext4 separado; el GRUB firmado de Ubuntu no incluye
  `argon2`, por lo que el desbloqueo lo hace el initramfs.
- EXT4 disponible como alternativa, sin Snapper ni rollback.
- RAID de datos con `mdadm`; no se ofrece instalar el SO sobre RAID en el flujo
  automático.
- Dual-boot con otra instalación Linux mediante `os-prober`, conservando las
  entradas ajenas de la ESP. Windows no se declara validado en 1.0.0.
- Swap: `none`, `file` (512 MiB en `@swap`), `small` (hasta 4 GiB) o `suspend`
  (partición >= RAM). La reanudación desde hibernación no se probó.
- zram sólo en equipos de hasta 8 GB; zswap desactivado.

## Recuperación

- Snapper en la raíz, con instantáneas PRE antes de dpkg.
- `@home` es un subvolumen separado y no se revierte.
- `supralinux-recover` se ejecuta desde el live y conserva la raíz anterior como
  `@pre-rollback-<fecha>`.
- La GUI `supralinux-recovery-gui` envuelve al backend y se elimina del target.
- Se retienen las tres raíces `@pre-rollback-*` más recientes.
- El sistema instalado no conserva una entrada de recuperación propia ni la GUI.
- EXT4 no tiene rollback.
- La recuperación guiada cubre Btrfs sin cifrar; LUKS2 no tiene rollback
  automático en 1.0.0.

## Actualizaciones

- Las actualizaciones de seguridad de la base siguen el ciclo de Ubuntu 26.04
  mientras el proyecto se mantenga.
- KDE se reconstruye cuando hay una actualización compatible con el Qt de la
  base.
- No se promete actualización entre bases mayores; un cambio de base se trata
  como reinstalación validada.
- No se promete `apt full-upgrade` entre campañas de KDE sin pasar por la
  matriz de pruebas.
- Un paquete publicado no se reescribe con la misma versión; se publica una
  versión nueva.

## i386 y multiarch

El repositorio SupraLINUX no publica `i386`. Si el usuario habilita multiarch
para Steam u otro software, APT puede pedir índices `binary-i386` de Ubuntu; las
fuentes propias declaran `Architectures: amd64` para no pedirlos. Los paquetes
de terceros i386 quedan fuera del alcance de la release.

## Limitaciones conocidas

- No hay cadena Secure Boot propia.
- No hay snapd.
- No se probó la reanudación real desde hibernación.
- No se ofrece instalación del SO sobre RAID en el flujo automático.
- La sincronización PBAP de contactos por Bluetooth no está integrada.
- `fastfetch` puede mostrar una variante genérica.
- El hardware físico se prueba best-effort; QEMU es la validación primaria.
- No hay SLA ni promesa de fin de soporte.
- No se garantiza compatibilidad con software que dependa de un snap o de
  `ID=ubuntu` exacto.

## Checklist de compatibilidad

- [ ] `os-release` y `lsb-release` coherentes.
- [ ] `apt update` contra Ubuntu y SupraLINUX sin errores de firma.
- [ ] `apt install` explícito desde `testing`/`stable` con prioridad correcta.
- [ ] Firefox de Mozilla gana al paquete de Ubuntu.
- [ ] `ubuntu-drivers` detecta y aplica un driver.
- [ ] Secure Boot activo con kernel y módulos firmados.
- [ ] SDDM, Plasma Wayland y XWayland.
- [ ] KWallet/Secret Service desde el primer inicio.
- [ ] Btrfs, Snapper y rollback; EXT4 sin rollback.
- [ ] Locale y teclado en consola y Plasma.
- [ ] Sin `snapd` ni paquetes transicionales de snap.
