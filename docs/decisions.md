# Decisiones

Registro de decisiones de arquitectura y producto. Cada decisión indica el
motivo y la consecuencia; si se revisa, se agrega una entrada nueva en lugar de
reescribir la anterior.

## D-001 — Repositorio e historia nuevos

**Decisión:** crear un repositorio nuevo con historia curada de aproximadamente
35–40 commits. El proyecto anterior queda como referencia de sólo lectura.

**Motivo:** la historia anterior mezcla 498 commits, campañas, pasos muertos y
manifests internos. No es una base legible para una release nueva.

**Consecuencia:** no se replica la historia ni se copia en bloque. Cada
importación se revisa y se registra en [reuse.md](reuse.md). `main` contiene
sólo releases; `testing`, la integración.

## D-002 — Base Ubuntu 26.04 y KDE desde upstream

**Decisión:** usar Ubuntu 26.04 LTS como base y construir KDE Frameworks,
Plasma y Gear desde fuentes upstream contra el Qt de Ubuntu.

**Motivo:** Ubuntu mantiene kernel, firmware, drivers, Qt y bibliotecas de
plataforma. KDE define el escritorio. La cadencia de Kubuntu no selecciona la
versión.

**Consecuencia:** no se reconstruye Qt, el kernel ni los drivers de plataforma.
No se mantiene un fork de KDE. Una versión de KDE que exija un Qt superior al
de la base queda fuera de la campaña.

## D-003 — Identidad separada de la base

**Decisión:** `ID=supralinux`, `ID_LIKE="ubuntu debian"`, `VERSION_ID=26.04`,
`VERSION_CODENAME=resolute`, `UBUNTU_CODENAME=resolute`,
`VERSION="1.0.0 (Aurora)"`, `PRETTY_NAME="SupraLINUX Aurora 1.0.0"` y
`SUPRALINUX_VERSION`/`SUPRALINUX_CODENAME` para el producto.

**Motivo:** APT y las herramientas de la base esperan `VERSION_ID=26.04` y el
codename de Ubuntu. A la vez, el usuario necesita ver la versión del producto.

**Consecuencia:** no se cambia `VERSION_ID` para mostrar 1.0.0. Las herramientas
que detectan la base leen `VERSION_ID`/`UBUNTU_CODENAME`; las que muestran el
producto leen `PRETTY_NAME`/`VERSION`/`SUPRALINUX_*`.

## D-004 — `supralinux-base-files` con `dpkg-divert`

**Decisión:** la identidad la posee un paquete propio, `supralinux-base-files`,
con `dpkg-divert` sobre los archivos de `base-files`.

**Motivo:** se necesita controlar `os-release`, `lsb-release`, `issue` y
`legal` sin reemplazar ni romper `base-files` de Ubuntu.

**Consecuencia:** el paquete se instala y se actualiza de forma independiente.
Los archivos de identidad no se copian a mano en el rootfs ni en el instalador.

## D-005 — Stack KDE fijado por release

**Decisión:** 1.0.0 usa Frameworks 6.24, Plasma 6.6.7, Gear 25.12.3 y Qt
6.10.2. No se mezclan versiones dentro de la misma release.

**Motivo:** las dependencias entre Frameworks, Plasma y Gear son estrictas; una
mezcla produce fallos de ABI y de runtime.

**Consecuencia:** cada campaña fija fuentes, versiones, parches y claves. Una
nueva release upstream no cambia la release en curso.

## D-006 — Calamares configurado, no parcheado

**Decisión:** la configuración de Calamares se empaqueta como
`supralinux-calamares-config` e instala `/etc/calamares`. No se instala
`calamares-settings-kubuntu` ni se parchea Calamares.

**Motivo:** separar configuración de binario; evitar depender de los settings de
Kubuntu y facilitar la actualización de Calamares.

**Consecuencia:** el paquete declara la dependencia de `calamares` y prueba la
instalación en BIOS, UEFI y Secure Boot. Los módulos propios se versionan y se
documentan.

## D-007 — Secure Boot con la cadena de Ubuntu

**Decisión:** usar shim, GRUB y kernel firmados por Canonical; no mantener una
cadena Secure Boot propia en 1.0.0.

**Motivo:** una cadena propia exige custodia de claves, revisión de seguridad,
enrolamiento y, potencialmente, revisión de Microsoft. No es el costo correcto
para la primera release.

**Consecuencia:** la ISO y el sistema instalado arrancan con Secure Boot en
firmware que confía en Canonical. Los módulos propios requieren MOK. Ver
[secure-boot.md](secure-boot.md).

## D-008 — Btrfs, Snapper y recuperación desde el live

**Decisión:** Btrfs por defecto, con `@`, `@home` y `@snapshots`; Snapper en la
raíz; rollback desde el live con `supralinux-recover` y una GUI Kirigami
propia, live-only.

**Motivo:** permitir volver a un estado anterior sin revertir los datos
personales y sin depender de una entrada de recuperación en el sistema
instalado. Una terminal cruda no es una experiencia aceptable para un usuario
común.

**Consecuencia:** `@home` no se toca en el rollback. La raíz anterior se
conserva como `@pre-rollback-<fecha>` y se retienen las tres más recientes. EXT4
sigue disponible, pero sin rollback. La GUI no se instala en el target; el
sistema instalado no conserva entrada de recuperación ni backend. La
recuperación guiada cubre Btrfs sin cifrar; LUKS2 no tiene rollback automático
en 1.0.0.

## D-009 — Firefox desde el repositorio oficial de Mozilla

**Decisión:** preinstalar Firefox y los paquetes de idioma español desde el
repositorio oficial de Mozilla. No mantener un mirror propio ni un cron de
sincronización.

**Motivo:** evitar un mirror y un servicio propios; Mozilla mantiene el
repositorio y las firmas.

**Consecuencia:** la ISO y el sistema instalado configuran la fuente y la clave
de Mozilla. Los paquetes `firefox-l10n-es-ar`, `firefox-l10n-es-es` y
`firefox-l10n-es-mx` se instalan; el inglés queda incorporado. No se usa el
paquete transicional de Ubuntu ni snap.

El `.deb` de Mozilla en `/usr/lib/firefox` no coincide con el patrón del perfil
AppArmor de Ubuntu 26.04. Se instala un perfil exacto
`/etc/apparmor.d/firefox-supralinux` con `userns,` para que el sandbox de
Firefox conserve los user namespaces con
`kernel.apparmor_restrict_unprivileged_userns=1`.

## D-010 — Sin snapd en 1.0.0

**Decisión:** la release no incluye `snapd`. Usa APT, el repositorio propio y
Flatpak/Flathub.

**Motivo:** reducir capas y servicios; el escritorio y las apps necesarias se
empaquetan o se instalan por Flatpak.

**Consecuencia:** las instrucciones que asumen snap no aplican. Firefox se
instala desde Mozilla; Thunderbird, si se necesita, se ofrece por Flathub. Los
usuarios pueden agregar snap por su cuenta, pero no es parte del producto.

## D-011 — Aptly nuevo, clave Ed25519 nueva

**Decisión:** crear una instancia y un volumen nuevos de Aptly, con una clave
Ed25519 nueva. Verificar la publicación antes de cambiar el repositorio en uso.
La instancia, el volumen y las claves anteriores se consideran descartables y
sólo se eliminan después de la validación y con autorización explícita.

**Motivo:** separar la infraestructura nueva de la anterior y no arrastrar una
clave o un estado de publicación que ya no representan al proyecto.

**Consecuencia:** `testing` y `stable` se publican con la clave nueva. La clave
privada vive fuera de Git. No se reutiliza la clave anterior para 1.0.0.

## D-012 — Nombres de packaging

**Decisión:** `packages/complete` pasa a `packages/gear-extras` y
`desktop-complete.list` pasa a `desktop-packages.list`.

**Motivo:** los nombres describen el contenido y el perfil de escritorio, no una
campaña anterior.

**Consecuencia:** las referencias, manifests y scripts usan los nombres nuevos.
No se mantienen enlaces de compatibilidad con los nombres viejos.

## D-013 — fastfetch sin parche de `os-release`

**Decisión:** no se parchea fastfetch para su heurística de variantes Ubuntu. Se
usa su comportamiento estándar sobre la identidad de SupraLINUX.

**Motivo:** la identidad correcta vive en `os-release`; un parche propio de una
herramienta cosmética agrega mantenimiento sin valor de producto.

**Consecuencia:** la salida de fastfetch puede mostrar un logo o una variante
genérica. Es cosmético y no afecta la identidad del sistema.

## D-014 — Keyring/Secret Service por usuario

**Decisión:** KWallet/Secret Service se activa por usuario, no con un servicio
system-wide.

**Motivo:** el bus de sesión y la cartera pertenecen al usuario; un servicio
global produce condiciones de carrera y diálogos fuera de la sesión.

**Consecuencia:** la cartera está disponible desde el primer inicio. No se
instala `evolution-data-server` para no desplazar `org.freedesktop.secrets` con
`gnome-keyring`. La sincronización PBAP de contactos por Bluetooth queda como
limitación conocida. Los plugins `pbap` e `irmc` de `obexd` se deshabilitan
con `-P pbap,irmc`; ambos inicializan el backend de contactos de Evolution y
`irmc` es el que intenta activar EDS antes de la exclusión. OBEX/FTP/MAP siguen
disponibles.

## D-015 — zram sólo en equipos pequeños

**Decisión:** `systemd-zram-generator` se configura en equipos de hasta 8 GB de
RAM, con `zram-size = min(ram / 2, 4096)` y `lz4`. No se usa zswap. El swap de
disco elegido en el instalador sigue disponible.

**Motivo:** evitar doble compresión y mejorar la respuesta en equipos con poca
memoria sin imponer zram en equipos grandes.

**Consecuencia:** los equipos grandes usan swap de disco o ningún swap según la
elección. La hibernación sólo se ofrece con partición `suspend`; no se promete
reanudación real.

## D-016 — Git local, sin CI ni remoto

**Decisión:** el desarrollo es local. No hay remoto, CI, PR, Actions ni JIT. La
publicación es una operación explícita.

**Motivo:** el proyecto es personal y no quiere depender de una plataforma. La
historia y los tags se controlan localmente.

**Consecuencia:** las pruebas se ejecutan a mano y se registran. No se crean
opciones de compatibilidad para CI. Un remoto sólo se configura con
autorización.

## D-017 — Sitio web sin build

**Decisión:** el sitio público es HTML/CSS/JS plano, sin Astro, Node ni paso de
build. Se desarrolla directamente sobre el servidor. El backend privado de
bugs es Flask y los datos quedan fuera del web root.

**Motivo:** reducir dependencias y mantener el sitio simple, rápido y fácil de
auditar.

**Consecuencia:** no hay `node_modules`, lockfiles ni pipeline de frontend. El
sitio se sirve con nginx; el formulario de bugs no envía notificaciones ni
correo. Los datos personales se normalizan y no se publican.

## D-018 — Alcance recortado de 1.0.0

**Decisión:** no se incluyen openQA, SBOM/CRA, `CODE_OF_CONDUCT`, `MAINTAINERS`,
un archivo de marca separado, una publicación de validación completa ni
`reprotest` de todo el stack.

**Motivo:** mantener el foco en una release construible y validable, sin
infraestructura que no aporte al producto.

**Consecuencia:** la validación se publica como manifiestos y evidencia
resumida. `reprotest` se aplica a paquetes clave. La marca se describe en el
README. El soporte es best-effort.

## D-019 — Aislamiento del host

**Decisión:** ninguna distribución instalada se modifica. Los builds y pruebas
se hacen en ISO, rootfs o VM desechable, con cero NIC o SLIRP.

**Motivo:** el host es una herramienta de desarrollo, no un banco de pruebas.
Modificarlo oculta errores de packaging y arriesga el entorno.

**Consecuencia:** no se usan bridges, TAP ni redes de libvirt del host. Las
bases/checkpoints KVM son inmutables para sus consumidores. Una excepción exige
autorización explícita y puntual.

## D-020 — Documentación y licencias

**Decisión:** documentación principal en español, con índice en inglés. Código
y configuración propios bajo GPL-2.0-or-later; drivers GPL-3.0-or-later; arte
CC-BY-4.0; sonidos CC0-1.0; KDE/Breeze LGPL-2.1-or-later; fuentes OFL-1.1;
documentación CC BY-SA 4.0; terceros según `debian/copyright`.

**Motivo:** una licencia clara por área y una documentación usable por el
usuario hispanohablante, sin perder el índice en inglés.

**Consecuencia:** `LICENSE` resume; `LICENSES/` contiene los textos; cada
paquete declara su licencia en `debian/copyright`.

## D-021 — ISO híbrida con payload del rootfs

**Decisión:** construir una ISO híbrida BIOS/UEFI con `xorriso` y el payload de
GRUB/shim del rootfs. No usar `grub-mkrescue` ni el GRUB del host.

**Motivo:** controlar el contenido firmado y evitar que el host introduzca
binarios o módulos distintos.

**Consecuencia:** el build depende de `grub-pc-bin`, `grub-efi-amd64-bin`,
`grub-efi-amd64-signed` y `shim-signed` dentro del rootfs. Los binarios
firmados no se modifican.

## D-022 — URLs públicas

**Decisión:** la URL pública del sitio es `supralinux.com` y la del
repositorio APT es `repo.supralinux.com`. Los canales se separan por suite:
`testing` y `stable`, no por subdominio.

**Motivo:** un solo host de repositorio simplifica DNS, TLS y la configuración
de APT; la suite sigue separando QA de release.

**Consecuencia:** `supralinux-testing.sources` y `supralinux-stable.sources`
usan `https://repo.supralinux.com/` con `Suites: testing` o `Suites: stable`.
La infraestructura interna no se publica.

## D-023 — Sin promesa de fin de soporte

**Decisión:** no se publica `SUPPORT_END`. El soporte es best-effort.

**Motivo:** el proyecto es personal y no puede comprometer una fecha de fin de
soporte que dependa de Ubuntu, KDE y del tiempo disponible.

**Consecuencia:** la documentación informa que las actualizaciones de seguridad
siguen el ciclo de Ubuntu 26.04 mientras el proyecto se mantenga, sin SLA ni
fecha garantizada.

## D-024 — Logo de os-release resuelto en el tema

**Decisión:** `LOGO=distributor-logo` en `os-release`. Ese nombre lo instala
`supralinux-branding` y su contenido es idéntico al logo `supralinux-color`.

**Motivo:** `LOGO=supralinux` no tenía un icono instalado y KDE mostraba una
imagen rota en “Acerca de este sistema”.

**Consecuencia:** el test `test_os_release_logo_resolves_to_a_branded_icon`
falla si el nombre de `LOGO` no existe en el tema. No se duplica el archivo.

## D-025 — WiFi live: límite de plasma-nm en la primera conexión

**Decisión:** no se aplica un parche local a `plasma-nm` en 1.0.0. Se documenta
el límite y el workaround; la corrección corresponde aguas arriba.

**Motivo:** en una red sin perfil guardado, el ítem del applet conserva el
`AccessPoint` del escaneo. `NetworkModel::wirelessNetworkReferenceApChanged()`
sólo actualiza `specificPath` cuando existe una conexión guardada. Si el AP de
referencia cambia mientras el diálogo de contraseña está abierto, NM responde
`specific_object_not_found` (“The access point ... was not in the scan list”).
En un sistema instalado el perfil ya existe y el camino se refresca; en live
no. La pila de usuarios (NetworkManager, wpa_supplicant, firmware, regdb y
configuración) coincide con Kubuntu 26.04.

**Consecuencia:** en live, conectar con `nmcli device wifi connect "<SSID>"
--ask` o `nmtui`. Calamares conserva el perfil del live en el sistema instalado
con `networkcfg`. Se reevalúa si upstream publica la corrección.

## D-026 — Ark: visor con estado propio y multivolumen sin falso ENOSPC

**Decisión:** se mantienen dos parches locales en `ark`:

- `ArkViewer` abre en 800×600 cuando no hay tamaño guardado —pasando la
  geometría del `.ui` a `setupGUI(size(), ToolBar)`— y usa
  `setStateConfigGroup("Viewer")` para guardar su tamaño y posición en un
  grupo propio de `arkstaterc`.
- Los chequeos de espacio previos a la extracción se omiten cuando el
  archivo es multivolumen; el backend sigue reportando un ENOSPC real.

**Motivo:** `setupGUI(ToolBar)` llamaba `adjustSize()` con la ventana vacía
y el visor abría en su tamaño mínimo (~224×148), sin recordar el tamaño
entre sesiones de Ark. Además, el listado de un RAR multivolumen repite
cada entrada una vez por volumen e infla el tamaño estimado (4 entradas de
3 MiB para un archivo de 3 MiB), bloqueando extracciones que sí caben.

**Consecuencia:** el fix de tamaño es el backport del MR upstream !360 (KDE
bug 503213, Ark 26.12); el de multivolumen sigue local. Se revisan al
actualizar Ark. El visor abre en 800×600 por defecto, conserva el tamaño
elegido entre sesiones y la extracción real sigue fallando si de verdad
falta espacio. Probado en VM desechable con un RAR de 4 volúmenes y un
tmpfs de 5 MiB, y con apertura, resize, cierre y reapertura del visor.

## D-027 — URLs limpias y formulario de bugs privado

**Decisión:** el sitio sirve URLs sin `.html` (`/bugs`, `/download`, `/docs`)
y redirige con 301 las direcciones viejas. `BUG_REPORT_URL` y el MOTD usan
`https://supralinux.com/bugs`. El formulario mantiene el endpoint
`POST /api/bugs` y no tiene usuarios, login ni panel de lectura. Los reportes
se leen por SSH desde `/data`.

**Motivo:** las URLs con `.html` son innecesarias para el usuario y el
formulario no necesita cuentas. Un panel de administración público ampliaría
la superficie de ataque sin aportar nada al flujo de diagnóstico.

**Consecuencia:** nginx del sitio implementa `try_files $uri $uri.html` y los
301; NPM sigue siendo sólo el proxy TLS. El rate limit usa `X-Real-IP` puesto
por el proxy y no confía en `X-Forwarded-For` del cliente. Se agregaron
`security.txt`, COOP/CORP, `Cache-Control: no-store` en `/api/bugs` y
normalización de hostname/UUID/IPv6. No se parchea DrKonqi: el botón existente
abre el formulario y el usuario pega el informe si lo necesita.

## D-028 — Gwenview: rueda para ampliar por defecto

**Decisión:** `supralinux-defaults` instala `/etc/xdg/gwenviewrc` con
`[ImageView] MouseWheelBehavior=2` (Ampliar). No se parchea Gwenview.

**Motivo:** el default upstream es Desplazamiento. La configuración de sistema
es suficiente y mantiene la posibilidad de que cada usuario elija otra cosa
desde Preferencias; una preferencia explícita en `~/.config/gwenviewrc` gana
sobre `/etc/xdg`.

**Consecuencia:** probado en VM desechable: sin configuración de usuario la
rueda cambia el zoom de 33% a 94% y vuelve a 33%; Preferencias muestra
“Ampliar”; al elegir “Desplazamiento” el zoom queda en 33% y la preferencia
persiste. Evidencia en `evidence/live/gwenview-default-20261120/`.

## D-029 — GUI de recuperación propia, live-only

**Decisión:** crear `supralinux-recovery-gui`, una app Qt 6/QML/Kirigami,
GPL-2.0-or-later, que lista instantáneas, pide confirmación, muestra progreso y
restaura desde el live. No crea, borra ni compara instantáneas. Usa `pkexec` y
una política polkit para llamar a `supralinux-recover`; no corre como root.

**Motivo:** la recuperación es una promesa central del producto y una TUI no es
aceptable para un usuario común. Las GUIs existentes (qSnapper, Btrfs
Assistant, snapper-gui, Timeshift) administran el sistema en ejecución o usan
otro store; no son un drop-in para restaurar un `@` desmontado desde el live.

**Consecuencia:** la GUI y el helper se instalan sólo en el live y Calamares los
elimina del target. No se agrega `grub-btrfs` ni una entrada de recuperación al
GRUB instalado. La entrada Recovery del live arranca gráfica y autolanza la
GUI. La app se prueba en VM desechable con un disco Btrfs y snapshots.

## D-030 — Dual-boot de 1.0.0 limitado a Linux

**Decisión:** validar dual-boot con otra instalación Linux, en el mismo disco y
en dos discos. No declarar Windows validado en 1.0.0.

**Motivo:** el flujo de Windows necesita una ISO, BitLocker y pruebas de
firmware que no forman parte del alcance actual. `os-prober` ya detecta otras
raíces Linux y el instalador conserva las entradas ajenas de la ESP.

**Consecuencia:** la matriz L4-DUAL y la web hablan de dual-boot Linux. Windows
queda como trabajo futuro; no se promete en la home ni en la FAQ.

## D-031 — Snapper se mantiene; Timeshift no se migra

**Decisión:** conservar Snapper, el layout `@`/`@home`/`@snapshots` y el hook
APT. Timeshift no se instala ni se usa como store paralelo.

**Motivo:** Snapper ya está configurado, validado en hardware y conectado al
backend de recuperación. Migrar a Timeshift implicaría otro store, otro hook y
repetir la matriz de recuperación.

**Consecuencia:** Timeshift sirve sólo como referencia de UX. La GUI propia
llama al backend existente.

## D-032 — LUKS2 sin rollback automático en 1.0.0

**Decisión:** la recuperación guiada desde el live cubre Btrfs sin cifrar. Una
instalación LUKS2 no tiene rollback automático en 1.0.0.

**Motivo:** el live necesitaría desbloquear LUKS2, montar el Btrfs interno y
pedir la contraseña de forma segura; además, `/boot` es una partición ext4
separada y no forma parte del snapshot de `@`.

**Consecuencia:** la GUI debe mostrar un estado claro para LUKS2. La
recuperación de LUKS2 queda para una versión futura; no se promete en la web.

## D-033 — Acción administrativa de Dolphin también en el home

**Decisión:** `kio-admin` lee `ShowInHome` desde `kio-adminrc` (default `true`)
y `supralinux-defaults` instala `/etc/xdg/kio-adminrc` con `true`. La acción
“Abrir como administrador” aparece en todas las ubicaciones locales, incluido
el home. Un usuario puede poner `false` en `~/.config/kio-adminrc` para
recuperar el comportamiento original de KDE.

**Motivo:** el plugin upstream oculta la acción cuando todo lo seleccionado está
bajo `$HOME`. SupraLINUX quiere la misma acción en cualquier carpeta local, sin
parchear Dolphin ni agregar helpers.

**Consecuencia:** con `true` la acción aparece en el home; con `false`
desaparece allí y sigue apareciendo fuera. Probado en live desechable, sin red:
evidencia en `evidence/qa/kio-admin-home-20261122/`. Abrir el home como root
puede dejar archivos con dueño root; la opción existe para desactivarlo.

## D-034 — AppArmor permite el bind mount de os-prober en Btrfs @

**Decisión:** `supralinux-defaults` instala un override local en
`/etc/apparmor.d/local/linux-boot-prober` que permite a `linux-boot-prober`
hacer `mount --bind` sobre `/var/lib/os-prober/mount/`. El perfil sigue en modo
`enforce`; solo se amplía el montaje sobre el punto temporal de os-prober. El
`postinst` invalida la caché del perfil y lo recarga antes de `update-grub`.

**Motivo:** el perfil de `apparmor 5.0.2-0ubuntu1~26.04.1` permite
`mount options=(rw, nosuid, nodev)` pero no `rw,bind`. `os-prober 1.84ubuntu1`
usa `mount --bind` para exponer una raíz Btrfs en `@`. La sonda propia
`91supralinux` detecta esas raíces, pero `linux-boot-prober` no puede generar
la entrada y `update-grub` termina con el bloque `30_os-prober` vacío.

**Consecuencia:** las instalaciones nuevas y las existentes conservan la
entrada de otras instalaciones SupraLINUX con Btrfs `@` después de
`update-grub`. La regla no permite montajes sobre `/`, `/etc` ni rutas fuera de
`/var/lib/os-prober/mount/`. Ubuntu/Kubuntu tienen el mismo perfil, pero su
sonda estándar no detecta raíces en `@`; el bug se reporta upstream.

## D-035 — Atenuar el asset del login claro, no el QML

**Decisión:** el fondo del tema SDDM `supralinux-light` se genera desde el
wallpaper Light con el mismo tratamiento de atenuación que el tema oscuro
(`-evaluate multiply 0.71`). No se agrega un overlay en `Background.qml`.

**Motivo:** el fondo claro era una copia cruda del wallpaper (brillo medio
42.490) mientras el oscuro ya estaba atenuado (12.742 frente a 17.973 del
wallpaper oscuro). El lock screen se ve equilibrado por su propio atenuado.
Un overlay QML solo para el tema claro duplicaría el mecanismo y se alejaría
del QML upstream de Breeze.

**Consecuencia:** el asset se versiona en `supralinux-theme`; el QML queda igual
al upstream. La comparación antes/después está en
`evidence/qa/sddm-light-1.1.4-20261123/`; la validación final se hace en VM/ISO.

## D-036 — Soporte de PPA con template de python-apt

**Decisión:** `supralinux-defaults` instala
`/usr/share/python-apt/templates/supralinux.info` con `Suite: resolute` y
declara `python-apt-common` en `Depends`. No se cambia `ID=ubuntu`.

**Motivo:** `add-apt-repository` usa `aptsources.distro`, que busca un template
`<ID>.info`; sin `supralinux.info`, toda operación falla con
`NoDistroTemplateException`. Es el mecanismo estándar de las derivadas;
`ID_LIKE` y `UBUNTU_CODENAME` no se usan en ese lookup.

**Consecuencia:** los PPAs se agregan con `Suites: resolute`. Un test compara el
`Suite` con `VERSION_CODENAME` y otro valida `get_sources()` con el parser real.
`-c`/`-p` aplicados a un PPA modifican la entrada de ese PPA, no
`supralinux.sources`: por ejemplo, `-c universe` agrega `Components: universe`
y `-p updates` usa `Suites: resolute-updates`. El único caso no soportado es
usarlos solos para cambiar todos los repositorios del sistema, porque ahí
`add-apt-repository` escribe en `supralinux.sources`, el repo del producto.
Los PPAs que no publican `resolute` no funcionan, igual que en Ubuntu 26.04.

## D-037 — KDE Connect aplica el toggle de plugins por D-Bus

**Decisión:** el paquete `kdeconnect` incluye el parche
`0006-plugin-settings-apply-immediately.patch`, que llama a
`Device::setPluginEnabled()` cuando la app cambia el estado de un plugin.

**Motivo:** `PluginModel::setData()` sólo escribía el archivo por dispositivo;
`kdeconnectd` mantiene el mapa de plugins en memoria y no lo recarga hasta
reconectar o reiniciar. Destildar “Recibir notificaciones” no tenía efecto
inmediato.

**Consecuencia:** el cambio se aplica al instante. Se prueba en VM con un
teléfono pareado y se verifica `loadedPlugins`; el parche queda
`Forwarded: not-yet` hasta que upstream lo acepte.

## D-038 — IDs canónicos y árbol Breeze en los temas de iconos

**Decisión:** los temas se llaman `SupraLINUX-Dark` y `SupraLINUX-Light`, con
nombres visibles `SupraLINUX Oscuro` y `SupraLINUX Claro`. `index.theme` toma
la metadata completa de Breeze/Breeze Dark y cada tema materializa un symlink
por entrada de su tema base. No se agregan aliases para los IDs anteriores.

**Motivo:** la herencia por sí sola no cubre aplicaciones que buscan nombres
concretos y no recorren el tema heredado, como Kdenlive. Los IDs anteriores
tenían además capitalización inconsistente entre el paquete y las referencias
de LNF/GTK.

**Consecuencia:** LNF, GTK 3/4 y los defaults del paquete apuntan a los IDs
nuevos. `tests/test_theme.py` verifica IDs, nombres, metadata y que cada
symlink resuelva a la misma ruta relativa en Breeze.
