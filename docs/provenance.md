# Procedencia

## Objetivo

Cada paquete, parche y artifact de SupraLINUX debe poder rastrearse hasta su
fuente, su packaging, sus licencias y el build que lo produjo. La procedencia
no es un resumen: es el conjunto de inputs y hashes que permiten reconstruir y
auditar la release.

## Categorías de inputs

| Categoría | Origen | Verificación |
|---|---|---|
| Base | Ubuntu 26.04 LTS | Paquete, versión, archivo y clave de Ubuntu |
| KDE | Tarballs oficiales de Frameworks, Plasma y Gear | SHA-256 publicado por KDE |
| Packaging | Ubuntu/Debian de la misma rama, o propio | Revisión de `debian/`, parches y copyright |
| Qt y plataforma | Ubuntu 26.04 | No se reconstruye |
| Firefox | Repositorio oficial de Mozilla | Clave y `InRelease` de Mozilla |
| Flatpak | Flathub | Configuración del remoto; no se empaqueta |
| Fuentes | Google Noto u otra fuente upstream | SHA-256 y licencia OFL |
| Arte y sonidos | Producción propia o upstream compatible | Licencia por archivo |

No se usa un binario sin fuente identificable. No se usa un artifact heredado
sin hash, versión, arquitectura y dependencias comprobadas.

## Manifiesto de build

Cada build deja un manifiesto JSON con, como mínimo:

```json
{
  "package": "kwin",
  "version": "6.6.7-0supralinux1",
  "source": {
    "url": "https://download.kde.org/stable/plasma/6.6.7/kwin-6.6.7.tar.xz",
    "sha256": "..."
  },
  "packaging": {
    "origin": "ubuntu-26.04",
    "commit": "...",
    "patches": ["..."],
    "copyright": "debian/copyright"
  },
  "build": {
    "image": "sha256:...",
    "distribution": "resolute",
    "architecture": "amd64",
    "build_depends_sha256": "...",
    "command": "sbuild ...",
    "source_date_epoch": 0,
    "network": false
  },
  "artifacts": [
    {"name": "kwin_6.6.7-0supralinux1_amd64.deb", "sha256": "..."}
  ],
  "result": "PASS"
}
```

El manifiesto se guarda en `manifests/` y los artifacts en el workspace. Un
manifiesto sin artifacts retenidos no certifica una release.

## Importación

1. Fijar la versión upstream y el SHA-256.
2. Partir del packaging Ubuntu 26.04 de la misma rama cuando exista.
3. Conservar `debian/`, `debian/patches/`, `debian/copyright` y los avisos de
   terceros.
4. Retirar metadatos internos de la distro de origen que no correspondan:
   Salsa, CI, VCS, rutas personales y credenciales.
5. Revisar cada parche: conservar el necesario, retirar el obsoleto y
   documentar el motivo.
6. Verificar que construye contra el Qt y las bibliotecas de la base.
7. Registrar fuente, versión, hashes y dependencias.
8. Crear un commit nuevo; no se replica la historia de origen.

Las importaciones del proyecto anterior se registran en
[reuse.md](reuse.md). Ese registro indica el commit original, el alcance y los
cambios aplicados.

## Parches

- Mínimos y con una razón concreta.
- Documentados en `debian/patches/series` y, si cambian comportamiento, en este
  documento.
- Preferir upstream o el packaging Ubuntu antes que un parche propio.
- No se parchea Calamares: su configuración va en un paquete separado.
- No se mantiene una línea propia de parches de seguridad.
- Un parche que sólo existe para ocultar una dependencia o un ABI se rechaza.

## Licencias

| Área | Licencia |
|---|---|
| Código y configuración propios | GPL-2.0-or-later |
| `supralinux-drivers` | GPL-3.0-or-later |
| Arte y wallpapers | CC-BY-4.0 |
| Sonidos | CC0-1.0 |
| Partes derivadas de KDE/Breeze | LGPL-2.1-or-later |
| Fuentes | OFL-1.1 |
| Documentación | CC BY-SA 4.0 |
| Terceros y vendor | La de cada `debian/copyright` |

`debian/copyright` usa DEP-5 y cubre código, assets, fuentes, traducciones y
vendor. `THIRD-PARTY.md` es un índice; la referencia principal es el copyright
del paquete. Los avisos de copyright y las licencias de terceros se conservan.

## Fuentes publicadas

- Los paquetes modificados publican su fuente en `deb-src`.
- Se conservan `.dsc`, `.debian.tar.*` y `.orig.tar.*` de la release.
- Los tarballs originales se conservan con su SHA-256.
- No se publica una fuente sin la licencia y el copyright correspondientes.
- Los binarios de terceros no se relicencian ni se presentan como propios.

## Reproducibilidad

- `SOURCE_DATE_EPOCH` en los paquetes que lo admiten.
- `mksquashfs` con `-all-time 0`, `-xattrs` y opciones deterministas.
- Sin red durante el build.
- Clausura de dependencias retenida por hash.
- `reprotest` en paquetes clave, no en todo el stack a la vez.
- Las diferencias conocidas se documentan; no se declara reproducible lo que no
  se comprobó.

## Auditoría

Antes de una release:

- `debian/copyright` completo en cada paquete.
- `lintian` sin errores en paquetes propios.
- Fuente y binario con hashes.
- Vendor y módulos de Go con licencias.
- Assets con licencia y atribución.
- Sin marcas o logos de terceros usados como identidad del producto.
- Sin datos personales, rutas internas ni credenciales en el árbol.

## Retención

La fuente, el binario, `.changes`, `.buildinfo`, logs y manifiesto se conservan
al menos mientras la release esté publicada. La evidencia de una release
retirada también se conserva: explica qué se publicó y por qué se retiró.
