# Changelog

Todos los cambios importantes de SupraLINUX se registran en este archivo.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el versionado usa [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

### Added

- Documentación de producto, arquitectura, packaging, desarrollo, pruebas,
  release, Secure Boot, procedencia, decisiones y compatibilidad.
- Guías de build limpio, imagen live e instalador.
- Registro de reutilización del proyecto anterior.
- Herramientas de host, importación, build limpio, smoke tests y paquete sintético.
- Builds limpios de 10 paquetes nativos y muestras de Frameworks, Plasma y Gear.
- Packaging de KDE Frameworks 6.24, Plasma 6.6.7 y Gear 25.12.3.
- Integración de Calamares, Secure Boot, Btrfs/Snapper y recuperación live.
- Branding y tema Aurora.
- Identidad `supralinux-base-files`, fuentes y defaults.
- Firefox con paquetes de idioma español.
- Repositorio APT firmado y fuentes de paquetes modificados.
- URLs limpias en el sitio (`/bugs`, `/download`, `/docs`) con redirecciones
  301 desde `.html`, `security.txt` y cabeceras COOP/CORP.
- Gwenview con la rueda del ratón en “Ampliar” por defecto.
- Recuperación gráfica live-only (`supralinux-recovery-gui 1.0.0`): lista las
  instantáneas de Snapper, restaura la raíz Btrfs con progreso y se lanza desde
  la entrada Recovery del GRUB; se elimina del sistema instalado.
- `os-prober` en el live y en el sistema instalado para que GRUB detecte otras
  instalaciones Linux en dual-boot.

## [1.0.0] - Por anunciar

Primera release pública de SupraLINUX, nombre clave **Aurora**.

### Added

- Base Ubuntu 26.04 LTS.
- KDE Plasma 6.6.7, Frameworks 6.24, Gear 25.12.3 y Qt 6.10.2.
- Instalador Calamares con Btrfs, LUKS y RAID de datos.
- Secure Boot en BIOS y UEFI con la cadena firmada de Ubuntu.
- Snapper y recuperación desde el entorno live.
- Keyring/Secret Service por usuario.
- Tema Aurora, fuentes y ajustes de escritorio.
- Firefox con español preinstalado.
- Repositorio APT firmado y manifiestos de build.

### Fixed

- El formulario de bugs usa `X-Real-IP` para el rate limit, rechaza
  `Origin` externo y responde con `Cache-Control: no-store`.
- `BUG_REPORT_URL` apunta a `https://supralinux.com/bugs`.

- `supralinux-base-files 1.0.1`: `LOGO=distributor-logo` para que Acerca de
  este sistema muestre el logo; el icono ya lo instala `supralinux-branding`.
- Documentado el límite de WiFi en live: la primera conexión sin perfil
  guardado puede conservar un `AccessPoint` obsoleto en `plasma-nm`; usar
  `nmcli`/`nmtui` o reintentar (D-025).
- `ark`: el visor interno abre en 800×600 cuando no hay tamaño guardado,
  recuerda su tamaño entre sesiones y la extracción de RAR multivolumen ya
  no se bloquea por un tamaño estimado inflado (D-026).

[Unreleased]: https://supralinux.com/
[1.0.0]: https://supralinux.com/
