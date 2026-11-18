#!/bin/sh
# SupraLINUX Btrfs rollback helper. Runs from the live/recovery environment.
# It only replaces the root subvolume @; @home and @snapshots stay untouched.
set -eu

usage() {
    cat <<EOF
Uso: supralinux-recover [--device /dev/vda1] [--snapshot N] [--yes]

Sin --snapshot muestra las instantáneas disponibles. La raíz actual se conserva
como @pre-rollback-<fecha>; /home (@home) nunca se modifica.
EOF
}

device=
snapshot=
assume_yes=no
while [ $# -gt 0 ]; do
    case "$1" in
        --device) device=${2:?}; shift 2 ;;
        --snapshot) snapshot=${2:?}; shift 2 ;;
        --yes) assume_yes=yes; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Argumento desconocido: $1" >&2; usage; exit 2 ;;
    esac
done

[ "$(id -u)" -eq 0 ] || { echo "Ejecutar como root." >&2; exit 1; }

if [ -z "$device" ]; then
    devices=$(lsblk -rpno NAME,FSTYPE | awk '$2 == "btrfs" { print $1 }')
    count=$(printf '%s\n' "$devices" | sed '/^$/d' | wc -l)
    if [ "$count" -ne 1 ]; then
        echo "Selecciona el dispositivo Btrfs con --device (detectados: $count)." >&2
        printf '%s\n' "$devices" >&2
        exit 2
    fi
    device=$devices
fi

[ -b "$device" ] || { echo "No existe el dispositivo $device" >&2; exit 1; }
if findmnt -rn -S "$device" >/dev/null 2>&1; then
    echo "$device ya está montado; desmonta el sistema instalado antes." >&2
    exit 1
fi

mountpoint=/run/supralinux-recovery
btrfs=$mountpoint/btrfs
mkdir -p "$btrfs"
mount -o subvolid=5,rw "$device" "$btrfs"
cleanup() {
    sync
    umount "$btrfs" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

[ -d "$btrfs/@snapshots" ] || { echo "No existe @snapshots en $device" >&2; exit 1; }
[ -d "$btrfs/@" ] || { echo "No existe la raíz @ en $device" >&2; exit 1; }

if [ -z "$snapshot" ]; then
    echo "Instantáneas en $device:"
    printf '%-6s %s\n' "NUM" "RUTA"
    for dir in "$btrfs"/@snapshots/[0-9]*; do
        [ -d "$dir/snapshot" ] || continue
        printf '%-6s %s\n' "$(basename "$dir")" "$(basename "$dir")"
    done
    echo
    printf 'Número de instantánea a restaurar: '
    read -r snapshot
fi

case "$snapshot" in *[!0-9]*|'') echo "Número inválido." >&2; exit 2 ;; esac
source_snapshot=$btrfs/@snapshots/$snapshot/snapshot
[ -d "$source_snapshot" ] || { echo "No existe $source_snapshot" >&2; exit 1; }

echo "Se restaurará la instantánea $snapshot sobre @."
echo "La raíz actual quedará como @pre-rollback-<fecha>; @home no se toca."
if [ "$assume_yes" != yes ]; then
    printf '¿Continuar? [s/N] '
    read -r answer
    case "$answer" in s|S|si|sí|y|Y|yes) ;; *) echo "Cancelado."; exit 1 ;; esac
fi

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
new_root=$btrfs/@rollback-$timestamp
old_root=$btrfs/@pre-rollback-$timestamp

btrfs subvolume snapshot "$source_snapshot" "$new_root"
if ! mv "$btrfs/@" "$old_root"; then
    btrfs subvolume delete "$new_root" >/dev/null 2>&1 || true
    echo "No se pudo apartar la raíz actual; no se modificó nada." >&2
    exit 1
fi
if ! mv "$new_root" "$btrfs/@"; then
    mv "$old_root" "$btrfs/@" || true
    echo "No se pudo activar la instantánea; se restauró la raíz anterior." >&2
    exit 1
fi

sync

# Keep the three most recent pre-rollback roots.  The one just created is the
# newest; older copies are no longer useful and can fill the filesystem.
count=0
for dir in $(ls -1d "$btrfs"/@pre-rollback-* 2>/dev/null | sort -r); do
    count=$((count + 1))
    [ "$count" -le 3 ] && continue
    btrfs subvolume delete "$dir" >/dev/null 2>&1 || true
done

echo "Rollback completado. Raíz anterior: $old_root"
echo "/home permanece en @home sin cambios. Reinicia el sistema instalado."
