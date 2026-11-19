# Pruebas

## Principios

- Las pruebas se ejecutan en ISO, rootfs o VM desechable. Nunca se modifica una
  distribución instalada para validar un cambio.
- Un resultado se liga al commit limpio y a los hashes de sus inputs.
- No se inventa un PASS. Un test que no se ejecutó no es PASS.
- Un fallo de infraestructura no se atribuye al paquete ni a la release.

Estados permitidos:

| Estado | Significado |
|---|---|
| `PASS` | El resultado esperado se observó y quedó evidencia. |
| `FAIL` | El producto no cumplió el resultado esperado. |
| `INFRA_INVALID` | Falló la preparación, el transporte o el cleanup; no certifica ni condena el producto. |
| `BLOCKED` | Falta un prerequisito y no se obtuvo resultado. No es PASS. |

No se admiten PASS parciales. Si una matriz no se completó, se publica como
`BLOCKED` y la release no se aprueba para ese alcance.

## Niveles

| Nivel | Alcance | Ejecución |
|---|---|---|
| L0 | Unitarias, estáticas y de contrato | Host |
| L1 | Build limpio de un paquete | VM o `sbuild`/`unshare` |
| L2 | Smoke offline de instalación | VM sin NIC |
| L3 | Arranque y escritorio live | QEMU BIOS/UEFI/Secure Boot |
| L4 | Instalador | QEMU con discos desechables |
| L5 | Primer arranque y post-instalación | VM instalada desechable |
| L6 | Recuperación y rollback | Live + disco Btrfs desechable |
| L7 | Integridad de release | Host y repositorio |

## L0: unitarias y estáticas

```sh
python3 -m unittest discover -s tests -v
```

Cubren, como mínimo:

- Restauración por SHA-256 y rechazo de conflictos.
- Preservación de archivos y permisos.
- Opciones QEMU sin NIC y ausencia de bridges/TAP.
- Configuración APT con `Signed-By`.
- Transporte parcial o truncado.
- Cleanup de overlays y verificación del padre.
- Parseo de manifests y contratos de herramientas.
- Enlaces de documentación y ausencia de artifacts o secretos en Git.

También se revisan `shellcheck` en scripts, sintaxis de JSON/YAML, `git diff
--check` y que no haya `.deb`, ISOs, discos, logs ni claves versionadas.

Un test unitario no sustituye un build ni una prueba de VM.

## L1: build limpio

Gates:

- Fuente y `debian/` verificados por hash.
- Clausura de `Build-Depends` retenida y resuelta desde el repositorio local.
- Sin red y sin SDKs preinstalados que oculten dependencias.
- Build reproducible dentro del alcance documentado.
- `dh_missing --fail-missing` sin archivos sin empaquetar.
- `lintian` sin errores en paquetes propios.
- `debian/copyright` completo.
- `.changes`, `.buildinfo`, binarios, logs y hashes retenidos.

Resultado: `PASS` sólo si el binario esperado y su payload coinciden con el
manifiesto. Un fallo de sbuild se registra como `FAIL` con causa `BUILD_FAIL`;
un fallo de preparación, transporte o cleanup es `INFRA_INVALID`.

## L2: smoke offline

Circuito:

1. Restaurar el artifact por SHA-256.
2. Crear un repositorio APT local firmado con clave efímera de prueba.
3. Arrancar una VM sin NIC.
4. Instalar la versión exacta desde el repositorio firmado, sin desactivar
   firmas.
5. Verificar hashes de archivos instalados y ejecutar el test funcional.
6. Comprobar el control negativo: el test falla si falta su dato runtime y
   vuelve a pasar al restaurarlo.
7. Comprobar que APT rechaza índices manipulados.
8. Restaurar el artifact en un destino vacío y verificar el digest.
9. Exportar evidencia, apagar la VM, eliminar el overlay y comprobar que el
   padre no cambió.

No certifica un build nuevo, KDE completo, una ISO ni la publicación estable.
El resultado cubre restauración, transporte offline, APT/instalación, test
funcional y cleanup.

## L3: live

Casos mínimos:

| ID | Caso | Criterio |
|---|---|---|
| L3-BIOS | Arranque BIOS/SeaBIOS | Llega a SDDM y abre sesión Plasma Wayland. |
| L3-UEFI | Arranque UEFI con OVMF | Igual que BIOS; `efibootmgr` coherente. |
| L3-SB | UEFI Secure Boot | `SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c` vale `1`. |
| L3-MD5 | Integridad del medio | `md5sum -c /cdrom/md5sum.txt` sin errores. |
| L3-SAFE | Safe graphics | Arranca con `nomodeset` y permite diagnóstico. |
| L3-REC | Entrada Recovery | Arranca en multi-user y permite `supralinux-recover`. |
| L3-DEBUG | Entrada debug | Arranca con logs de systemd y consola serie. |
| L3-SESSION | Sesión | `plasmashell`, `kwin_wayland`, XWayland y `systemsettings`. |
| L3-APPS | Apps base | Dolphin, Konsole, Kate, Ark, Gwenview, Okular, Firefox. |
| L3-NET | Red | NetworkManager gestiona Ethernet y Wi-Fi en QEMU. |
| L3-AUDIO | Audio | PipeWire/WirePlumber activos; dispositivo de prueba. |
| L3-KEYRING | Secret Service | KWallet responde en la sesión, sin diálogo bloqueante. |
| L3-SHUTDOWN | Apagado | Apagado limpio desde el menú, sin cuelgues. |

La suite live completa se registra con su total ejecutado. No se publica un
número de tests si no se corrieron.

## L4: instalador

Matriz mínima:

| ID | Caso | Criterio |
|---|---|---|
| L4-BTRFS | Btrfs estándar | Instala, arranca y crea `@`, `@home`, `@snapshots`. |
| L4-LUKS | Btrfs + LUKS2 | `/boot` ext4 separado; initramfs desbloquea la raíz. |
| L4-EXT4 | EXT4 | Instala y arranca; sin Snapper. |
| L4-DUAL | Dual-boot | Detecta Windows/Linux existente sin pisar su arranque. |
| L4-UEFI | UEFI | Entrada `SupraLINUX` apunta al shim firmado. |
| L4-BIOS | BIOS | GRUB instala y arranca. |
| L4-SB | Secure Boot | El sistema instalado arranca con Secure Boot activo. |
| L4-RAID | RAID de datos | Ensambla arrays existentes; no se ofrece como disco de SO. |
| L4-SWAP | Swap | `none`, `file`, `small` y `suspend` según lo elegido. |
| L4-LOCALE | Locale y teclado | Consola y Plasma respetan lo elegido. |
| L4-USER | Usuario y grupos | Grupos declarados, incluido `gamemode`; sudo funciona. |
| L4-OFFLINE | Instalación sin red | No depende de APT online; metadata local disponible. |

Cada caso usa discos desechables y un overlay propio. Un fallo de QEMU, OVMF o
del host es `INFRA_INVALID`, no `FAIL` del instalador.

## L5: primer arranque

- SDDM y sesión Wayland.
- KWallet/Secret Service sin diálogo detrás de la aplicación.
- Firefox abre, tiene español disponible y no vuelve a pedir ser el navegador
  por defecto en cada inicio.
- Discover muestra aplicaciones y Flatpak/Flathub configurado.
- `apt update` y una instalación/actualización de paquete del repositorio
  `testing` funcionan con firmas.
- Snapper lista la configuración `root` por D-Bus y por `--no-dbus`.
- El gestor de controladores detecta y aplica un driver cuando corresponde.
- Apagado limpio, sin servicios colgados.
- No hay errores críticos en `journalctl -p err` sin explicación.

## L6: recuperación

| ID | Caso | Criterio |
|---|---|---|
| L6-SNAP | Instantáneas APT | El hook crea una instantánea PRE antes de dpkg. |
| L6-ROLLBACK | Rollback | `supralinux-recover` crea un `@` nuevo desde la instantánea. |
| L6-HOME | `/home` | `@home` no se modifica durante el rollback. |
| L6-RETENTION | Retención | Se conservan las tres raíces `@pre-rollback-*` más recientes. |
| L6-BOOT | Arranque posterior | El sistema vuelve a arrancar y es utilizable. |

El sistema instalado no conserva una entrada de recuperación propia: el script
necesita que `@` no esté montado y se ejecuta desde el live.

## L7: release

- ISO verificada por SHA-256 y firma GPG.
- `InRelease` del repositorio verificado con la clave pública publicada.
- Snapshot `stable` contiene exactamente los paquetes de la release.
- Fuentes de paquetes modificados disponibles en `deb-src`.
- Documentación, changelog y manifiestos coherentes con la versión.
- Sin secretos, claves privadas, discos ni capturas en el árbol publicado.
- Enlaces del sitio web y del repositorio responden.

## Evidencia

Cada ejecución deja un directorio propio:

```text
evidence/<tipo>/<run>/
  result.json
  command.txt
  console.log
  qemu-command.json
  screenshots/
  logs/
  hashes.txt
  cleanup.json
```

`result.json` incluye commit, fecha, inputs con SHA-256, versión de la ISO o
paquete, estado, duración, errores y cleanup. Las capturas y logs no se suben a
Git. La evidencia se conserva fuera del repositorio y se referencia desde el
manifiesto de release.

## Regresión

- Un fix de packaging exige build limpio y smoke del paquete afectado.
- Un cambio de escritorio exige ISO y sesión live.
- Un cambio de instalador exige la matriz L4 completa.
- Un cambio de base o de kernel exige L3, L4, L5 y L6.
- Un cambio de Secure Boot exige L3-SB, L4-SB y L4-UEFI.
- Un fallo corregido se reproduce antes y después; el test queda como
  regresión.

## Resultados actuales

- Suite unitaria: `PASS`.
- 9 paquetes nativos del producto y el paquete sintético de prueba: `PASS` en
  build limpio, con artifact y evidencia retenidos. El resumen está en
  `manifests/native-builds-1.0.0.json`.
- Muestras de Frameworks, Plasma y Gear: `extra-cmake-modules`,
  `libkf6coreaddons6`, `libkwin6` y `dolphin` con build limpio `PASS`.
  El resumen está en `manifests/stack-builds-1.0.0.json`.
- Smoke offline: `supralinux-build-test` y `supralinux-base-files` instalan
  desde un repositorio local firmado, pasan el control negativo y rechazan
  índices manipulados. El resumen está en
  `manifests/package-smoke-results-1.0.0.json`.
- El intento inicial de `supralinux-base-files` falló por preguntas de
  conffile; se corrigió el paquete y se repitió el smoke.
- ISO de humo `8994da94…`: arranque BIOS y UEFI Secure Boot hasta Plasma
  `PASS`. Se construyó desde el rootfs live anterior con 9 paquetes nuevos;
  no es un build limpio, no se probó Calamares y no es una release. UEFI
  Secure Boot se verificó con `mokutil` y el efivar en `1`.
  El resumen está en `manifests/smoke-iso-1.0.0.json`.
- Los 176 paquetes fuente: build limpio `PASS` (176/176), con artifact,
  `.changes`, `.buildinfo`, evidencia y cleanup comprobado. El resumen está en
  `manifests/full-build-results-1.0.0.json`. Los cierres de `Build-Depends` se
  reutilizaron como inputs verificados por SHA-256; cada paquete se reconstruyó
  con el packaging actual.
- ISO limpia `be806212…`: rootfs nuevo desde Ubuntu 26.04 + snapshot
  `supralinux-testing-1.0.0-20261119b`; BIOS y UEFI Secure Boot hasta Plasma
  `PASS`. UEFI Secure Boot verificado con `mokutil` y efivar `1`.
- Instalación Btrfs offline con Calamares 1.0.1: `PASS`. Primer arranque en
  BIOS, SDDM, login de usuario y Plasma Wayland: `PASS`. El target queda en
  Btrfs con los subvolúmenes `@`, `@home` y `@snapshots`; Calamares, casper y
  `supralinux-calamares-config` no quedan instalados.
- El intento con `supralinux-calamares-config` 1.0.0 falló en el módulo
  `packages` porque intentaba quitar paquetes ausentes con listas APT vacías.
  Se corrigió en 1.0.1, se recompiló y se repitió la instalación.
- LUKS2, EXT4, dual-boot y recuperación Btrfs siguen pendientes.
- El resumen de la ISO limpia está en `manifests/iso-1.0.0.json`.

Un resultado de esta sección no se extrapola a la release completa.

## Retención y limpieza

- Se conserva una ISO por fase validada con su `BUILD-ID`, `SHA256SUMS`,
  firma y `result.json`.
- Se conservan los rootfs de la fase vigente y de la release.
- Se pueden podar rootfs y runs antiguos ya resumidos, nunca la evidencia de la
  release publicada.
- `cache/` y los overlays son reconstruibles; no se conservan como evidencia.
- Al cerrar una ejecución se comprueba que no quedan VMs, discos ni montajes
  propios.
