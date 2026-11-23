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
| L3-REC | Entrada Recovery | Arranca el live gráfico, autolanza la GUI y permite restaurar. |
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
| L4-DUAL | Dual-boot Linux | Detecta otra instalación Linux existente sin pisar su arranque. Se prueba en el mismo disco y en dos discos. Windows no se declara validado en 1.0.0. |
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
| L6-GUI | GUI de recuperación | Lista las instantáneas con fecha y descripción desde el live. |
| L6-ROLLBACK | Rollback | `supralinux-recover` crea un `@` nuevo desde la instantánea. |
| L6-HOME | `/home` | `@home` no se modifica durante el rollback. |
| L6-RETENTION | Retención | Se conservan las tres raíces `@pre-rollback-*` más recientes. |
| L6-BOOT | Arranque posterior | El sistema vuelve a arrancar y es utilizable. |
| L6-POLKIT | Polkit | La GUI no corre como root; el helper autoriza al usuario live. |
| L6-DESKTOP | Escritorio live | El icono «Recuperar SupraLINUX» aparece junto a Calamares y la entrada Recovery autolanza la GUI. |

El sistema instalado no conserva una entrada de recuperación propia ni la GUI:
el backend necesita que `@` no esté montado y se ejecuta desde el live. La
recuperación guiada cubre Btrfs sin cifrar; con LUKS2 el rollback no está
soportado en 1.0.0 y debe documentarse como limitación.

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
- Los 177 paquetes fuente: build limpio `PASS` (177/177), con artifact,
  `.changes`, `.buildinfo`, evidencia y cleanup comprobado. El resumen está en
  `manifests/full-build-results-1.0.0.json`. Los cierres de `Build-Depends` se
  reutilizaron como inputs verificados por SHA-256; cada paquete se reconstruyó
  con el packaging actual.
- `supralinux-recovery-gui 1.0.0` y `supralinux-calamares-config 1.0.2`: build
  limpio `PASS` en VMs desechables; el `.deb` de la GUI incluye binario, QML,
  polkit, autostart, icono y helper, y el de Calamares incluye el payload de
  limpieza del target. Evidencia en `evidence/clean-build/`.
- ISO limpia `93f2fef4…`: rootfs nuevo desde Ubuntu 26.04 + snapshot
  `supralinux-testing-1.0.0-20261120c`; BIOS y UEFI Secure Boot hasta Plasma
  `PASS`. UEFI Secure Boot verificado con `mokutil` y efivar `1`.
- ISO candidata `fef5990f…`
  (`supralinux-aurora-1.0.0-amd64-20261120T061139Z-g25bf91c.iso`): rootfs
  nuevo desde Ubuntu 26.04 + snapshot `20261120d`; BIOS y UEFI Secure Boot
  `PASS`, visor de Ark en 800×600 por defecto y RAR multivolumen `PASS`.
- Snapshot `supralinux-testing-1.0.0-20261120f`: 604 binarios y 176 fuentes.
  Incluye `supralinux-base-files 1.0.2` (`BUG_REPORT_URL=/bugs`) y
  `supralinux-defaults 1.1.3` (rueda de Gwenview en Ampliar).
- Snapshot `supralinux-testing-1.0.0-20261121g`: 608 binarios y 180 fuentes.
  Agrega `supralinux-recovery-gui 1.0.0` y actualiza
  `supralinux-calamares-config` a 1.0.2; `InRelease` verificado con la clave
  Ed25519. El resumen está en `manifests/aptly-publication-1.0.0.json`.
- Snapshot `supralinux-testing-1.0.0-20261122a`: 608 binarios y 180 fuentes.
  Actualiza `supralinux-defaults` a 1.1.4 con el probe de os-prober para
  raíces Btrfs `@`; mantiene GUI 1.0.0 y Calamares 1.0.2. `InRelease`
  verificado con la clave Ed25519.
- Snapshot `supralinux-testing-1.0.0-20261122b`: 610 binarios y 182 fuentes.
  Publica `supralinux-theme 1.1.2` (GTK 3/4 oscuro) y `supralinux-defaults
  1.2.2` (Aurora oscuro por defecto, claro seleccionable); branding sigue en
  1.3.0. `InRelease` verificado con la clave Ed25519.
- Snapshot `supralinux-testing-1.0.0-20261122c`: 612 binarios y 184 fuentes.
  Publica `supralinux-theme 1.1.3` (selección `#51A2DA`, neutral `#F67400`,
  SDDM claro y hover por defecto) y `supralinux-branding 1.3.1` (wallpapers
  Light/Dark sueltos). `InRelease` verificado con la clave Ed25519.
- Snapshot `supralinux-testing-1.0.0-20261122d`: 613 binarios y 185 fuentes.
  Agrega `supralinux-branding 1.3.2` con el icono opcional
  `supralinux-white-blue` para el menú Inicio. `InRelease` verificado con la
  clave Ed25519.
- Snapshot `supralinux-testing-1.0.0-20261122e`: 614 binarios y 186 fuentes.
  Agrega `supralinux-defaults 1.2.3` con la página por defecto del Monitor del
  sistema y colores distintos para CPU, GPU, memoria e intercambio.
  `InRelease` verificado con la clave Ed25519.
- Snapshot `supralinux-testing-1.0.0-20261122f`: 616 binarios y 188 fuentes.
  Agrega `kio-admin 25.12.3-0supralinux2` con `ShowInHome` y
  `supralinux-defaults 1.2.4` con `/etc/xdg/kio-adminrc`; la acción “Abrir
  como administrador” queda visible en todas las carpetas locales.
  `InRelease` verificado con la clave Ed25519.
- Snapshot `supralinux-testing-1.0.0-20261122g`: 617 binarios y 189 fuentes.
  Agrega `supralinux-defaults 1.2.5` con el override local de AppArmor para
  `linux-boot-prober` y la invalidación de la caché del perfil.
  `InRelease` verificado con la clave Ed25519.
- Gwenview en VM desechable: sin configuración de usuario la rueda cambió
  33% → 94% → 33%; Preferencias mostró “Ampliar”; una preferencia explícita
  de “Desplazamiento” dejó el zoom en 33%. Evidencia en
  `evidence/live/gwenview-default-20261120/`.
- ISO candidata `1c79f343…`
  (`supralinux-aurora-1.0.0-amd64-20261120T134809Z-g6e17fa1.iso`): BIOS y
  UEFI Secure Boot `PASS`; `BUG_REPORT_URL=/bugs` responde 200 desde la VM;
  Gwenview abre en 33% y la rueda lo lleva a 94%; Preferencias muestra
  “Ampliar”. Evidencia en `evidence/live/bios-20261120f/` y
  `evidence/live/uefi-sb-20261120f/`.
- Simulación de actualización desde la ISO anterior: `apt-get update` ve
  `supralinux-base-files 1.0.2` y `supralinux-defaults 1.1.3` con prioridad
  1001; `apt-get -s install --only-upgrade` selecciona ambos. Evidencia en
  `evidence/live/apt-upgrade-sim-20261120f/checks.txt`.
- Instalación Btrfs offline con Calamares 1.0.1: `PASS`. Primer arranque en
  BIOS, SDDM, login `supratest` y Plasma Wayland: `PASS`. El target queda en
  Btrfs con los subvolúmenes `@`, `@home` y `@snapshots`; Calamares, casper y
  `supralinux-calamares-config` no quedan instalados.
- L5: `apt-get update` y reinstalación desde `https://repo.supralinux.com/
  testing` `PASS`; Snapper lista por D-Bus y `--no-dbus`, crea snapshot y
  registra APT pre; ksecretd expone `org.freedesktop.secrets`; Firefox abre en
  español sin pedir ser el navegador por defecto; apagado limpio `PASS`.
- `supralinux-defaults 1.1.2`: perfil AppArmor exacto `firefox-supralinux` y
  `obexd -P pbap,irmc`; los procesos de Firefox quedan etiquetados y
  `journalctl -p err` no muestra EDS/Evolution.
- El intento con `supralinux-calamares-config` 1.0.0 falló en el módulo
  `packages` porque intentaba quitar paquetes ausentes con listas APT vacías.
  Se corrigió en 1.0.1, se recompiló y se repitió la instalación.
- AppArmor y Btrfs `@` en VM desechable: sin el override,
  `linux-boot-prober /dev/loop1` falla con `mount ... flags="rw, bind"` denegado;
  con `supralinux-defaults 1.2.5` instalado, el mismo comando devuelve las
  entradas de arranque y el journal no registra la denegación del mount.
  Evidencia en `evidence/qa/apparmor-os-prober-20261122/`.
- kio-admin en live desechable: con `ShowInHome=true` por defecto el menú de
  Dolphin muestra “Abrir como administrador” al seleccionar la carpeta
  personal; con `ShowInHome=false` desaparece allí y sigue apareciendo fuera
  del home. Evidencia en `evidence/qa/kio-admin-home-20261122/`.
- ISO final `0611853b…` (`supralinux-aurora-1.0.0-amd64.iso`, snapshot
  `20261122g`): BIOS y UEFI Secure Boot `PASS` con `supralinux-theme 1.1.3`,
  `supralinux-defaults 1.2.5`, `kio-admin 25.12.3-0supralinux2` y
  `supralinux-branding 1.3.2`; default oscuro, tema claro con selección
  `#51A2DA`/neutral `#F67400`, SDDM claro disponible, wallpapers Light/Dark,
  icono `supralinux-white-blue` opcional, página del Monitor con colores
  distintos, “Abrir como administrador” en todas las carpetas locales y
  `switchCategoryOnHover=true`. La sonda Btrfs `@` de AppArmor también quedó
  validada en la live: `linux-boot-prober` devuelve las entradas sin denegación
  del mount. `GRUB_GFXMODE` y sonido `Supralinux-KDE3` presentes. La matriz
  L3/L4/L6 se ejecutó sobre la ISO `547fd33b…`, que comparte instalador, base y
  kernel; el delta son los paquetes de escritorio. Los detalles y la evidencia
  están en `manifests/iso-1.0.0.json` y `evidence/qa/`.
- SDDM claro: `supralinux-light` carga sin errores QML y queda disponible en
  el KCM; la validación visual final se hará en la reinstalación NVMe.
- LUKS2: rollback automático sigue fuera de alcance en 1.0.0.
- RAID: en un arranque limpio, el live detiene el array (sin `/dev/md*`) y
  Calamares ofrece solo `vda`, `vdb` y `vdc`; el target recibe `mdadm.conf` y
  reensambla el array con los datos intactos. Evidencia:
  `evidence/qa/l4-e-raid-clean/`.
- Preflight de la GUI de recuperación (ISO `b830b764…`, rootfs de prueba con
  paquetes 1.0.1/1.1.2): el icono aparece junto a Calamares, la GUI lista dos
  instantáneas, restaura la raíz, conserva `@home`, deja `@pre-rollback-*` y la
  entrada Recovery autolanza la GUI. Es un preflight, no un PASS de release.
  Evidencia: `evidence/live/gui-recovery-preflight-20261120/`.
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
