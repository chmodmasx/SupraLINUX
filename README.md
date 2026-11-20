# SupraLINUX

Distribución Linux personal basada en **Ubuntu 26.04 LTS**, con **KDE Plasma 6.6.7**, instalador Calamares, Secure Boot y recuperación Btrfs.

> **Estado:** 1.0.0 Aurora en preparación.  
> Proyecto personal, sin garantía. No está afiliado a Canonical, Ubuntu ni KDE.

Sitio web: <https://supralinux.com>

## Qué es

SupraLINUX busca un escritorio KDE completo, una base LTS y las herramientas necesarias para instalar, actualizar y recuperar el sistema sin sorpresas.

Incluye:

- KDE Plasma 6.6.7, Frameworks 6.24, Gear 25.12.3 y Qt 6.10.2.
- Instalador Calamares con Btrfs, LUKS y RAID de datos.
- Secure Boot en BIOS y UEFI, usando la cadena firmada de Ubuntu.
- Snapper y recuperación desde el entorno live.
- Firefox con paquetes de idioma español.
- Keyring/Secret Service funcionando desde el primer inicio.
- Tema Aurora, fuentes y ajustes de escritorio.
- Repositorio APT firmado para paquetes propios.

La ISO se publicará cuando la release 1.0.0 esté validada.

## Base

| Componente | Versión |
|---|---|
| Base | Ubuntu 26.04 LTS |
| Escritorio | KDE Plasma 6.6.7 |
| Frameworks | 6.24 |
| Gear | 25.12.3 |
| Qt | 6.10.2 |
| Arquitectura | amd64 |

## Repositorio

```text
packages/       Packaging Debian de la distro
branding/       Identidad visual, GRUB, Plymouth y wallpapers
installer/      Configuración de Calamares y recuperación
tools/          Herramientas de build, importación y live
tests/          Pruebas y fixtures
docs/           Documentación
manifests/      Registros de build y release
```

## Documentación

- [Índice de documentación](docs/README.md)

La documentación completa se publica con la release 1.0.0.

## Compilar

El build usa un entorno limpio con `sbuild`/`unshare` y un rootfs retenido. Los pasos completos se publican con la documentación de la release 1.0.0.

No se modifica ninguna distribución instalada. Las pruebas se hacen en ISO, rootfs o VM desechable.

## Seguridad

Para fallos en KDE o Ubuntu, usá sus canales oficiales. Para fallos en el packaging, los defaults o la integración de SupraLINUX, reportá en privado:

- `https://supralinux.com/bugs` (marcá “seguridad” en el resumen).

No abras issues públicos para vulnerabilidades. Ver [SECURITY.md](SECURITY.md).

## Contribuir

El proyecto se desarrolla en local y no asume una plataforma de CI. Las reglas de ramas, commits, pruebas y DCO están en [CONTRIBUTING.md](CONTRIBUTING.md).

## Licencia

El código y la configuración propios usan **GPL-2.0-or-later**, con excepciones por paquete. El arte, los sonidos, las fuentes y las partes derivadas de KDE tienen sus propias licencias. Ver [LICENSE](LICENSE), [THIRD-PARTY.md](THIRD-PARTY.md) y [LICENSES/](LICENSES/).

La documentación se publica bajo **CC BY-SA 4.0**.

## Marca

SupraLINUX es el nombre del proyecto. No se usa el nombre ni el logo de Ubuntu para identificar el producto. “Basado en Ubuntu” es una referencia descriptiva.

Forks y derivados deben usar su propio nombre y logo, y no implicar respaldo de SupraLINUX, Canonical, Ubuntu o KDE.

## Agradecimientos

A KDE, Ubuntu, Calamares, Noto, Breeze y al resto de proyectos cuyas licencias y atribuciones se conservan en cada paquete.
