#!/bin/sh
# mmdebstrap --setup-hook: stage keys, APT sources and the Flathub definition.
set -eu

root="$1"
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
channel=${SUPRALINUX_APT_CHANNEL:-testing}

case "$channel" in
    testing|stable) ;;
    *)
        echo "Unknown SUPRALINUX_APT_CHANNEL: $channel" >&2
        exit 1
        ;;
esac

archive_key="$repo_root/installer/keys/supralinux-archive-key.asc"
if [ ! -s "$archive_key" ]; then
    echo "Missing $archive_key" >&2
    echo "Generate the new Aptly key and place its public half there." >&2
    exit 1
fi

source_file="$repo_root/installer/apt/supralinux-${channel}.sources"
test -s "$source_file"

install -d -m 0755 "$root/usr/share/keyrings" \
                   "$root/usr/share/supralinux/apt" \
                   "$root/etc/flatpak/remotes.d"
install -m 0644 "$archive_key" \
        "$root/usr/share/keyrings/supralinux-archive-key.asc"
install -m 0644 "$repo_root/installer/keys/packages.mozilla.org.asc" \
        "$root/usr/share/keyrings/packages.mozilla.org.asc"
install -m 0644 "$source_file" \
        "$root/usr/share/supralinux/apt/supralinux.sources"
install -m 0644 "$repo_root/installer/apt/mozilla.sources" \
        "$root/usr/share/supralinux/apt/mozilla.sources"
install -m 0644 "$repo_root/installer/apt/90-supralinux.pref" \
        "$root/usr/share/supralinux/apt/90-supralinux.pref"
install -m 0644 "$repo_root/installer/apt/90-mozilla.pref" \
        "$root/usr/share/supralinux/apt/90-mozilla.pref"
install -m 0644 "$repo_root/installer/apt/flathub.flatpakrepo" \
        "$root/etc/flatpak/remotes.d/flathub.flatpakrepo"
