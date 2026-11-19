# Build limpio

## Alcance

`tools/clean_build.py` reconstruye un paquete fijado en un manifiesto dentro de
una VM KVM desechable, sin red y con `sbuild` en modo `unshare`.

El circuito es:

1. Verificar el árbol Git limpio y los inputs del manifiesto.
2. Crear el paquete fuente con `dpkg-source`.
3. Restaurar la imagen base, el rootfs y la clausura de `Build-Depends` por
   SHA-256.
4. Crear un repositorio APT local firmado con una clave efímera.
5. Preparar un disco de entrada ext4 de sólo lectura.
6. Arrancar una VM sin NIC, montar el disco y extraer el rootfs.
7. Ejecutar `sbuild` con las dependencias resueltas desde el repositorio local.
8. Verificar binarios, `.changes`, `.buildinfo` y el payload esperado.
9. Retener artifacts, logs, hashes y el resultado.

El build limpio no certifica una ISO ni una release. Certifica un paquete.

## Entradas

Un manifiesto `manifests/<paquete>-<version>-clean-build.json` fija:

- Paquete, versión y arquitectura.
- Fuente `native` o `quilt`, ruta, commit original y `.dsc`.
- Tarball upstream, URL y SHA-256 cuando es `quilt`.
- Imagen base qcow2 y SHA-256.
- Rootfs buildd, SHA-256, tamaño y cantidad de paquetes instalados.
- Clausura de `Build-Depends` con nombre, versión, arquitectura y SHA-256.
- Versión de `sbuild`, distribución, arquitectura, RAM, vCPU, red y timeout.
- Binarios esperados y rutas de verificación.

Las rutas de workspace son relativas a `SUPRALINUX_WORKSPACE` cuando el archivo
vive dentro de él. `source.path` es relativa al repositorio.

## Ejecución

```sh
export SUPRALINUX_WORKSPACE=/mnt/RAID0/Proyectos/SupraLINUX-workspace
python3 tools/clean_build.py --manifest manifests/<paquete>-<version>-clean-build.json
```

Requisitos:

- Usuario sin privilegios con acceso real a `/dev/kvm`.
- `qemu-system-x86_64`, `qemu-img`, `dpkg-source`, `dpkg-deb`,
  `dpkg-scanpackages`, `gnupg`, `e2fsprogs`, `sbuild` en la imagen base.
- RAM disponible para el guest más 1536 MiB de margen.
- 20 GiB libres en el workspace.
- `kvm/runs/` vacío; una ejecución a la vez.

El host no instala paquetes ni configura red. La VM usa cero NIC y el disco de
entrada se monta `ro`.

## Rootfs y dependencias

El rootfs buildd no debe contener `debhelper`, `fakeroot` ni los SDKs que el
paquete declara. Las dependencias se resuelven desde el repositorio local
firmado; las fuentes APT del chroot se reducen a ese repositorio.

`tools/resolve_build_deps.py` resuelve una cláusula `Build-Depends` contra el
archivo de Ubuntu y, si se indica, un archivo de preferencias. Retiene cada
`.deb` con su hash y escribe `resolved.json`.

## Evidencia

```text
evidence/clean-build/<run>/
  result.json
  source/
  repository/
  build/
  sbuild.log
  guest-run.log
  apt-update.log
  apt-simulation.log
  guest-result.json
  qemu-command.json
  console.log
  hashes.txt
```

Un fallo de `sbuild` se registra como `FAIL` con causa `BUILD_FAIL`. Un fallo de
preparación, transporte o cleanup es `INFRA_INVALID`. Un `PASS` exige binario,
payload y metadatos coincidentes con el manifiesto.

## Retención

Fuente, binario, `.changes`, `.buildinfo`, logs y hashes se conservan en el
workspace. Los artifacts se direccionan por SHA-256 en
`artifacts/sha256/<sha256>/`. El repositorio no guarda binarios ni logs.

## Lote completo

`tools/build_release.py` recorre `manifests/release-1.0.0/` en orden, ejecuta un
`clean_build.py` por paquete y guarda el estado fuera de Git para poder
reanudar. Un `FAIL` de paquete no detiene el lote; los `INFRA_INVALID`
consecutivos sí.

```sh
python3 tools/build_release.py
```

El estado queda en `SUPRALINUX_WORKSPACE/state/full-build-1.0.0.json` y los
logs en `evidence/full-build/`.

## Estado en el repo nuevo

Los 176 paquetes fuente de 1.0.0 tienen build limpio `PASS`, con artifact,
`.changes`, `.buildinfo`, evidencia y cleanup comprobado. El resumen está en
`manifests/full-build-results-1.0.0.json`. El build de paquetes no certifica la
ISO, la instalación ni la recuperación.
