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
   checksums.
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

Nombres:

```text
supralinux-aurora-1.0.0-amd64.iso
supralinux-aurora-1.0.0-amd64.iso.sha256
supralinux-aurora-1.0.0-amd64.iso.sha256.asc
supralinux-aurora-1.0.0-amd64.manifest.json
```

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
| Instalador | Btrfs, LUKS2, EXT4, dual-boot y offline `PASS`. |
| Post-instalación | Keyring, Firefox, APT, Snapper y apagado `PASS`. |
| Recuperación | Rollback y preservación de `/home` `PASS`. |
| Repositorio | `InRelease` verificado y snapshot `stable` exacto. |
| Inventario | 176 paquetes fuente listados y sin paquetes de prueba. |
| Documentación | Sin enlaces rotos; versión y changelog coherentes. |
| Higiene | Sin secretos, artifacts ni datos personales en Git. |
| Autorización | Publicación estable aprobada explícitamente. |

Un gate `BLOCKED` o `INFRA_INVALID` no se convierte en `PASS`. Si un gate no se
puede completar, la release se detiene o se publica con un alcance menor
explícitamente documentado, nunca con una afirmación falsa.

## Estado de validación (2026-11-18)

- Suite unitaria: `PASS`.
- 9 paquetes nativos del producto y el paquete sintético: build limpio `PASS`,
  con artifact y evidencia.
- Muestras de Frameworks, Plasma y Gear: `extra-cmake-modules`,
  `libkf6coreaddons6`, `libkwin6` y `dolphin` con build limpio `PASS`.
- Smoke offline: `supralinux-build-test` y `supralinux-base-files` con
  instalación, control negativo y rechazo de índices manipulados `PASS`.
- Los 176 paquetes fuente y la ISO no se construyeron completos.
- Clave pública Ed25519 publicada en `installer/keys/supralinux-archive-key.asc`
  (huella `9BAD7A4B1826213B3BE271E208780B9EEC43C2B8`); la privada está en
  `SUPRALINUX_SECRETS`.
- Instancia Aptly paralela creada con `supralinux-testing` y
  `supralinux-stable` vacíos. No está publicada ni reemplaza a la anterior.
- No hay snapshot `stable` ni autorización de release.

Esto no es una release validada. Los gates de la tabla siguen pendientes hasta
completar el build de todos los paquetes y la matriz de ISO.

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
