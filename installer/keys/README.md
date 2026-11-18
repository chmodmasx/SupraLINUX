# Claves

- `packages.mozilla.org.asc` es la clave pública del repositorio oficial de
  Mozilla. Se conserva en el repositorio y se instala en
  `/usr/share/keyrings/packages.mozilla.org.asc`.
- `supralinux-archive-key.asc` es la clave pública Ed25519 del repositorio APT
  de SupraLINUX. Huella:

  ```text
  9BAD7A4B1826213B3BE271E208780B9EEC43C2B8
  ```

  La clave privada y su passphrase viven en `SUPRALINUX_SECRETS` y nunca se
  versionan. La clave anterior del repositorio no se reutiliza.

El build de la ISO se detiene si falta `supralinux-archive-key.asc`; no se
sustituye por una clave vieja.
