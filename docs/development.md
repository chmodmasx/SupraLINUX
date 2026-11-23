# Desarrollo

## Un solo flujo local

SupraLINUX se desarrolla con Git local. No hay remoto, CI, PR ni Actions en el
flujo ordinario. La publicación de una release es una operación explícita y
separada del desarrollo.

Ramas:

- `main`: releases estables. No recibe commits directos.
- `testing`: integración. Recibe features, fixes y pruebas.
- `feature/<tema>` y `fix/<tema>`: trabajo puntual, salen de `testing`.
- `hotfix/<tema>`: sale de `main`, se prueba y se integra a `main` y `testing`.

Los merges conservan el contexto con `--no-ff`. No se reescribe historia ya
integrada. Los commits son pequeños, coherentes y en español, con prefijo
`feat:`, `fix:`, `docs:`, `build:`, `test:`, `chore:` o `refactor:`.

El proyecto usa DCO: `git commit -s`. No se versionan artifacts, discos,
credenciales, capturas del host, logs ni `__pycache__`.

## Workspace

El repositorio y los almacenes de trabajo están separados:

```sh
SUPRALINUX_REPO=/mnt/RAID0/Proyectos/SupraLINUX
SUPRALINUX_WORKSPACE=/mnt/RAID0/Proyectos/SupraLINUX-workspace
SUPRALINUX_SECRETS=/mnt/RAID0/Proyectos/SupraLINUX-secrets
```

Sólo `SUPRALINUX_REPO` pertenece a Git. El workspace contiene:

```text
artifacts/sha256/<sha256>/     Fuentes, binarios y clausuras retenidas
evidence/<tipo>/<run>/         Resultados de build y pruebas
kvm/bases/<sha256>.qcow2       Imágenes base inmutables
kvm/runs/<run>/                Overlays y discos de una ejecución
live/<version>/                Rootfs, árbol de ISO y salida
cache/                         Descargas y cachés reconstruibles
```

`SUPRALINUX_SECRETS` queda fuera del workspace y del repositorio. Las rutas son
configurables; los scripts no deben fijar rutas de una máquina concreta.

El workspace anterior `/mnt/RAID0/SupraLINUX_OS` es una referencia de sólo
lectura. No se modifica, no se usa como destino de builds nuevos y no se copia
en bloque. Sólo se admiten artifacts concretos después de comprobar su hash,
procedencia, versión, arquitectura y dependencias. La historia y los manifests
anteriores no se consideran verdad vigente.

## Recorrido de un cambio

El recorrido mínimo es:

**inputs fijados → fuente verificada → packaging → build limpio → pruebas →
artifact retenido → repositorio `testing` → ISO o actualización en VM
desechable → evidencia → release.**

Un cambio no está probado por aplicarlo a mano en un sistema instalado. Tiene
que pasar por el paquete, el repositorio y una imagen o instalación nueva. El
sistema instalado sólo se usa para diagnóstico de lectura.

Empezar por un componente pequeño para certificar el circuito antes de compilar
todo el escritorio. El repositorio APT y la prueba de instalación se incorporan
temprano, no al final.

## Herramientas del host

El host necesita, como mínimo:

| Grupo | Herramientas |
|---|---|
| Virtualización | `qemu-system-x86_64`, `qemu-img`, `ovmf`, `/dev/kvm` |
| Rootfs live | `mmdebstrap`, `apt`, `dpkg` |
| ISO | `mksquashfs`, `xorriso`, `mtools`, `dosfstools` |
| Firma | `gpg`, `gpgv` |
| Empaquetado | `dpkg-source`, `dpkg-deb`, `dpkg-scanpackages`, `dpkg-query` |
| Validación | `python3`, `imagemagick`, `fonts-dejavu-core` |
| Traducciones | `msgfmt` |
| Red | `curl`, `ssh`, `rsync`, `xz-utils`, `zstd`, `ca-certificates` |

`sbuild`, `debhelper`, `devscripts` y las herramientas de compilación viven
dentro de la imagen base de build, no en el host. `grub-mkrescue`, `grub-pc-bin`,
`grub-efi-amd64-bin`, `grub-efi-amd64-signed` y `shim-signed` tampoco se
necesitan en el host: el payload de arranque sale del rootfs.

`sh tools/check-host.sh` sólo informa de comandos ausentes y de `/dev/kvm`.
No instala ni configura nada. Instalar herramientas del host requiere permiso
específico.

## Aislamiento y checkpoints KVM

- Cada ejecución escribe en su propio overlay qcow2. Las bases y checkpoints
  admitidos son inmutables para sus consumidores.
- No se arranca un padre en escritura mientras tenga consumidores. No se mueven
  backing files ni se opera sobre discos en uso.
- La VM de build y las pruebas usan cero NIC o SLIRP. No se usan bridges, TAP
  ni redes de libvirt del host.
- Se prefiere apagado limpio. Los snapshots de RAM no son el mecanismo ordinario.
- Antes de descartar un overlay se exportan artifacts, resultados y logs a
  `artifacts/` y `evidence/`.
- Al cerrar una ejecución se elimina su overlay y se comprueba que el padre no
  cambió. No se dejan VMs ni discos efímeros sin cleanup comprobado.
- Los snapshots no son backups: dependen de sus padres y pueden compartir el
  mismo fallo de almacenamiento.

Una ejecución a la vez por circuito. No se levantan más VMs suponiendo que
eso acelera el trabajo; se presupuestan CPU, RAM, espacio y crecimiento real de
los overlays.

## User namespaces

`mmdebstrap` y los hooks live usan `unshare` con mapeo subuid. El flujo del
proyecto lo ejecuta con `sudo`:

```sh
sudo env SUPRALINUX_LIVE_DIR="$LIVE" \
  unshare --map-users=0:100000:65536 --map-groups=0:100000:65536 \
  --setuid=0 --setgid=0 ...
```

Así el namespace lo crea root y el uid 0 interior queda mapeado a 100000 en el
host. Es el “mapped root” que espera `build-iso.sh`: el rootfs de 100000 se ve
como `0:0` dentro y los archivos nuevos siguen siendo de 100000, no de root.

Si se ejecuta `unshare` como usuario común en un host con
`kernel.apparmor_restrict_unprivileged_userns=1`, el perfil
`unprivileged_userns` deniega `setgroups` y falla con
`setgroups() failed: Operation not permitted`. Eso no afecta al flujo con
`sudo`.

`mmdebstrap --mode=unshare` ejecutado directamente también funciona sin `sudo`
porque tiene su propio perfil AppArmor, pero el wrapper de la ISO usa el
`unshare` externo y necesita `sudo`.

No hace falta cambiar la política del host para el flujo con `sudo`. Si se
quisiera usar `unshare` sin privilegios, las opciones siguen siendo:

- ejecutar el build live en una VM desechable con user namespaces permitidos;
- usar un host de build preparado para `unshare` y mapeo subuid;
- si se autoriza, ajustar la política del host y registrar el cambio.

`sudo` limpia el entorno: pasar `SUPRALINUX_LIVE_DIR` y las demás variables
necesarias con `env`.

El build limpio de paquetes (`tools/clean_build.py`) no usa `unshare` en el
host: arranca QEMU y ejecuta `sbuild` dentro del guest.

## Build limpio

`sbuild`/`unshare` sobre un rootfs retenido. El rootfs no lleva preinstalados
los SDKs que el paquete declara: eso ocultaría `Build-Depends`. Las
dependencias se resuelven desde el archivo de Ubuntu y el repositorio local,
con versiones y hashes retenidos.

Reglas:

- Árbol Git limpio antes de construir.
- Fuente verificada por SHA-256; `debian/` revisado.
- `SOURCE_DATE_EPOCH` y opciones deterministas cuando aplique.
- Sin red durante el build; fuentes APT limitadas al repositorio local firmado.
- `dh_missing --fail-missing`.
- `lintian` en paquetes propios.
- `autopkgtest` en paquetes clave.
- `reprotest` en paquetes clave, no en todo el stack a la vez.

Cada build deja fuente, binario, `.changes`, `.buildinfo`, logs, hashes y
resultado. Un fallo de sbuild se registra como `FAIL` con causa `BUILD_FAIL`; un
fallo de preparación, transporte o cleanup es `INFRA_INVALID`. Un fallo de
infraestructura no es un fallo del paquete ni se convierte en PASS.

## Paquetes y repositorio

- El packaging parte de Ubuntu 26.04 cuando existe y de upstream cuando no.
- Cada importación conserva `debian/`, `debian/patches/` y `debian/copyright`,
  y retira metadatos internos que no correspondan.
- Los parches son mínimos, documentados y con motivo.
- No se parchea Calamares: su configuración va en un paquete separado.
- No se introducen parches de seguridad propios; se siguen los de Ubuntu/KDE.
- Los paquetes modificados publican su fuente en `deb-src`.

El repositorio `testing` se usa para QA. `stable` sólo apunta a una release
validada. La publicación se firma y se verifica antes de cambiarla.

## Imagen live

1. `mmdebstrap` bajo `sudo unshare` construye el rootfs desde Ubuntu y el
   repositorio `testing`.
2. Los hooks versionados instalan el escritorio, el branding y la configuración.
3. Se copian kernel e initramfs, se sella el rootfs y se crea el squashfs con
   `mksquashfs` determinista.
4. `xorriso` compone la ISO híbrida BIOS/UEFI con shim y GRUB firmados por
   Ubuntu. No se usa `grub-mkrescue` ni `/boot/grub` del host.
5. La ISO se prueba en BIOS, UEFI y UEFI Secure Boot antes de publicarla.

El rootfs conserva los directorios vacíos `/dev`, `/proc`, `/sys`, `/run`,
`/tmp` y `/var/tmp`; casper los monta al arrancar. No se usa `-all-root` en
`mksquashfs`: cambia los grupos y rompe helpers de D-Bus.

## Reglas del sistema instalado

Ninguna distribución instalada se modifica. Ni la del host ni la de otra
computadora. Las distros instaladas son fuentes de diagnóstico de sólo lectura:
`journalctl`, `dpkg-query`, `systemctl status/show`, `ls`, `cat`.

No se instalan, actualizan ni quitan paquetes, ni se edita `/etc`, `/usr` o
`/var`, ni se cambian servicios, PAM, permisos, locale, Snapper, systemd,
arranque, red o cualquier otro estado. Tampoco se reinician servicios o el
equipo para aplicar cambios. Tener `sudo` no es autorización.

Los cambios se construyen y validan en el repositorio y en una ISO, rootfs o VM
desechable. Si una prueba exigiera modificar una distro instalada, se detiene y
se pide autorización explícita para esa acción puntual. La respuesta por
defecto es no.

## Reutilización de trabajo anterior

Antes de reutilizar código, packaging o evidencia:

1. Revisar función, inputs y alcance.
2. Comprobar que no depende de una versión, ruta o decisión muerta.
3. Verificar hashes y procedencia.
4. Registrar el commit original y los cambios en `docs/reuse.md`.
5. Crear un commit nuevo; no se replica la historia vieja.

No se copian `AGENTS.md`, manifests internos, rutas personales, credenciales ni
capturas. Los datos personales se normalizan. Un artifact heredado no certifica
un build nuevo ni una release.

## Checklist de cambio

- [ ] Rama correcta y commits pequeños.
- [ ] `python3 -m unittest discover -s tests -v`.
- [ ] Build limpio del paquete afectado.
- [ ] Smoke offline si cambia instalación o runtime.
- [ ] ISO o VM si cambia escritorio, instalador, arranque o recuperación.
- [ ] Documentación y `debian/changelog` actualizados.
- [ ] Sin artifacts, secretos ni rutas internas en Git.
- [ ] Evidencia ligada al commit y a los hashes de inputs.
