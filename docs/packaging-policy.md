# Política de packaging

## Fuentes

- **Ubuntu 26.04 LTS**: referencia de packaging, dependencias, ABI y compatibilidad.
- **KDE upstream**: tarballs oficiales de Frameworks, Plasma y Gear, verificados por SHA-256.
- **Qt**: se consume el de Ubuntu; no se reconstruye.
- No se mezclan versiones de Frameworks, Plasma o Gear dentro de una release.
- No se seleccionan betas o RC como base de una release estable.

## Importación

1. Partir del packaging Ubuntu 26.04 de la misma rama cuando exista.
2. Conservar `debian/`, `debian/patches/` y `debian/copyright`.
3. Retirar metadatos internos de la distro de origen (Salsa, CI, VCS) que no correspondan.
4. Revisar cada parche: conservar los necesarios, retirar los obsoletos y documentar el motivo.
5. Verificar que el paquete construya contra el Qt y las bibliotecas de la base.
6. Registrar fuente, versión, checksums y dependencias en un manifiesto.

## Parches

- Mínimos y con una razón concreta.
- Documentados en `debian/patches/series` y, si cambian comportamiento, en `docs/provenance.md`.
- Preferir upstream o el packaging Ubuntu antes que un parche propio.
- No parchear Calamares: su configuración va en un paquete separado.
- No introducir parches de seguridad propios; se siguen los de Ubuntu/KDE.

## ABI y símbolos

- Mantener los archivos `symbols` y las transiciones ABI.
- No ocultar un cambio de ABI con un parche de símbolos.
- Revisar `libplasma`, `libksysguard`, `libkscreen`, `kwallet`, `kwin` y las bibliotecas KF6 en cada actualización.
- Un cambio de soname exige reconstruir los consumidores y probar la instalación.

## Versiones

- Paquetes reconstruidos desde upstream: `6.6.7-0supralinuxN`, `6.24.0-0supralinuxN`, `25.12.3-0supralinuxN`.
- Paquetes nativos de SupraLINUX: versión propia, por ejemplo `1.0.18` o `1.1.0`.
- Conservar el `epoch` del packaging Ubuntu cuando exista.
- Cada cambio de paquete lleva una entrada clara en `debian/changelog`.
- No se publica un paquete sin build limpio y manifiesto.

## Build limpio

- `sbuild`/`unshare` sobre un rootfs retenido.
- Sin SDKs preinstalados que oculten `Build-Depends`.
- Dependencias declaradas y resueltas desde fuentes retenidas.
- `debhelper` y `dh_missing --fail-missing`.
- `SOURCE_DATE_EPOCH` y opciones deterministas cuando aplique.
- `lintian` en paquetes propios.
- `autopkgtest` en paquetes clave.
- `reprotest` en paquetes clave, no en los 184 paquetes de una vez.

## Copyright y licencias

- `debian/copyright` en formato DEP-5.
- Cubrir código, assets, fuentes, traducciones y vendor.
- Conservar avisos de copyright y licencias de terceros.
- `THIRD-PARTY.md` es un índice; la fuente autoritativa es cada `debian/copyright`.
- Los paquetes modificados publican su fuente en `deb-src`.

## Categorías

| Categoría | Contenido |
|---|---|
| `packages/kde` | Frameworks 6.24 |
| `packages/plasma` | Plasma 6.6.7 |
| `packages/gear` | Aplicaciones Gear 25.12.3 |
| `packages/gear-extras` | Extras de completitud KDE |
| `packages/desktop` | Integración SupraLINUX, tema, defaults, hardware |
| `packages/apps` | Apps propias |
| `packages/system` | casper y hardware específico |
| `packages/fonts` | Fuentes empaquetadas |
| `packages/fastfetch` | Configuración de fastfetch |

- `packages/gear-extras` reemplaza el nombre antiguo `complete`.
- La lista de instalación es `packages/desktop/desktop-packages.list`.
- `supralinux-base-files` posee la identidad con `dpkg-divert`.
- `supralinux-calamares-config` instala `/etc/calamares`; no se copia a mano.
- No se instala `calamares-settings-kubuntu`.

## Artefactos

No se commitean:

- `.deb`, `.udeb`, `.changes`, `.buildinfo`, `.dsc`.
- `.orig.tar.*`, `.debian.tar.*`.
- ISOs, imágenes de disco, `.qcow2`, `.vmdk`, `.vdi`.
- Logs, capturas del host, `__pycache__`, credenciales.

Las fuentes y artefactos se conservan en el workspace y se referencian desde
los manifiestos.

## Gates de paquete

- Build limpio PASS.
- Instalación/desinstalación PASS.
- Dependencias resueltas desde el repositorio y la base.
- Sin archivos sin empaquetar (`dh_missing`).
- Copyright completo.
- Manifiesto y checksums.
- Fuente publicada si el paquete fue modificado.
