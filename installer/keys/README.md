# Claves

- `packages.mozilla.org.asc` es la clave pública del repositorio oficial de
  Mozilla. Se conserva en el repositorio y se instala en
  `/usr/share/keyrings/packages.mozilla.org.asc`.
- `supralinux-archive-key.asc` es la clave pública del repositorio APT de
  SupraLINUX. Se genera con la instancia nueva de Aptly y se publica con la
  release. La clave privada vive en `SUPRALINUX_SECRETS` y nunca se versiona.
- La clave anterior del repositorio no se reutiliza.

El build de la ISO se detiene si falta `supralinux-archive-key.asc`; no se
sustituye por una clave vieja.
