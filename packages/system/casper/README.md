# casper 26.04.2-0supralinux2

Reconstrucción de `casper` 26.04.2 de Ubuntu con un único cambio:
`casper-bottom/13swap` sale sin activar swap si `/proc/cmdline` contiene
`noswap`.

- Fuente: `casper_26.04.2.tar.xz` de `archive.ubuntu.com`, fijada por SHA-256
  en `manifests/casper-26.04.2-clean-build.json`.
- Formato fuente: `3.0 (quilt)`, con
  `debian/patches/0001-honor-noswap.patch`.
- Build: `tools/clean_build.py --manifest
  manifests/casper-26.04.2-clean-build.json`, con sbuild/unshare en una VM
  desechable y sin NIC.
- La evidencia conserva `.dsc`, `.orig.tar.xz`, `.debian.tar.xz`, `.deb`,
  `.changes`, `.buildinfo`, logs y hashes en
  `evidence/clean-build/20261104T054323Z-39905994307a`.
- El build produce `casper` y `ubiquity-casper` desde la misma fuente.

Este directorio conserva el `debian/` revisado y el parche, no el árbol
upstream completo.
