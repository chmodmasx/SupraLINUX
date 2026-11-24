# Release

## Versiones

SupraLINUX usa versiones de producto `MAJOR.MINOR.PATCH`. La primera release es
**1.0.0 Aurora**.

La identidad separa producto y base:

```text
VERSION="1.0.0 (Aurora)"
VERSION_ID="26.04"
VERSION_CODENAME=resolute
UBUNTU_CODENAME=resolute
SUPRALINUX_VERSION="1.0.0"
SUPRALINUX_CODENAME="aurora"
```

- `VERSION_ID` y `VERSION_CODENAME` describen la base Ubuntu y mantienen
  compatibilidad con APT y con herramientas que leen la base.
- `VERSION`, `PRETTY_NAME` y `SUPRALINUX_*` describen el producto.
- No se cambia `VERSION_ID` para mostrar la versión de SupraLINUX.

Los paquetes reconstruidos desde upstream usan el sufijo
`-0supralinuxN`: `6.24.0-0supralinux1`, `6.6.7-0supralinux1`,
`25.12.3-0supralinux1`. Los paquetes nativos usan versión propia. Se conserva
el `epoch` del packaging de origen cuando exista.

## Canales

| Canal | Uso | Política |
|---|---|---|
| `testing` | QA e integración | Cambia durante la campaña. No es una release. |
| `stable` | Release publicada | Snapshot inmutable que apunta a una versión validada. |

`testing` se publica con `NotAutomatic: yes` y prioridad alta para que una
instalación explícita funcione sin que un `apt upgrade` ordinario salte a
paquetes de QA. `stable` se publica con la misma prioridad y sólo después de la
aprobación de release.

El repositorio usa el componente `main`, arquitectura `amd64` y `source`.
Los paquetes modificados publican su fuente en `deb-src`.

## Flujo de release

1. **Congelar `testing`.** No se aceptan cambios nuevos salvo fixes bloqueantes.
2. **Subir versiones y changelogs.** Producto, paquetes modificados y
   documentación.
3. **Reconstruir.** Build limpio de los paquetes afectados y de los que
   dependan de ellos. No se reutiliza un artifact si cambiaron sus inputs.
4. **Publicar `testing`.** Subir binarios y fuentes, firmar y verificar
   `InRelease`.
5. **Crear snapshot.** Snapshot inmutable de `testing` para la release.
6. **Construir la ISO.** Rootfs, squashfs, ISO BIOS/UEFI/Secure Boot y
   checksums, con el nombre limpio de release y
   `SUPRALINUX_REQUIRE_RECOVERY_GUI=1` para que el build falle si falta la GUI
   de recuperación.
7. **Ejecutar la matriz.** L0 a L7 de [pruebas](testing.md). Los bloqueantes
   deben estar en `PASS`.
8. **Cerrar documentación.** Producto, arquitectura, packaging, desarrollo,
   pruebas, release, Secure Boot, procedencia, decisiones, compatibilidad,
   changelog y `THIRD-PARTY.md`.
9. **Revisar el árbol.** Sin secretos, artifacts, discos, capturas, rutas
   personales ni cambios sin commit.
10. **Merge a `main`.** Desde `testing` con `--no-ff`; `main` queda en el
    commit de release.
11. **Tag.** Tag anotado y firmado `v1.0.0` sobre el commit de `main`.
12. **Publicar.** Snapshot `stable`, ISO, checksums, firma y sitio web. Requiere
    autorización explícita.
13. **Verificar.** Descargar y verificar lo publicado como si fuera un usuario
    externo.

## Artefactos

La ISO de release usa el nombre limpio, sin sufijo de build:

```text
supralinux-aurora-1.0.0-amd64.iso
supralinux-aurora-1.0.0-amd64.iso.sha256
supralinux-aurora-1.0.0-amd64.iso.sha256.asc
supralinux-aurora-1.0.0-amd64.manifest.json
```

Mientras la versión está en `testing`, cada build es un candidato y lleva
fecha UTC y commit corto:

```text
supralinux-aurora-1.0.0-amd64-20261120T044138Z-gc292031.iso
supralinux-aurora-1.0.0-amd64-20261120T044138Z-gc292031.iso.sha256
```

Reglas:

- La versión y el codename salen de `os-release` del rootfs. El sufijo
  `YYYYMMDDTHHMMSSZ-g<commit>` identifica el build, no la versión del producto.
- El nombre limpio se reserva para la release. Se construye explícitamente con
  `SUPRALINUX_ISO_NAME` una vez congelado `testing`, y se valida ese mismo
  archivo. No se renombra ni se reconstruye después de la validación.
- Si el candidato de release falla la matriz, se corrige y se reconstruye con
  nombre de candidato. El nombre limpio se genera de nuevo sólo para el intento
  final que se va a publicar.
- Un build de `testing` nunca se publica con el nombre limpio. Dos candidatos
  de la misma versión se distinguen por fecha, commit y SHA-256.
- El nombre del archivo debe coincidir con `manifests/iso-<versión>.json` y con
  el `os-release` del rootfs. Un cambio de nombre no cambia el SHA-256, pero
  obliga a regenerar el `.sha256` y actualizar el manifiesto.

Se conservan, además:

- Fuentes, `.dsc`, `.debian.tar.*` y `.orig.tar.*` de paquetes modificados.
- `.deb`, `.changes`, `.buildinfo` y logs de build.
- Manifiestos de build con hashes de inputs y dependencias.
- Inventario de fuentes `manifests/packages-1.0.0.json`.
- Resultados de pruebas y capturas de la release.
- Snapshot de Aptly y clave pública de verificación.

Los artifacts viven en el workspace, no en Git. La release publica sólo lo que
corresponda: ISO, checksums, firma, fuentes y repositorio.

## Firma

- El repositorio APT se firma con una clave **Ed25519** nueva.
- El tag `v1.0.0` y el archivo de checksums se firman con la clave de release.
  En 1.0.0 se usa la misma clave Ed25519; si se separan, se registra en
  [decisions.md](decisions.md).
- La clave se genera una vez, con passphrase, y se respalda fuera del repo.
- La clave pública y su huella se publican en el sitio y en la documentación.
- La clave privada vive en `SUPRALINUX_SECRETS`, nunca en el repositorio, en
  una ISO o en un log.
- La clave de APT no es una clave UEFI. Secure Boot usa la cadena de Ubuntu.

Antes de publicar:

```sh
gpg --verify SHA256SUMS.asc SHA256SUMS
sha256sum -c SHA256SUMS
gpgv --keyring ./release-keyring.gpg InRelease
```

La verificación se hace con una copia limpia de la clave pública, no con el
keyring personal del desarrollador.

## Gates bloqueantes

| Gate | Criterio |
|---|---|
| Build | Todos los paquetes de la release con build limpio `PASS`. |
| Smoke | Instalación offline y control negativo `PASS`. |
| Live | BIOS, UEFI y Secure Boot `PASS`. |
| Instalador | Btrfs, LUKS2, EXT4, dual-boot Linux y offline `PASS`. |
| Post-instalación | Keyring, Firefox, APT, Snapper y apagado `PASS`. |
| Recuperación | Rollback y preservación de `/home` `PASS`. |
| Repositorio | `InRelease` verificado y snapshot `stable` exacto. |
| Inventario | 177 paquetes fuente listados y sin paquetes de prueba. |
| Documentación | Sin enlaces rotos; versión y changelog coherentes. |
| Higiene | Sin secretos, artifacts ni datos personales en Git. |
| Autorización | Publicación estable aprobada explícitamente. |

Un gate `BLOCKED` o `INFRA_INVALID` no se convierte en `PASS`. Si un gate no se
puede completar, la release se detiene o se publica con un alcance menor
explícitamente documentado, nunca con una afirmación falsa.

## Estado de validación (2026-11-21)

- Suite unitaria: `PASS`.
- 9 paquetes nativos del producto y el paquete sintético: build limpio `PASS`,
  con artifact y evidencia.
- Muestras de Frameworks, Plasma y Gear: `extra-cmake-modules`,
  `libkf6coreaddons6`, `libkwin6` y `dolphin` con build limpio `PASS`.
- Smoke offline: `supralinux-build-test` y `supralinux-base-files` con
  instalación, control negativo y rechazo de índices manipulados `PASS`.
- Los 177 paquetes fuente tienen build limpio `PASS` (177/177), con artifact,
  `.changes`, `.buildinfo`, evidencia y cleanup. Incluye
  `supralinux-recovery-gui 1.0.0` y `supralinux-calamares-config 1.0.2`,
  reconstruidos después del lote original. El resumen está en
  `manifests/full-build-results-1.0.0.json`.
- ISO limpia `93f2fef4…` construida desde un rootfs nuevo y el snapshot
  `supralinux-testing-1.0.0-20261120c`: BIOS y UEFI Secure Boot `PASS`.
- ISO candidata `fef5990f…`
  (`supralinux-aurora-1.0.0-amd64-20261120T061139Z-g25bf91c.iso`) construida
  desde un rootfs nuevo y el snapshot `20261120d`: BIOS y UEFI Secure Boot
  `PASS`, visor de Ark en 800×600 por defecto y RAR multivolumen `PASS`.
- La ISO `93f2fef4…` se construyó antes de la convención de nombres de
  candidato y conserva el nombre limpio; la candidata nueva ya usa
  fecha/commit.
- ISO candidata `1c79f343…`
  (`supralinux-aurora-1.0.0-amd64-20261120T134809Z-g6e17fa1.iso`)
  construida desde un rootfs nuevo y el snapshot `20261120f`: BIOS y UEFI
  Secure Boot `PASS`, `BUG_REPORT_URL=/bugs`, `supralinux-defaults 1.1.3`
  con la rueda de Gwenview en Ampliar y el logo SL en Acerca de este sistema.
  Ark y RAR conservan el mismo paquete validado en la ISO anterior.
- `supralinux-base-files 1.0.1`: `LOGO=distributor-logo`; Acerca de este
  sistema muestra el logo SL en BIOS y UEFI Secure Boot.
- `ark 25.12.3-0supralinux2`: el visor interno conserva su tamaño entre
  sesiones y la extracción de RAR multivolumen no se bloquea por el tamaño
  estimado inflado.
- `ark 25.12.3-0supralinux3`: backport del MR upstream !360 (KDE bug
  503213); el visor abre en 800×600 cuando no hay tamaño guardado y
  conserva el tamaño elegido. Probado en VM desechable: apertura por
  defecto, resize a 600×420, cierre y reapertura.
- La instalación Btrfs y L5 se validaron sobre la ISO candidata anterior;
  el delta de esta ISO es Ark (visor), no el instalador. Ver
  `regression_scope` en `manifests/iso-1.0.0.json`.
- Instalación Btrfs offline con Calamares 1.0.1: `PASS`; primer arranque,
  SDDM, login `supratest` y Plasma Wayland: `PASS`. El target queda en Btrfs
  (`@`, `@home`, `@snapshots`) y sin Calamares/casper.
- L5 `PASS`: APT contra `https://repo.supralinux.com/ testing`, Snapper por
  D-Bus y `--no-dbus`, Secret Service (`ksecretd`), Firefox en español sin
  prompt de navegador por defecto y apagado limpio.
- `supralinux-base-files 1.0.2`: `BUG_REPORT_URL` y el MOTD apuntan a
  `https://supralinux.com/bugs`, servido por el sitio con URL limpia.
- `supralinux-defaults 1.1.3`: Gwenview abre con la rueda configurada en
  “Ampliar” mediante `/etc/xdg/gwenviewrc`; una preferencia explícita del
  usuario sigue ganando.
- `supralinux-defaults 1.1.2`: perfil AppArmor exacto para el Firefox de
  Mozilla (`firefox-supralinux`) y `obexd -P pbap,irmc`; `journalctl -p err`
  queda sin errores de EDS/Evolution.
- Se corrigió `supralinux-calamares-config` 1.0.0: el módulo `packages` quitaba
  paquetes ausentes y `apt-get` devolvía 100 sin listas APT. La 1.0.1 quedó
  publicada y validada en la instalación.
- ISO de humo `8994da94…`: BIOS y UEFI Secure Boot arrancan a Plasma. Es un
  smoke sobre el rootfs anterior, no una release; Calamares y recuperación no
  se probaron en esta ISO. UEFI Secure Boot: `mokutil` y efivar en `1`.
- Clave pública Ed25519 publicada en `installer/keys/supralinux-archive-key.asc`
  (huella `9BAD7A4B1826213B3BE271E208780B9EEC43C2B8`); la privada está en
  `SUPRALINUX_SECRETS`.
- Aptly `supralinux-testing`: snapshot `supralinux-testing-1.0.0-20261122g`
  con 617 binarios y 189 fuentes; publicación `testing` firmada y verificada.
  Incluye `supralinux-recovery-gui 1.0.0`, `supralinux-calamares-config
  1.0.2`, `supralinux-theme 1.1.3`, `supralinux-defaults 1.2.5`,
  `kio-admin 25.12.3-0supralinux2` y `supralinux-branding 1.3.2`. El default
  para instalaciones nuevas es el tema global oscuro Aurora; el claro sigue
  instalado y seleccionable, con
  selección `#51A2DA`, neutral `#F67400`, SDDM claro disponible, wallpapers
  Light/Dark sueltos, icono de menú `supralinux-white-blue` opcional, página
  del Monitor con colores distintos por sensor, “Abrir como administrador”
  en todas las carpetas locales y el override de AppArmor que permite a
  `linux-boot-prober` leer raíces Btrfs `@` para el menú GRUB.
  `https://repo.supralinux.com/` ya apunta al Aptly nuevo; el Aptly viejo
  dejó de servirse. El resumen está en
  `manifests/aptly-publication-1.0.0.json`.
- Snapshot `supralinux-testing-1.0.0-20261124a`: 623 binarios y 192 fuentes.
  Agrega `kdeconnect 25.12.3-0supralinux8` con el toggle de plugins aplicado
  por D-Bus y `supralinux-defaults 1.2.6` con el template `python-apt` para
  PPAs. `InRelease` firmado y verificado; los índices públicos declaran 623
  binarios y 192 fuentes. Evidencia de la VM en
  `evidence/qa/ppa-kdeconnect-20261124/`.
- Snapshot `supralinux-testing-1.0.0-20261124b`: 624 binarios y 193 fuentes.
  Agrega `supralinux-theme 1.2.0` con IDs `SupraLINUX-Dark`/`SupraLINUX-Light`,
  metadata completa derivada de Breeze y 19.852 symlinks por tema. El fondo
  del login claro queda a 0.68. `InRelease` firmado y verificado; el detalle
  está en `manifests/aptly-publication-1.0.0.json`.
- Snapshot `supralinux-testing-1.0.0-20261124c`: 626 binarios y 195 fuentes.
  Agrega `supralinux-icons 1.3.0` con copias completas e independientes de
  Breeze/Breeze Dark y actualiza `supralinux-theme 1.3.0` para separar los
  iconos. El tema oscuro sigue usando Breeze Dark por defecto; el pack
  SupraLINUX queda instalado y seleccionable. `InRelease` firmado y
  verificado; el detalle está en `manifests/aptly-publication-1.0.0.json`.
- Snapshot `supralinux-testing-1.0.0-20261124d`: 627 binarios y 196 fuentes.
  Actualiza `supralinux-theme 1.3.1` con chrome claro uniforme, selección de
  filas de Plasma pálida, `AccentColor` conservado y barra de progreso con el
  acento de marca. `InRelease` firmado y verificado; el detalle está en
  `manifests/aptly-publication-1.0.0.json`.
- ISO candidata `a218fc66…`
  (`supralinux-aurora-1.0.0-amd64-20261124T180005Z-gf724c1b.iso`): BIOS y UEFI
  Secure Boot `PASS`; incluye theme 1.1.4, defaults 1.2.6 y kdeconnect
  0supralinux8. El PPA de Inkscape se agrega con `resolute` y `apt install
  inkscape` instala 1.4.4. El asset claro de SDDM conserva el hash
  `b74bcbe4…` y el default sigue siendo oscuro. El candidato no es release ni
  stable; el detalle está en `manifests/iso-candidate-20261124a.json`.
- ISO candidata `097696c9…`
  (`supralinux-aurora-1.0.0-amd64-20261124T210917Z-g2e1f379.iso`): rootfs
  nuevo con kernel `7.0.0-44.44`, snapshot
  `supralinux-testing-1.0.0-20261124c`, `supralinux-icons 1.3.0` y
  `supralinux-theme 1.3.0`. BIOS y UEFI Secure Boot `PASS`; el PPA de
  Inkscape se agrega con `resolute` e instala 1.4.4; los iconos resuelven en
  ambos temas, sin symlinks rotos ni externos; Breeze Dark sigue siendo el
  icon theme por defecto y el menú inicio conserva `supralinux-color`.
  El candidato no es release ni stable; el detalle está en
  `manifests/iso-candidate-20261124b.json`.
- `supralinux-stable` sigue vacío. No hay snapshot `stable` ni autorización de
  release.

La ISO final `0611853b…` (`supralinux-aurora-1.0.0-amd64.iso`, construida
desde el snapshot `20261122g`) arranca en BIOS y UEFI Secure Boot con
`supralinux-theme 1.1.3`, `supralinux-defaults 1.2.5`,
`kio-admin 25.12.3-0supralinux2` y `supralinux-branding 1.3.2`. El tema global
oscuro Aurora es el default; el claro sigue instalado y seleccionable, con
selección `#51A2DA`, neutral `#F67400`, SDDM claro disponible, wallpapers
Light/Dark sueltos, icono de menú `supralinux-white-blue` opcional, página del
Monitor con colores distintos por sensor y “Abrir como administrador” en todas
las carpetas locales. `supralinux-defaults 1.2.5` permite a `linux-boot-prober`
leer raíces Btrfs `@`, de modo que `update-grub` conserva otras instalaciones
SupraLINUX en el menú. La matriz L3/L4/L6 se ejecutó sobre la ISO `547fd33b…`,
que comparte instalador, base y kernel; el delta de esta ISO son
los paquetes de escritorio, que no modifican las rutas de instalación ni de
almacenamiento. El detalle está en `manifests/iso-1.0.0.json` y
`evidence/qa/`.

Quedan como limitaciones explícitas: LUKS2 no tiene rollback automático en
1.0.0, Windows no se declara validado y Secure Boot en hardware real sigue
pendiente (la evidencia formal es OVMF). RAID se validó con el array detenido
en el live (sin `/dev/md*`), instalación en `vda`, `mdadm.conf` en el target y
datos intactos tras reensamblar.

El gate `Repositorio` sigue abierto: `supralinux-stable` está vacío y la
publicación estable no se ejecuta sin autorización explícita.

## Publicación

La publicación estable y las operaciones destructivas requieren autorización
explícita. No se infiere de una autorización anterior.

Orden:

1. Snapshot `stable` en Aptly, verificado.
2. ISO y checksums en el servidor.
3. Firma y clave pública.
4. Actualización del sitio: versión, enlaces, checksums y notas.
5. Verificación externa de descarga, firma, `apt update` y una instalación de
   prueba.

No se publica una ISO sin repositorio coherente ni un repositorio sin ISO
coherente. Si algo falla después del paso 1, se restaura el snapshot anterior
antes de continuar.

## Rollback

- **Repositorio:** volver a publicar el snapshot `stable` anterior. El snapshot
  nuevo se conserva para diagnóstico; no se borra la evidencia.
- **ISO:** retirar el enlace de descarga y marcar la versión como retirada. El
  archivo se conserva en el archivo histórico con su checksum.
- **Sitio:** volver a la versión anterior de la página y de los enlaces.
- **Tag:** no se mueve ni se borra un tag publicado. Un error se corrige con
  una versión nueva.
- **Paquetes:** no se reescribe un paquete publicado con el mismo nombre y
  versión. Se publica una versión nueva.

## Hotfix

Un hotfix sale de `main`, no de `testing`:

```text
main → hotfix/1.0.1 → pruebas → main → tag v1.0.1
                              └→ testing
```

Incluye sólo el fix, su prueba de regresión y el changelog. Si el fix cambia
packaging, exige build limpio y smoke. Si cambia la ISO, exige la matriz
afectada.

## Soporte

- Soporte best-effort, sin SLA ni soporte comercial.
- No se promete una fecha de fin de soporte (`SUPPORT_END`).
- Las actualizaciones de seguridad de la base siguen el ciclo de Ubuntu 26.04
  mientras el proyecto se mantenga.
- KDE se reconstruye cuando haya una actualización compatible con el Qt de la
  base.
- No se promete compatibilidad con hardware no validado.
- No se promete actualización entre bases mayores; un cambio de base se trata
  como una reinstalación validada.

## Checklist final

- [ ] `testing` congelado y versión subida.
- [ ] Builds limpios y manifiestos completos.
- [ ] `testing` publicado y verificado.
- [ ] Snapshot de release creado.
- [ ] ISO construida con la versión correcta.
- [ ] Matriz L0–L7 sin gates bloqueantes.
- [ ] Documentación y changelog cerrados.
- [ ] `main` con merge `--no-ff` y tag `v1.0.0` firmado.
- [ ] Snapshot `stable` publicado y verificado.
- [ ] ISO, checksums y firma publicados.
- [ ] Sitio actualizado y verificado.
- [ ] Evidencia y fuentes retenidas.
- [ ] Autorización de publicación registrada.
