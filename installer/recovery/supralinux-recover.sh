#!/bin/sh
# SupraLINUX Btrfs rollback helper. Runs from the live/recovery environment.
# It only replaces the root subvolume @; @home and @snapshots stay untouched.
#
# Machine-readable modes:
#   --list-tsv          NUM<TAB>DATE<TAB>DESCRIPTION<TAB>TYPE
#   --progress=json     one JSON object per line on stdout
#
# Human-readable messages go to stderr when a machine-readable mode is active.
set -eu

usage() {
    cat <<EOF
Uso: supralinux-recover [--device /dev/vda1] [--snapshot N] [--yes]
                        [--list-tsv] [--progress=json]

Sin --snapshot muestra las instantáneas disponibles. La raíz actual se conserva
como @pre-rollback-<fecha>; /home (@home) nunca se modifica.

--list-tsv      Lista las instantáneas en formato TSV y termina.
--progress=json Emite el progreso como líneas JSON en stdout.
EOF
}

device=
snapshot=
assume_yes=no
list_tsv=no
progress_json=no

while [ $# -gt 0 ]; do
    case "$1" in
        --device) device=${2:?}; shift 2 ;;
        --snapshot) snapshot=${2:?}; shift 2 ;;
        --yes) assume_yes=yes; shift ;;
        --list-tsv) list_tsv=yes; shift ;;
        --progress=json) progress_json=yes; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Argumento desconocido: $1" >&2; usage; exit 2 ;;
    esac
done

json_escape() {
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n\r\t' '   '
}

say() {
    if [ "$progress_json" = yes ]; then
        echo "$*" >&2
    else
        echo "$*"
    fi
}

emit_json() {
    [ "$progress_json" = yes ] || return 0
    printf '%s\n' "$1"
}

emit_step() {
    emit_json "{\"event\":\"step\",\"step\":\"$1\",\"status\":\"$2\"}"
}

fail() {
    code=$1
    shift
    message=$*
    if [ "$progress_json" = yes ]; then
        emit_json "{\"event\":\"error\",\"code\":\"$code\",\"message\":\"$(json_escape "$message")\"}"
    fi
    echo "$message" >&2
    exit "$code"
}

xml_value() {
    # Extract the first occurrence of a simple XML element from info.xml.
    sed -n "s:.*<$1>\\(.*\\)</$1>.*:\\1:p" "$2" 2>/dev/null | head -n 1
}

xml_unescape() {
    printf '%s' "$1" |
        sed -e 's/&amp;/\&/g' \
            -e 's/&lt;/</g' \
            -e 's/&gt;/>/g' \
            -e 's/&quot;/"/g' \
            -e "s/&apos;/'/g"
}

tsv_clean() {
    # Tabs and newlines would break the TSV contract.
    printf '%s' "$1" | tr '\t\n\r' '   '
}

[ "$(id -u)" -eq 0 ] || fail 3 "Ejecutar como root."

if [ -z "$device" ]; then
    devices=$(lsblk -rpno NAME,FSTYPE | awk '$2 == "btrfs" { print $1 }')
    count=$(printf '%s\n' "$devices" | sed '/^$/d' | wc -l)
    if [ "$count" -ne 1 ]; then
        fail 4 "Selecciona el dispositivo Btrfs con --device (detectados: $count)."
    fi
    device=$(printf '%s\n' "$devices" | sed -n '1p')
fi

[ -b "$device" ] || fail 5 "No existe el dispositivo $device"
fs_type=$(blkid -o value -s TYPE "$device" 2>/dev/null || true)
[ "$fs_type" = btrfs ] || fail 5 "$device no es un sistema de archivos Btrfs."

if findmnt -rn -S "$device" >/dev/null 2>&1; then
    fail 6 "$device ya está montado; desmonta el sistema instalado antes."
fi

mountpoint=$(mktemp -d /run/supralinux-recovery.XXXXXX)
btrfs=$mountpoint/btrfs
mkdir -p "$btrfs"

cleanup() {
    sync
    umount "$btrfs" 2>/dev/null || true
    rmdir "$btrfs" 2>/dev/null || true
    rmdir "$mountpoint" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

mount -o subvolid=5,rw "$device" "$btrfs" ||
    fail 7 "No se pudo montar $device."

[ -d "$btrfs/@snapshots" ] || fail 8 "No existe @snapshots en $device"
[ -d "$btrfs/@" ] || fail 8 "No existe la raíz @ en $device"

list_snapshots_tsv() {
    for num in $(find "$btrfs/@snapshots" -mindepth 1 -maxdepth 1 \
                     -type d -name '[0-9]*' -printf '%f\n' 2>/dev/null | sort -n); do
        info=$btrfs/@snapshots/$num/info.xml
        [ -f "$info" ] || continue
        date=$(xml_value date "$info")
        description=$(xml_unescape "$(xml_value description "$info")")
        type=$(xml_value type "$info")
        [ -n "$date" ] || date=-
        [ -n "$description" ] || description=-
        [ -n "$type" ] || type=-
        printf '%s\t%s\t%s\t%s\n' \
            "$(tsv_clean "$num")" "$(tsv_clean "$date")" \
            "$(tsv_clean "$description")" "$(tsv_clean "$type")"
    done
}

if [ "$list_tsv" = yes ]; then
    list_snapshots_tsv
    exit 0
fi

if [ -z "$snapshot" ]; then
    say "Instantáneas en $device:"
    printf '%-6s %-19s %s\n' "NUM" "FECHA" "DESCRIPCIÓN"
    list_snapshots_tsv | while IFS="$(printf '\t')" read -r num date description type; do
        printf '%-6s %-19s %s\n' "$num" "$date" "$description"
    done
    echo
    printf 'Número de instantánea a restaurar: '
    read -r snapshot
fi

case "$snapshot" in
    *[!0-9]*|'') fail 9 "Número de instantánea inválido: $snapshot" ;;
esac

source_snapshot=$btrfs/@snapshots/$snapshot/snapshot
[ -d "$source_snapshot" ] || fail 10 "No existe la instantánea $snapshot en $device."

say "Se restaurará la instantánea $snapshot sobre @."
say "La raíz actual quedará como @pre-rollback-<fecha>; @home no se toca."
if [ "$assume_yes" != yes ]; then
    printf '¿Continuar? [s/N] '
    read -r answer
    case "$answer" in
        s|S|si|sí|y|Y|yes) ;;
        *) say "Cancelado."; exit 1 ;;
    esac
fi

emit_json "{\"event\":\"start\",\"device\":\"$(json_escape "$device")\",\"snapshot\":$snapshot}"
emit_step verify running

# Re-check the essential paths after the confirmation prompt.
[ -d "$btrfs/@" ] || fail 8 "No existe la raíz @ en $device"
[ -d "$btrfs/@snapshots" ] || fail 8 "No existe @snapshots en $device"
[ -d "$source_snapshot" ] || fail 10 "No existe la instantánea $snapshot en $device."

emit_step verify ok
emit_step backup running

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
new_root=$btrfs/@rollback-$timestamp
old_root=$btrfs/@pre-rollback-$timestamp
if [ -e "$new_root" ] || [ -e "$old_root" ]; then
    timestamp=${timestamp}-$$
    new_root=$btrfs/@rollback-$timestamp
    old_root=$btrfs/@pre-rollback-$timestamp
fi

btrfs subvolume snapshot "$source_snapshot" "$new_root" >&2 ||
    fail 11 "No se pudo crear la instantánea de trabajo."
emit_step backup ok
emit_step restore running

if ! mv "$btrfs/@" "$old_root"; then
    btrfs subvolume delete "$new_root" >/dev/null 2>&1 || true
    fail 12 "No se pudo apartar la raíz actual; no se modificó nada."
fi
if ! mv "$new_root" "$btrfs/@"; then
    mv "$old_root" "$btrfs/@" || true
    fail 13 "No se pudo activar la instantánea; se restauró la raíz anterior."
fi

sync

# Keep the three most recent pre-rollback roots. The one just created is the
# newest; older copies are no longer useful and can fill the filesystem.
count=0
for dir in $(ls -1d "$btrfs"/@pre-rollback-* 2>/dev/null | sort -r); do
    count=$((count + 1))
    [ "$count" -le 3 ] && continue
    btrfs subvolume delete "$dir" >/dev/null 2>&1 || true
done

emit_step restore ok
emit_step cleanup running
emit_step cleanup ok
emit_json "{\"event\":\"done\",\"status\":\"ok\",\"previous_root\":\"$(json_escape "$old_root")\"}"

say "Rollback completado. Raíz anterior: $old_root"
say "/home permanece en @home sin cambios. Reinicia el sistema instalado."
