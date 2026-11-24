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
- Probe propio de os-prober para raíces Btrfs en `@`, de modo que GRUB detecte
  otras instalaciones SupraLINUX en el mismo disco o en dos discos.
- Icono opcional `supralinux-white-blue` para el menú Inicio, con SVG y PNGs
  16–512; el default sigue siendo `supralinux-color`.
- Página por defecto del Monitor del sistema con colores distintos para CPU,
  GPU, memoria e intercambio, pensada para usuarios nuevos y la live.
- Soporte de PPAs con `add-apt-repository`: `supralinux-defaults` instala el
  template `supralinux.info` para la suite `resolute` y declara
  `python-apt-common` como dependencia.

### Changed

- El tema global oscuro Aurora es el default para instalaciones nuevas; el
  tema claro sigue instalado y seleccionable. GTK 3/4, el estilo Plasma y el
  splash acompañan el default oscuro.
- El tema claro usa una selección `#51A2DA` y neutral `#F67400` para que las
  barras, anillos y badges se vean; el estilo Plasma light queda alineado.
- SDDM ofrece una variante clara seleccionable, sin herencia automática del
  wallpaper del usuario. El fondo del login claro queda atenuado a 0.68 para
  mantener legibles el reloj, el campo de contraseña y los controles.
- Los temas de iconos usan los IDs canónicos `SupraLINUX-Dark` y
  `SupraLINUX-Light`, con nombres visibles `SupraLINUX Oscuro` y
  `SupraLINUX Claro`. La metadata completa y el árbol de symlinks derivado de
  Breeze cubren todos los nombres estándar, también en aplicaciones de
  terceros como Kdenlive.
- Wallpapers: entradas sueltas `SupraLINUX Aurora Light` y `Dark`, además de
  la automática.
- El lanzador cambia de categoría al pasar el puntero por defecto en paneles
  nuevos.
- Dolphin muestra “Abrir como administrador” en todas las carpetas locales,
  incluido el home. Se puede recuperar el comportamiento original de KDE con
  `ShowInHome=false` en `~/.config/kio-adminrc`.
- El menú GRUB conserva otras instalaciones SupraLINUX con raíz Btrfs `@`:
  un override local de AppArmor permite a `linux-boot-prober` el `mount --bind`
  que os-prober necesita para generar la entrada.

### Fixed

- KDE Connect aplica en el acto los cambios de plugins de la app: al destildar
  “Recibir notificaciones” el daemon descarga el plugin sin esperar a
  reconectar el teléfono ni reiniciar `kdeconnectd`.

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
