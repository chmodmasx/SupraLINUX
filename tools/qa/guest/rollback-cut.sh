#!/bin/sh
# QA only. The helper remains unmodified; wrappers pause at operation boundaries.
set -eu
. /etc/os-release
test "$ID" = supralinux
test -d /cdrom/casper
dev=/dev/disk/by-id/virtio-SUPRAQA-CUT
test -b "$dev"
test "$(readlink -f "$dev")" = /dev/vda
test "$(lsblk -dn -o SERIAL "$dev" | tr -d ' ')" = SUPRAQA-CUT
test "$(lsblk -bdn -o SIZE "$dev")" = 4294967296
test "$(lsblk -rn -o NAME "$dev" | wc -l)" -eq 1
test "$(lsblk -dn -o NAME,TYPE | awk '$2 == "disk" && $1 !~ /^zram[0-9]+$/ {print $1}')" = vda
if findmnt -rn -S /dev/vda >/dev/null; then exit 1; fi

case "${1:-}" in
prepare)
    test -z "$(lsblk -dn -o FSTYPE "$dev")"
    mkfs.btrfs -q "$dev"
    top=$(mktemp -d /run/supra-cut-fixture.XXXXXX)
    trap 'umount "$top" 2>/dev/null || true; rmdir "$top" 2>/dev/null || true' EXIT
    mount -o subvolid=5 "$dev" "$top"
    btrfs subvolume create "$top/@"
    btrfs subvolume create "$top/@home"
    btrfs subvolume create "$top/@snapshots"
    printf 'original\n' > "$top/@/root-marker"
    printf 'unchanged\n' > "$top/@home/home-marker"
    mkdir "$top/@snapshots/1"
    btrfs subvolume snapshot -r "$top/@" "$top/@snapshots/1/snapshot"
    printf '<snapshot><type>single</type><date>2026-11-26</date><description>QA cut fixture</description></snapshot>\n' > "$top/@snapshots/1/info.xml"
    printf 'changed\n' > "$top/@/root-marker"
    btrfs filesystem sync "$top"
    umount "$top"
    ;;
run)
    phase=${2:?}
    case "$phase" in before-exchange|after-exchange|before-backup-rename|after-backup-rename) ;; *) exit 2;; esac
    test "$(blkid -o value -s TYPE "$dev")" = btrfs
    work=/run/supra-qa-cut
    mkdir -m 0700 "$work"
    # /run may be mounted noexec; use a fresh executable QA directory.
    bindir=$(mktemp -d /tmp/supra-qa-cut-bin.XXXXXX)
    chmod 0700 "$bindir"
    export SUPRA_QA_CUT_PHASE="$phase"
    cat > "$bindir/python3" <<'WRAPPER'
#!/bin/sh
set -eu
# Verify the wrapper itself can execute before running the real helper.
if [ "$#" -eq 1 ] && [ "$1" = --supra-qa-wrapper-probe ]; then
    echo PYTHON_WRAPPER_OK
    exit 0
fi
# Only the product helper's exchange invocation is allowed.
test "$#" -eq 3
test "$1" = -
case "$2" in /run/supralinux-recovery.*/btrfs) ;; *) exit 2;; esac
case "$3" in @rollback-*) ;; *) exit 2;; esac
pause() {
    printf '%s\n' "$SUPRA_QA_CUT_PHASE" > /run/supra-qa-cut/checkpoint
    while :; do sleep 1; done
}
if [ "$SUPRA_QA_CUT_PHASE" = before-exchange ]; then pause; fi
/usr/bin/python3 "$@"
if [ "$SUPRA_QA_CUT_PHASE" = after-exchange ]; then pause; fi
WRAPPER
    cat > "$bindir/mv" <<'WRAPPER'
#!/bin/sh
set -eu
if [ "$#" -eq 1 ] && [ "$1" = --supra-qa-wrapper-probe ]; then
    echo MV_WRAPPER_OK
    exit 0
fi
test "$#" -eq 4
test "$1" = -T
test "$2" = --
case "$3" in /run/supralinux-recovery.*/btrfs/@rollback-*) ;; *) exit 2;; esac
case "$4" in /run/supralinux-recovery.*/btrfs/@pre-rollback-*) ;; *) exit 2;; esac
pause() {
    printf '%s\n' "$SUPRA_QA_CUT_PHASE" > /run/supra-qa-cut/checkpoint
    while :; do sleep 1; done
}
if [ "$SUPRA_QA_CUT_PHASE" = before-backup-rename ]; then pause; fi
/usr/bin/mv "$@"
if [ "$SUPRA_QA_CUT_PHASE" = after-backup-rename ]; then pause; fi
WRAPPER
    chmod 0700 "$bindir/python3" "$bindir/mv"
    PATH="$bindir:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PATH
    test "$(command -v python3)" = "$bindir/python3"
    test "$(command -v mv)" = "$bindir/mv"
    test "$(python3 --supra-qa-wrapper-probe)" = PYTHON_WRAPPER_OK
    test "$(mv --supra-qa-wrapper-probe)" = MV_WRAPPER_OK
    /bin/sh -c 'test "$(python3 --supra-qa-wrapper-probe)" = PYTHON_WRAPPER_OK &&
        test "$(mv --supra-qa-wrapper-probe)" = MV_WRAPPER_OK'
    /usr/local/sbin/supralinux-recover --device "$dev" --snapshot 1 --yes --progress=json > "$work/helper.log" 2>&1
    # The harness must hard-stop at a checkpoint, never accept normal completion.
    exit 3
    ;;
verify)
    phase=${2:?}
    test "$(blkid -o value -s TYPE "$dev")" = btrfs
    top=$(mktemp -d /run/supra-cut-replay.XXXXXX)
    trap 'umount "$top" 2>/dev/null || true; rmdir "$top" 2>/dev/null || true' EXIT
    mount -o subvolid=5 "$dev" "$top"
    btrfs subvolume show "$top/@" >/dev/null
    test "$(cat "$top/@home/home-marker")" = unchanged
    test "$(cat "$top/@snapshots/1/snapshot/root-marker")" = original
    root=$(cat "$top/@/root-marker")
    set -- "$top"/@rollback-* "$top"/@pre-rollback-*
    count=0
    for item do
        test -d "$item" || continue
        btrfs subvolume show "$item" >/dev/null
        backup=$(cat "$item/root-marker")
        backup_name=${item##*/}
        count=$((count+1))
    done
    test "$count" -eq 1
    case "$root:$backup" in original:changed|changed:original) ;; *) exit 1;; esac
    case "$phase" in
        before-exchange) test "$root" = changed;;
        after-exchange) :;; # exchange not yet synced: either complete state is valid
        before-backup-rename|after-backup-rename) test "$root" = original;;
        *) exit 2;;
    esac
    printf 'CUT_PASS: phase=%s root=%s retained=%s name=%s home=unchanged snapshot=original\n' "$phase" "$root" "$backup" "$backup_name"
    umount "$top"
    ;;
*) exit 2;;
esac
