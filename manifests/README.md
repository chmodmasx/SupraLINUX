# Manifests

Un manifiesto fija los inputs y el resultado esperado de un build o de una
prueba. No reemplaza los artifacts: los referencia por SHA-256.

## Reglas

- Un manifiesto por paquete y versión.
- Las rutas de workspace son relativas a `SUPRALINUX_WORKSPACE` cuando el archivo
  vive dentro de él; si no, se usa una ruta absoluta.
- La ruta de `source.path` es relativa al repositorio.
- Cada input declara SHA-256, versión y arquitectura cuando corresponde.
- Un manifiesto no se publica si sus artifacts no están retenidos.
- No se versionan `.deb`, `.changes`, `.buildinfo`, ISOs ni discos.

## Inventario de fuentes

`manifests/packages-1.0.0.json` lo genera
`python3 tools/package_inventory.py`. Lista cada paquete fuente, versión, área,
binarios y licencias declaradas. No contiene hashes de build ni afirma que un
paquete haya sido construido.

```sh
python3 tools/package_inventory.py
python3 tools/package_inventory.py --check
```

## Resultados de build

`manifests/native-builds-1.0.0.json` resume los builds nativos ejecutados.
Cada entrada enlaza su manifiesto, artifact por SHA-256 y run de evidencia.
El estado es `partial`: no cubre Frameworks, Plasma, Gear ni la ISO.

## Build limpio

`manifests/<paquete>-<version>-clean-build.json`:

- `schema` y `scope`.
- `package`, `version`, `architecture`.
- `source`: tipo `native` o `quilt`, ruta, commit original, `.dsc`, upstream.
- `base_image`: imagen qcow2, SHA-256 y formato.
- `rootfs`: tarball, SHA-256, bytes y cantidad de paquetes instalados.
- `build_dependencies`: clausura resuelta, hashes y evidencia.
- `builder`: sbuild, distribución, arquitectura, RAM, vCPU, red y timeout.
- `expected_binaries` y `verification.expected_paths`.

## Smoke

`manifests/<paquete>-<version>-package-smoke.json`:

- `artifact` y `base_image` con SHA-256.
- `test` con ruta y SHA-256.
- `installed_files` con hashes.
- `negative_test` con la ruta que debe provocar el fallo controlado.
- `repository_artifacts` si la instalación necesita dependencias locales.

## Creación

Los manifiestos de build los generan las herramientas de importación:

```sh
python3 tools/import_framework.py --help
python3 tools/import_kde_source.py --help
```

El manifiesto se revisa y se commitea con la fuente y el packaging. El artifact
se conserva en `SUPRALINUX_WORKSPACE/artifacts/sha256/`.
