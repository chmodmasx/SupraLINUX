#!/bin/sh
# mmdebstrap --customize-hook: install Plasma 6.6.7 and configure the live image.
set -eu

root="$1"
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
workspace=$(dirname -- "$repo_root")
live=${SUPRALINUX_LIVE_DIR:-$workspace/live/1.0.0}
user=${SUPRALINUX_LIVE_USER:-supralinux}
host=${SUPRALINUX_LIVE_HOST:-supralinux}
export DEBIAN_FRONTEND=noninteractive
export DEBCONF_NONINTERACTIVE_SEEN=true

apt_run() {
    chroot "$root" env DEBIAN_FRONTEND=noninteractive \
        apt-get -y -o Dpkg::Options::=--force-confnew \
                -o Dpkg::Options::=--force-confdef "$@"
}

# The chroot shares the host resolver namespace during the build. If
# systemd-resolved was installed already, its stub target may not exist yet.
mkdir -p "$root/run/systemd/resolve"
if [ ! -s "$root/run/systemd/resolve/stub-resolv.conf" ]; then
    printf 'nameserver 127.0.0.53\noptions edns0 trust-ad\n' \
        > "$root/run/systemd/resolve/stub-resolv.conf"
fi

if [ -n "${SUPRALINUX_APT_BUILD_URL:-}" ]; then
    case "$SUPRALINUX_APT_BUILD_URL" in
        http://*|https://*) ;;
        *)
            echo "Invalid SUPRALINUX_APT_BUILD_URL: $SUPRALINUX_APT_BUILD_URL" >&2
            exit 1
            ;;
    esac
    sed "s|^URIs:.*|URIs: $SUPRALINUX_APT_BUILD_URL|" \
        "$root/usr/share/supralinux/apt/supralinux.sources" \
        > "$root/etc/apt/sources.list.d/supralinux.sources"
else
    install -m 0644 "$root/usr/share/supralinux/apt/supralinux.sources" \
            "$root/etc/apt/sources.list.d/supralinux.sources"
fi
install -m 0644 "$root/usr/share/supralinux/apt/mozilla.sources" \
        "$root/etc/apt/sources.list.d/mozilla.sources"
install -m 0644 "$root/usr/share/supralinux/apt/90-supralinux.pref" \
        "$root/etc/apt/preferences.d/90-supralinux.pref"
install -m 0644 "$root/usr/share/supralinux/apt/90-mozilla.pref" \
        "$root/etc/apt/preferences.d/90-mozilla.pref"

# mmdebstrap may start with main/universe only. Enable the Ubuntu components
# that supply firmware, drivers and optional codecs in the final image.
if [ -f "$root/etc/apt/sources.list" ]; then
    sed -i 's/ main universe$/ main universe restricted multiverse/' \
        "$root/etc/apt/sources.list"
fi

apt_run update

# casper is part of the live runtime and comes from the SupraLINUX snapshot
# so the noswap handling in casper-bottom/13swap ships in the package.
apt_run install --no-install-recommends casper

# Plasma 6.6.7, Frameworks 6.24 and Gear 25.12.3 come from the signed
# SupraLINUX repository. Firefox comes from the official Mozilla repository;
# Thunderbird is not packaged and remains available through Flathub.
# The rest of the runtime comes from the Ubuntu 26.04 archive.
desktop_list="$repo_root/packages/desktop/desktop-packages.list"
test -f "$desktop_list"
desktop_packages=$(sed -e 's/#.*//' -e '/^[[:space:]]*$/d' "$desktop_list")
# shellcheck disable=SC2086
apt_run install --no-install-recommends $desktop_packages

# The product app is injected as a local deb in test builds. Once it is
# published in the signed repository, this installs it in release builds.
if chroot "$root" apt-cache show supralinux-drivers >/dev/null 2>&1; then
    apt_run install --no-install-recommends supralinux-drivers
fi

# Test/incubation artifacts built outside the signed repository. The release
# build must publish these packages instead of injecting local .debs.
if [ -n "${SUPRALINUX_LOCAL_DEBS:-}" ]; then
    install -d -m 0755 "$root/tmp/supralinux-local-debs"
    local_deb_args=
    for deb in $SUPRALINUX_LOCAL_DEBS; do
        if [ ! -f "$deb" ]; then
            echo "Missing local deb: $deb" >&2
            exit 1
        fi
        install -m 0644 "$deb" "$root/tmp/supralinux-local-debs/"
        local_deb_args="$local_deb_args /tmp/supralinux-local-debs/$(basename "$deb")"
    done
    # apt compares the local files against the repository candidate. Since the
    # test packages are newer than the signed testing snapshot, apt labels the
    # replacement as a downgrade even though the local version is higher.
    # Release images must publish these versions in testing instead.
    # shellcheck disable=SC2086
    apt_run install --allow-downgrades $local_deb_args
    rm -rf "$root/tmp/supralinux-local-debs"
fi

# Install the resolver last: its postinst replaces /etc/resolv.conf with a
# symlink into /run, which is only populated after boot.
apt_run install --no-install-recommends systemd-resolved

# Materialize systemd-sysusers entries in the live rootfs.  Calamares adds the
# installer user to supplementary groups before the target's first boot, but
# some groups (notably gamemode) are only declared in /usr/lib/sysusers.d.
# Without this they do not exist yet and the users module's usermod fails.
chroot "$root" systemd-sysusers

# Keep the complete locale catalogue so Calamares can enable the locale the
# user selects, regardless of language. The live image generates en_US,
# es_ES and es_AR; the installer's post-localecfg check generates the chosen
# one.  es_AR is the product default so an offline install (GeoIP unavailable)
# does not fall back to es_US.
if [ -s "$root/usr/share/i18n/SUPPORTED" ]; then
    {
        printf '%s\n' '# Generated by SupraLINUX from /usr/share/i18n/SUPPORTED.'
        printf '%s\n' '# The live image enables en_US, es_ES and es_AR; Calamares enables the rest.'
        sed 's/^/# /' "$root/usr/share/i18n/SUPPORTED"
    } > "$root/etc/locale.gen"
    sed -i 's/^# en_US.UTF-8 UTF-8$/en_US.UTF-8 UTF-8/; s/^# es_ES.UTF-8 UTF-8$/es_ES.UTF-8 UTF-8/; s/^# es_AR.UTF-8 UTF-8$/es_AR.UTF-8 UTF-8/' \
        "$root/etc/locale.gen"
else
    cat > "$root/etc/locale.gen" <<'LOCALES'
en_US.UTF-8 UTF-8
es_ES.UTF-8 UTF-8
es_AR.UTF-8 UTF-8
LOCALES
fi
chroot "$root" locale-gen
printf 'LANG=es_AR.UTF-8\n' > "$root/etc/default/locale"
printf 'America/Argentina/Buenos_Aires\n' > "$root/etc/timezone"
ln -snf /usr/share/zoneinfo/America/Argentina/Buenos_Aires "$root/etc/localtime"

# Ubuntu's xdg-user-dirs package does not ship its gettext catalogs, so the
# XDG folder names would stay English. Install the upstream 0.19 catalogs so
# the user's selected language also names Escritorio/Documentos/Descargas.
if [ -d "$repo_root/branding/xdg-user-dirs/locale" ]; then
    install -d -m 0755 "$root/usr/share/locale"
    cp -a "$repo_root/branding/xdg-user-dirs/locale/." "$root/usr/share/locale/"
fi

# Ubuntu's network-manager package leaves every wired device unmanaged unless
# netplan provides a configuration. A desktop live image and installer need
# NetworkManager to own Ethernet; an empty unmanaged-devices list overrides
# the distro default and is inherited by the installed system.
rm -f "$root/usr/lib/NetworkManager/conf.d/10-globally-managed-devices.conf"
install -d -m 0755 "$root/etc/NetworkManager/conf.d"
cat > "$root/etc/NetworkManager/conf.d/10-managed-devices.conf" <<'NM'
[keyfile]
unmanaged-devices=
NM

# The QCA9565/AR9565 Bluetooth coexistence quirk is an optional package in
# testing; it is intentionally not preinstalled in the image.

# The published SupraLINUX and Mozilla sources stay configured for updates.
chroot "$root" apt-get clean

# A build-time repository URL is only for installing from a local staging
# mirror. The shipped sources must always point at the public endpoint.
if [ -n "${SUPRALINUX_APT_BUILD_URL:-}" ]; then
    install -m 0644 "$root/usr/share/supralinux/apt/supralinux.sources" \
            "$root/etc/apt/sources.list.d/supralinux.sources"
fi

# Calamares itself comes from Ubuntu; the settings, branding and launcher
# come from supralinux-calamares-config. Do not copy them from the repo here.
test -s "$root/etc/calamares/settings.conf"
test -s "$root/etc/calamares/branding/supralinux/branding.desc"
test -f "$root/usr/share/applications/kubuntu-calamares.desktop"

# Refuse to ship the known "pquetes" typo in any Spanish Calamares catalog.
for mo in "$root"/usr/share/locale/es*/LC_MESSAGES/calamares-python.mo; do
    [ -f "$mo" ] || continue
    if grep -aq 'pquetes' "$mo"; then
        echo "ERROR: Calamares Spanish catalog contains 'pquetes': $mo" >&2
        exit 1
    fi
done

# Branding and system defaults are installed from supralinux-branding and
# supralinux-defaults, not copied or patched here.
install -m 0755 "$repo_root/installer/recovery/supralinux-recover.sh" \
        "$root/usr/local/sbin/supralinux-recover"

# The graphical recovery application is live-only. It is installed from the
# signed repository in release builds, or injected as a local deb for testing.
if chroot "$root" apt-cache show supralinux-recovery-gui >/dev/null 2>&1; then
    apt_run install --no-install-recommends supralinux-recovery-gui
fi

if [ ! -f "$root/usr/share/applications/supralinux-recovery.desktop" ]; then
    if [ "${SUPRALINUX_REQUIRE_RECOVERY_GUI:-0}" = 1 ]; then
        echo "ERROR: supralinux-recovery-gui is required but was not installed." >&2
        exit 1
    fi
    echo "WARNING: supralinux-recovery-gui is not installed; live recovery GUI will be unavailable." >&2
fi

install -d -m 0755 "$root/etc/sddm.conf.d"
cat > "$root/etc/sddm.conf.d/10-supralinux.conf" <<SDDM
[Autologin]
User=$user
Session=plasma.desktop
Relogin=false

[General]
Numlock=on
SDDM

# Casper creates the live user from the initramfs. Provision the blank KWallet
# before SDDM autologins so the first Chrome run does not race the wallet
# creation dialog. Installed systems get the same wallet from the Calamares
# job; this unit is live-only.
install -m 0644 "$repo_root/tools/live/supralinux-kwallet-setup.service" \
        "$root/etc/systemd/system/supralinux-kwallet-setup.service"
install -d -m 0755 "$root/etc/systemd/system/multi-user.target.wants"
ln -sf ../supralinux-kwallet-setup.service \
       "$root/etc/systemd/system/multi-user.target.wants/supralinux-kwallet-setup.service"

cat > "$root/etc/casper.conf" <<CASPER
export USERNAME="$user"
export USERFULLNAME="SupraLINUX Live User"
export HOST="$host"
export BUILD_SYSTEM="Ubuntu"
CASPER

printf '%s\n' "$host" > "$root/etc/hostname"

# The default panel icon and the Folder View "Open Terminal" action are part
# of plasma-desktop-data's 0001-supralinux-desktop-defaults.patch, so they
# survive package updates instead of being edited in the rootfs.

if ! grep -q "^127\.0\.1\.1[[:space:]]*$host$" "$root/etc/hosts"; then
    printf '127.0.1.1\t%s\n' "$host" >> "$root/etc/hosts"
fi
install -d -m 0755 "$root/var/crash"

# Browser, MIME and Firefox policy files come from supralinux-defaults.
# Regenerate the Firefox override after the package is installed.
chroot "$root" /usr/lib/supralinux/fix-firefox-desktop

# The Kubuntu Calamares settings package leaves an OEM desktop entry and an
# automirror distribution name even though this product uses its own branding.
rm -f "$root/usr/share/applications/calamares-launch-oem.desktop"
rm -rf "$root/etc/calamares/branding/kubuntu"
if [ -f "$root/etc/calamares/modules/automirror.conf" ]; then
    sed -i 's/^distribution:.*/distribution: SupraLINUX/' \
        "$root/etc/calamares/modules/automirror.conf"
fi

chroot "$root" systemctl disable ufw >/dev/null 2>&1 || true
# Samba packages stay installed for file sharing, but the daemons must not be
# enabled by default. The user can enable smbd/nmbd explicitly when needed.
chroot "$root" systemctl disable smbd nmbd >/dev/null 2>&1 || true
chroot "$root" systemctl enable apparmor
chroot "$root" systemctl enable chrony
chroot "$root" systemctl enable sddm
chroot "$root" systemctl enable systemd-resolved
chroot "$root" systemctl enable NetworkManager
chroot "$root" systemctl set-default graphical.target

# Never let the live session auto-assemble an existing mdadm array.  The
# installer must not offer a RAID data array as an erase target.  The target
# gets its own mdadm.conf from shellprocess@raid and can assemble it after
# the first boot.
install -d -m 0755 "$root/etc/mdadm"
cat > "$root/etc/mdadm/mdadm.conf" <<'MDADM'
# SupraLINUX live: do not auto-assemble arrays in the installer session.
# The installed system receives a real configuration from Calamares.
AUTO -all
MDADM

# Casper runs these bottom scripts before init-bottom moves /dev into the
# live root and before systemd sets the hostname.  Set the kernel hostname
# early so hostname -f, make-ssl-cert and sudo can resolve "supralinux".
cat > "$root/usr/share/initramfs-tools/scripts/casper-bottom/19sethostname" <<'HOSTNAME'
#!/bin/sh
PREREQ=""
DESCRIPTION="Setting early hostname..."

prereqs()
{
    echo "$PREREQ"
}

case $1 in
prereqs)
    prereqs
    exit 0
    ;;
esac

. /scripts/casper-functions
load_confmodule

log_begin_msg "$DESCRIPTION"
printf '%s\n' "$HOST" > /proc/sys/kernel/hostname
log_end_msg
HOSTNAME
chmod 0755 "$root/usr/share/initramfs-tools/scripts/casper-bottom/19sethostname"

# Calamares must never offer mdadm member disks or an assembled array as an
# erase target.  UDisks/Solid honour UDISKS_IGNORE, which hides the devices
# from the partition page.  This rule is written into the live overlay only;
# the installed system gets the real mdadm configuration from
# shellprocess@raid.
cat > "$root/usr/share/initramfs-tools/scripts/casper-bottom/65hide-raid" <<'RAID'
#!/bin/sh
PREREQ=""
DESCRIPTION="Hiding RAID arrays from the installer..."

prereqs()
{
    echo "$PREREQ"
}

case $1 in
prereqs)
    prereqs
    exit 0
    ;;
esac

. /scripts/casper-functions

log_begin_msg "$DESCRIPTION"
# The initramfs mdadm hook may already have assembled data arrays.  Stop them
# for the live session and remove the udev rule that would assemble them again
# after switch_root.  The installed system keeps its own rule and mdadm.conf.
mdadm --stop --scan 2>/dev/null || true
rm -f /root/usr/lib/udev/rules.d/64-md-raid-assembly.rules
rm -f /root/lib/udev/rules.d/64-md-raid-assembly.rules
# casper-bottom runs before the full rootfs is available: coreutils'
# `install` is not present in the initramfs.  Use the shell builtin path.
mkdir -p /root/etc/udev/rules.d
cat > /root/etc/udev/rules.d/99-supralinux-raid-hide.rules <<'EOF'
SUBSYSTEM=="block", ENV{ID_FS_TYPE}=="linux_raid_member", ENV{UDISKS_IGNORE}="1"
SUBSYSTEM=="block", KERNEL=="md*", ENV{UDISKS_IGNORE}="1"
EOF
log_end_msg
RAID
chmod 0755 "$root/usr/share/initramfs-tools/scripts/casper-bottom/65hide-raid"

# Remove Ubuntu/GNOME-only casper hooks that assume packages this product
# does not ship (update-notifier, apport, gnome-initial-setup, Mozc).  They
# only add failed chroot calls and warnings to the live boot log.
for script in 31disable_update_notifier 33enable_apport_crashes \
              52gnome_initial_setup 59disable_mozc_autosetup; do
    rm -f "$root/usr/share/initramfs-tools/scripts/casper-bottom/$script"
done

# The Ubuntu casper hook builds an APT cache from a cdrom.sources repository.
# This ISO has no such repository, so the hook would run apt-get update against
# the network before NetworkManager is up.  Keep it for future CD repositories
# but skip it cleanly when the source is absent.
if [ -f "$root/usr/share/initramfs-tools/scripts/casper-bottom/41apt_build_cache_cdrom" ]; then
    sed -i '/^\. \/scripts\/casper-functions$/a [ -e /root/etc/apt/sources.list.d/cdrom.sources ] || { echo "SupraLINUX: no cdrom.sources, skipping APT cache build"; exit 0; }' \
        "$root/usr/share/initramfs-tools/scripts/casper-bottom/41apt_build_cache_cdrom"
fi

# Casper copies the installer launcher to the live user's Desktop. Put the
# recovery launcher next to it, using the same ownership and trust handling.
cat > "$root/usr/share/initramfs-tools/scripts/casper-bottom/27supralinux-recovery-icon" <<'RECOVERYICON'
#!/bin/sh
PREREQ=""
DESCRIPTION="Adding the SupraLINUX recovery desktop icon..."

prereqs()
{
    echo "$PREREQ"
}

case $1 in
prereqs)
    prereqs
    exit 0
    ;;
esac

. /scripts/casper-functions
load_confmodule

log_begin_msg "$DESCRIPTION"
src=/usr/share/applications/supralinux-recovery.desktop
if [ -f "/root$src" ] && [ -n "$USERNAME" ]; then
    chroot /root install -d -o "$USERNAME" -g "$USERNAME" "/home/$USERNAME/Desktop"
    chroot /root install -D -o "$USERNAME" -g "$USERNAME" "$src" \
        "/home/$USERNAME/Desktop/supralinux-recovery.desktop"
    if [ -x /root/usr/bin/dbus-run-session ] && [ -x /root/usr/bin/gio ]; then
        chroot /root sudo -i -u "$USERNAME" dbus-run-session -- \
            gio set "/home/$USERNAME/Desktop/supralinux-recovery.desktop" \
            metadata::trusted true >/dev/null 2>&1 || true
    fi
fi
log_end_msg
RECOVERYICON
chmod 0755 "$root/usr/share/initramfs-tools/scripts/casper-bottom/27supralinux-recovery-icon"

chroot "$root" update-initramfs -u -k all

chroot "$root" dpkg-query -W -f='${Package}\t${Version}\n' \
    sddm plasma-session-wayland plasma-desktop plasma-workspace \
    kwin-wayland systemsettings breeze kf6-breeze-icon-theme \
    apparmor chrony \
    qemu-guest-agent pipewire pipewire-pulse wireplumber \
    libspa-0.2-modules > "$root/var/lib/supralinux-live-packages.txt"
