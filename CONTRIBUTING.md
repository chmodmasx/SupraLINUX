# Contribuir a SupraLINUX

SupraLINUX es un proyecto personal que se desarrolla en local. No se asume una
plataforma de CI, un proveedor de Git ni un flujo de pull requests.

## Ramas

- `main`: releases estables. No recibe commits directos.
- `testing`: integración. Recibe features, fixes y pruebas.
- `feature/<tema>` y `fix/<tema>`: trabajo puntual, salen de `testing`.

Una release se integra a `main` desde `testing` o desde un `hotfix` probado.
`main` puede recibir merges de ramas probadas y tags, no trabajo directo.

## Commits

- Mensajes en español, con prefijo: `feat:`, `fix:`, `docs:`, `build:`,
  `test:`, `chore:`, `refactor:`.
- Un commit por unidad coherente. No mezclar áreas distintas.
- No incluir artefactos, discos, capturas del host, credenciales ni logs.
- Firmar los commits con DCO: `git commit -s`.

## Pruebas

- Unitarias: `make check` cuando el repo tenga las herramientas.
- Build limpio: `sbuild`/`unshare` en un rootfs retenido.
- Instalación y escritorio: ISO o VM desechable.
- Nunca se modifica una distribución instalada. Es solo diagnóstico de lectura.
- Las pruebas de una release se hacen sobre la ISO, no sobre el host.

## Packaging

- Debian Policy y `debhelper` como base.
- Parches documentados en `debian/patches/series`.
- `debian/copyright` DEP-5 completo, incluyendo assets y vendor.
- Versiones `0supralinuxN`; changelog claro.
- No se ocultan Build-Depends preinstalando SDKs en el rootfs.
- No se commitean `.deb`, `.changes`, `.buildinfo`, `.dsc`, ISOs, `.qcow2`,
  logs ni `__pycache__`.

## Documentación

- Español principal; `README.en.md` y `docs/README.en.md` para inglés.
- Los cambios de comportamiento se documentan en el mismo commit o en el
  commit de docs que corresponda.
- Las decisiones de arquitectura se registran en `docs/decisions.md`.

## Seguridad

No abras issues públicos para vulnerabilidades. Ver [SECURITY.md](SECURITY.md).

## Licencia y DCO

Al contribuir aceptás que tu aporte se distribuya bajo la licencia del área
correspondiente (ver [LICENSE](LICENSE)) y certificás el DCO con
`git commit -s`.
