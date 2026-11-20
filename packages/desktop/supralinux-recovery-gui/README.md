# supralinux-recovery-gui

Aplicación gráfica mínima para restaurar una instantánea de Snapper desde el
entorno live de SupraLINUX.

## Alcance

- Solo se instala en la imagen live.
- Calamares elimina el paquete del sistema instalado.
- No crea, borra ni compara instantáneas: solo restaura una existente.
- No reimplementa Btrfs: llama a `supralinux-recover`.
- No corre como root: usa `pkexec` y la política
  `com.supralinux.recovery.run`.
- En el live, una regla de polkit permite al usuario `supralinux` ejecutar el
  helper sin contraseña.

## Backend

El binario usa:

```sh
/usr/libexec/supralinux-recovery-helper --list-tsv --device /dev/...
/usr/libexec/supralinux-recovery-helper --device /dev/... --snapshot N --yes --progress=json
```

El helper ejecuta `/usr/local/sbin/supralinux-recover`, que se instala desde
`installer/recovery/supralinux-recover.sh` durante el build del live.

## Build

```sh
dpkg-buildpackage -b -us -uc
```

Dependencias de build: `debhelper-compat`, `cmake`, `qt6-base-dev` y
`qt6-declarative-dev`.

## Prueba local

El binario acepta `--demo` para mostrar datos falsos sin tocar el sistema:

```sh
SUPRALINUX_RECOVERY_QML="$PWD/qml" ./supralinux-recovery-gui --demo
```

La variable `SUPRALINUX_RECOVERY_DEV_HELPER` permite usar un helper de prueba
sin `pkexec`; no se usa en la imagen live.
