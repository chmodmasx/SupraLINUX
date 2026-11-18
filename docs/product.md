# Producto

SupraLINUX es una distribución Linux personal basada en **Ubuntu 26.04 LTS**, con **KDE Plasma 6.6.7**, **Frameworks 6.24**, **Gear 25.12.3** y **Qt 6.10.2**.

La release 1.0.0 se llama **Aurora**.

## Base

- Ubuntu 26.04 LTS es la base técnica: kernel, firmware, drivers, Qt y bibliotecas de plataforma.
- SupraLINUX selecciona, compila, empaqueta e integra el escritorio KDE.
- No se reconstruye Qt ni se mantiene un fork de KDE.
- La versión de KDE se elige por compatibilidad con el Qt de la base LTS, no por la cadencia de otra distro.
- No se mezclan versiones de Frameworks, Plasma o Gear dentro de la misma release.

## Escritorio

- Sesión de usuario **Wayland**, con XWayland para aplicaciones X11.
- SDDM usa Xorg solo para el greeter.
- KDE Plasma con Breeze, KDE Gear y las aplicaciones del perfil de escritorio.
- Tema Aurora, fuentes y ajustes propios, sin reemplazar las opciones de fábrica de Breeze.
- Keyring/Secret Service por usuario, funcionando desde el primer inicio.

## Instalación

- Instalador **Calamares**.
- Btrfs por defecto, con subvolúmenes y Snapper.
- LUKS2 con `/boot` ext4 separado cuando corresponde.
- RAID de datos y dual-boot con Windows/Linux.
- BIOS y UEFI; Secure Boot con la cadena firmada de Ubuntu.
- Instalación offline-first y online.

## Recuperación

- Snapper crea instantáneas de la raíz.
- Rollback desde el entorno live.
- `/home` no se modifica durante el rollback.
- La raíz anterior se conserva como `@pre-rollback-<fecha>`.
- El sistema instalado debe quedar utilizable después de una actualización fallida.

## Aplicaciones y actualizaciones

- Firefox preinstalado, con paquetes de idioma español.
- Aplicaciones KDE Gear y utilidades de completitud.
- App **Controladores** basada en UbuntuDrivers y `ubuntu-drivers`, con `pkexec`.
- Flatpak/Flathub disponible.
- Repositorio APT propio, firmado, con `testing` y `stable`.
- La release 1.0.0 se entrega sin snapd; usa APT y Flatpak.
- Las actualizaciones de seguridad de la base siguen el ciclo de Ubuntu 26.04 mientras el proyecto se mantenga.

## Identidad

La identidad visible y la compatibilidad se separan:

```text
NAME="SupraLINUX"
ID=supralinux
ID_LIKE="ubuntu debian"
PRETTY_NAME="SupraLINUX Aurora 1.0.0"
VERSION="1.0.0 (Aurora)"
VERSION_ID="26.04"
VERSION_CODENAME=resolute
UBUNTU_CODENAME=resolute
SUPRALINUX_VERSION="1.0.0"
SUPRALINUX_CODENAME="aurora"
SUPRALINUX_BASE="Ubuntu 26.04 LTS"
```

- `VERSION_ID` y `VERSION_CODENAME` describen la base y mantienen compatibilidad.
- `PRETTY_NAME`, `VERSION` y `SUPRALINUX_VERSION` muestran la versión del producto.
- `/etc/lsb-release` informa `SupraLINUX Aurora 1.0.0` y el codename base.
- La identidad la posee `supralinux-base-files`, con `dpkg-divert` sobre `base-files`.

## Alcance

- Arquitectura amd64 para 1.0.0.
- Proyecto personal, sin garantía ni soporte comercial.
- Sin SLA; soporte comunitario best-effort.
- Sin promesa de soporte de hardware que no se haya probado.
- Sin cadena Secure Boot propia en 1.0.0; se usa la de Ubuntu.
- Sin snapd en la release 1.0.0.

## Fuera de alcance

- Reconstruir Qt, el kernel o los drivers de plataforma.
- Mantener un fork de KDE.
- Publicar betas o RC como release estable.
- Modificar distribuciones instaladas durante el desarrollo o las pruebas.
- Prometer compatibilidad con hardware no validado.
