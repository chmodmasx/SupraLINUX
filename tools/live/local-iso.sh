#!/bin/bash
# Build a testing ISO from the committed local tree, without modifying it.
set -euo pipefail
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
if [[ $EUID -eq 0 ]]; then
    echo "Run make iso as your normal user; the live builder requests sudo." >&2
    exit 2
fi
if [[ "$(uname -m)" != x86_64 ]]; then
    echo "An amd64 Ubuntu 26.04-compatible build host is required." >&2
    exit 2
fi
if ! git -C "$repo" diff --quiet HEAD --; then
    echo "Commit tracked changes before building an ISO." >&2
    exit 2
fi
deps=(build-essential dpkg-dev debhelper gettext golang-go mmdebstrap uidmap squashfs-tools xorriso mtools dosfstools ubuntu-keyring git python3 sudo)
missing=()
for package in "${deps[@]}"; do
    if [[ "$(dpkg-query -W -f='${Status}' "$package" 2>/dev/null || true)" != "install ok installed" ]]; then
        missing+=("$package")
    fi
done
if (( ${#missing[@]} )); then
    echo "Missing host build dependencies: ${missing[*]}" >&2
    printf 'Install explicitly: sudo apt-get install --no-install-recommends %s\n' "${missing[*]}" >&2
    exit 2
fi
if [[ "$(dpkg --print-architecture)" != amd64 ]]; then
    echo "Expected amd64 Debian host architecture." >&2
    exit 2
fi
sha=$(git -C "$repo" rev-parse HEAD)
parent=$(realpath -m "${SUPRALINUX_WORKSPACE:-/var/tmp}")
case "$parent" in *[[:space:]]*) echo "Workspace path must not contain whitespace." >&2; exit 2;; esac
mkdir -p "$parent"
free=$(df -Pk "$parent" | awk 'NR==2 {print $4}')
if [[ "$free" -lt 23068672 ]]; then
    echo "INFRA_INVALID: at least 22 GiB free is required." >&2
    exit 1
fi
work=$(mktemp -d "$parent/supralinux-iso-XXXXXXXX")
chmod 0755 "$work"
# The mapped build root must be able to read the isolated checkout.
# Fail early if a parent directory denies traversal.
sudo -u '#100000' test -x "$work" || {
    echo "Workspace must be traversable by the mapped uid 100000: $work" >&2
    exit 1
}
echo "Workspace: $work"
echo "Committed source: $sha"
# A local clone makes all package builds disposable; no network Git access.
git clone --local --no-hardlinks --no-checkout -- "$repo" "$work/source"
git -C "$work/source" checkout --detach "$sha"
printf '%s\n' "$sha" > "$work/source-commit.txt"
export GOTOOLCHAIN=local GOPROXY=off GOSUMDB=off GOFLAGS=-mod=vendor CGO_ENABLED=0
for package in supralinux-defaults supralinux-calamares-config supralinux-kdeconnect-sftp; do
    python3 "$work/source/tools/ci/build-native-deb.py" "$package" "$work/overlays/$package"
done
python3 "$work/source/tools/live/stage-overlays.py" "$work/overlays" "$work/staged"
sh "$work/source/tools/live/build-testing-iso.sh" "$work/live" "$work/staged" 2>&1 | tee "$work/iso-build.log"
(
    cd "$work/live/build"
    sha256sum -c ./*.iso.sha256
)
printf '\nTesting ISO and checksum:\n'
find "$work/live/build" -maxdepth 1 -type f \( -name '*.iso' -o -name '*.iso.sha256' \) -print
printf 'Build workspace retained: %s\n' "$work"
