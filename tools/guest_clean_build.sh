#!/usr/bin/env bash
# Build the synthetic package in a disposable KVM guest, without network.
set -Eeuo pipefail

export LC_ALL=C
export LANG=C
export DEBIAN_FRONTEND=noninteractive

WORK=/srv/supralinux-clean-build
INPUT=/mnt/supralinux-inputs
ROOTFS="${WORK}/rootfs"
OUT="${WORK}/out"
RESULT="${WORK}/result.json"
BUILD_USER=ubuntu

infra_fail() {
    local message="$*"
    printf 'INFRA_INVALID: %s\n' "${message}" >&2
    python3 - "${RESULT}" "${message}" <<'PY'
import json
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(json.dumps({
    "schema": 1,
    "state": "INFRA_INVALID",
    "error": sys.argv[2],
}, indent=2) + "\n")
PY
    exit 1
}

mount_cleanup() {
    set +e
    for target in sys proc dev; do
        mountpoint -q "${ROOTFS}/${target}" && umount "${ROOTFS}/${target}"
    done
    mountpoint -q "${INPUT}" && umount "${INPUT}"
}
trap mount_cleanup EXIT

mkdir -p "${WORK}"
exec >>"${WORK}/run.log" 2>&1

printf '=== SupraLINUX clean sbuild build ===\n'
. /etc/os-release

[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]] || infra_fail "Expected Ubuntu 26.04"
[[ "$(systemd-detect-virt --vm 2>/dev/null || true)" == kvm ]] || infra_fail "Expected a KVM guest"
mapfile -t interfaces < <(find /sys/class/net -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)
[[ "${interfaces[*]}" == lo ]] || infra_fail "Expected only loopback networking, found: ${interfaces[*]}"
command -v sbuild >/dev/null || infra_fail "sbuild is not installed"
command -v runuser >/dev/null || infra_fail "runuser is not installed"
[[ "$(dpkg-query -W -f='${Version}' sbuild)" == "${SBUILD_VERSION}" ]] || infra_fail "Unexpected sbuild version"

mkdir -p "${INPUT}"
mount -o ro /dev/disk/by-label/SUPRAINPUTS "${INPUT}" || infra_fail "Cannot mount the read-only input disk"
[[ -f "${INPUT}/manifest.json" ]] || infra_fail "Input manifest is missing"
eval "$(python3 - "${INPUT}/manifest.json" <<'PY'
import json
import shlex
import sys

manifest = json.loads(open(sys.argv[1]).read())
print("PACKAGE=" + shlex.quote(manifest["package"]))
print("VERSION=" + shlex.quote(manifest["version"]))
print("ARCH=" + shlex.quote(manifest["architecture"]))
print("DSC_NAME=" + shlex.quote(manifest["source"]["dsc_name"]))
print("DECLARED_BUILD_DEPENDS=" + shlex.quote(manifest["source"]["declared_build_depends"]))
print("SBUILD_VERSION=" + shlex.quote(manifest["builder"]["sbuild_version"]))
print("DIST=" + shlex.quote(manifest["builder"]["distribution"]))
print("GUEST_ARCH=" + shlex.quote(manifest["builder"]["architecture"]))
PY
)"
[[ -n "${DSC_NAME}" && -f "${INPUT}/source/${DSC_NAME}" ]] || infra_fail "Source .dsc is missing"
[[ -f "${INPUT}/rootfs/resolute-amd64.tar" ]] || infra_fail "Buildd rootfs tarball is missing"
[[ -f "${INPUT}/repo/archive-key.gpg" ]] || infra_fail "Repository key is missing"

rm -rf "${WORK}/source" "${WORK}/repo" "${ROOTFS}" "${OUT}"
mkdir -p "${WORK}/source" "${WORK}/repo" "${ROOTFS}" "${OUT}"
cp -a "${INPUT}/source/." "${WORK}/source/"
cp -a "${INPUT}/repo/." "${WORK}/repo/"
cp "${INPUT}/rootfs/resolute-amd64.tar" "${WORK}/rootfs.tar"
cp "${INPUT}/manifest.json" "${WORK}/manifest.json"
tar -xf "${WORK}/rootfs.tar" -C "${ROOTFS}"
[[ -f "${ROOTFS}/var/lib/dpkg/status" ]] || infra_fail "Extracted rootfs has no dpkg status"

install -d -m 0755 "${ROOTFS}/srv/supralinux-local-repo"
cp "${WORK}/repo/"*.deb "${WORK}/repo/Packages" "${WORK}/repo/Packages.gz" \
   "${WORK}/repo/Release" "${WORK}/repo/InRelease" "${WORK}/repo/Release.gpg" \
   "${ROOTFS}/srv/supralinux-local-repo/"
chmod -R a+rX "${ROOTFS}/srv/supralinux-local-repo"
install -D -m 0644 "${WORK}/repo/archive-key.gpg" \
    "${ROOTFS}/usr/share/keyrings/supralinux-local.gpg"

if [[ -f "${ROOTFS}/etc/apt/sources.list" ]]; then
    mv "${ROOTFS}/etc/apt/sources.list" "${ROOTFS}/etc/apt/sources.list.disabled"
fi
install -d -m 0755 "${ROOTFS}/etc/apt/sources.list.d"
find "${ROOTFS}/etc/apt/sources.list.d" -mindepth 1 -maxdepth 1 -type f -delete
cat >"${ROOTFS}/etc/apt/sources.list.d/supralinux-local.list" <<'EOF'
deb [signed-by=/usr/share/keyrings/supralinux-local.gpg] file:/srv/supralinux-local-repo ./
EOF

chroot "${ROOTFS}" dpkg-query -W -f='${Package}\t${Version}\n' | sort >"${WORK}/base-packages.txt"
if awk -F'\t' '$1 == "debhelper" { found=1 } END { exit !found }' "${WORK}/base-packages.txt"; then
    infra_fail "Base rootfs unexpectedly contains debhelper"
fi

for target in dev proc sys; do
    mount --bind "/${target}" "${ROOTFS}/${target}"
done
chroot "${ROOTFS}" apt-get update >"${WORK}/apt-update.log" 2>&1 || infra_fail "Local APT update failed"
chroot "${ROOTFS}" apt-get -s install debhelper >"${WORK}/apt-simulation.log" 2>&1 || infra_fail "Build-dependency simulation failed"
grep -q '^Inst debhelper ' "${WORK}/apt-simulation.log" || infra_fail "Simulation did not select debhelper"
for target in sys proc dev; do
    umount "${ROOTFS}/${target}"
done
trap mount_cleanup EXIT

mkdir -p "/home/${BUILD_USER}/.cache/sbuild" "${WORK}/tmp"
tar --numeric-owner -C "${ROOTFS}" -cf "/home/${BUILD_USER}/.cache/sbuild/resolute-amd64.tar" .
sha256sum "/home/${BUILD_USER}/.cache/sbuild/resolute-amd64.tar" >"${WORK}/chroot-sha256.txt"
chown -R "${BUILD_USER}:${BUILD_USER}" "${WORK}/source" "${WORK}/repo" "${OUT}" "${WORK}/tmp" "/home/${BUILD_USER}/.cache/sbuild"
chmod a+r "${WORK}/rootfs.tar" "${WORK}/manifest.json" "${WORK}/base-packages.txt"
chmod a+r "/home/${BUILD_USER}/.cache/sbuild/resolute-amd64.tar"

set +e
runuser -u "${BUILD_USER}" -- env HOME="/home/${BUILD_USER}" USER="${BUILD_USER}" LOGNAME="${BUILD_USER}" \
    TMPDIR="${WORK}/tmp" LC_ALL=C.UTF-8 LANG=C.UTF-8 \
    sbuild --verbose --chroot-mode=unshare --dist="${DIST}" --arch="${GUEST_ARCH}" --arch-all \
    --no-run-lintian --build-dir="${OUT}" "${WORK}/source/${DSC_NAME}" \
    >"${WORK}/sbuild.log" 2>&1
sbuild_rc=$?
set -e

python3 - "${WORK}" "${WORK}/manifest.json" "${sbuild_rc}" <<'PY'
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

work = Path(sys.argv[1])
manifest = json.loads(Path(sys.argv[2]).read_text())
sbuild_rc = int(sys.argv[3])
out = work / "out"
result = {
    "schema": 1,
    "scope": manifest["scope"],
    "state": "FAIL",
    "package": manifest["package"],
    "version": manifest["version"],
    "architecture": manifest["architecture"],
    "sbuild_exit_code": sbuild_rc,
    "sbuild_version": subprocess.check_output(
        ["dpkg-query", "-W", "-f=${Version}", "sbuild"], text=True
    ).strip(),
    "interfaces": sorted(p.name for p in Path("/sys/class/net").iterdir()),
    "logs": {},
}


def digest(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def fields(path):
    values = {}
    key = None
    for line in path.read_text().splitlines():
        if line.startswith((" ", "\t")) and key:
            values[key] = (values[key] + "\n" if values[key] else "") + line.strip()
        elif ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


for name in ["run.log", "apt-update.log", "apt-simulation.log", "base-packages.txt", "sbuild.log"]:
    path = work / name
    if path.is_file():
        result["logs"][name] = {"sha256": digest(path), "bytes": path.stat().st_size}

if sbuild_rc != 0:
    result["error"] = f"sbuild exited with {sbuild_rc}"
    (work / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    raise SystemExit(0)

try:
    debs = sorted(out.glob("*.deb"))
    changes = sorted(out.glob("*.changes"))
    buildinfo = sorted(out.glob("*.buildinfo"))
    if not debs or len(changes) != 1 or len(buildinfo) != 1:
        raise ValueError(
            f"Expected deb artifacts and one changes/buildinfo, got {len(debs)}/{len(changes)}/{len(buildinfo)}"
        )
    change, info = changes[0], buildinfo[0]
    actual = {}
    path_by_package = {}
    for deb in debs:
        deb_fields = dict(line.split(": ", 1) for line in subprocess.check_output(
            ["dpkg-deb", "-f", str(deb), "Package", "Version", "Architecture"], text=True
        ).splitlines() if ": " in line)
        if deb_fields.get("Version") != manifest["version"]:
            raise ValueError("Built package version differs from the manifest")
        actual[deb_fields["Package"]] = deb_fields
        path_by_package[deb_fields["Package"]] = deb
    expected_binaries = manifest.get("expected_binaries", [])
    if expected_binaries:
        wanted = {entry["package"]: entry["architecture"] for entry in expected_binaries}
        if set(actual) != set(wanted):
            raise ValueError(f"Built binary set differs: expected {sorted(wanted)}, got {sorted(actual)}")
        for package, architecture in wanted.items():
            if actual[package]["Architecture"] != architecture:
                raise ValueError("Built package architecture differs: " + package)
    elif len(debs) != 1 or actual.get(manifest["package"], {}).get("Architecture") != manifest["architecture"]:
        raise ValueError("Built package identity differs from the manifest")

    artifacts = []
    for path in debs + [change, info]:
        artifacts.append({"name": path.name, "sha256": digest(path), "bytes": path.stat().st_size})
    result["artifacts"] = artifacts
    result["debs"] = [{"package": package, "name": path.name, "sha256": digest(path)}
                      for package, path in sorted(path_by_package.items())]

    unpacked = work / "unpacked"
    if unpacked.exists():
        raise ValueError("Unpacked verification directory already exists")
    for deb in debs:
        subprocess.run(["dpkg-deb", "-x", str(deb), str(unpacked)], check=True)
    for name in manifest.get("verification", {}).get("expected_paths", []):
        path = unpacked / name.lstrip("/")
        if path.is_symlink() or not path.is_file():
            raise ValueError("Expected installed path missing: " + name)
    installed = {}
    for name, expected in manifest.get("expected_installed_files", {}).items():
        path = unpacked / name.lstrip("/")
        if path.is_symlink() or not path.is_file():
            raise ValueError("Expected regular installed payload: " + name)
        actual_hash = digest(path)
        if actual_hash != expected:
            raise ValueError("Installed payload hash mismatch: " + name)
        installed[name] = actual_hash

    info_fields = fields(info)
    deps = info_fields.get("Installed-Build-Depends", "")
    if not re.search(r"(?:^|,\s*)debhelper(?:\s|\()", deps):
        raise ValueError("buildinfo does not record debhelper as installed")
    if re.search(r"(?:^|,\s*)sbuild(?:\s|\()", deps):
        raise ValueError("buildinfo records sbuild inside the build environment")
    if not re.search(r"(?:^|,\s*)build-essential(?:\s|\()", deps):
        raise ValueError("buildinfo does not record build-essential")
    dsc = work / "source" / manifest["source"]["dsc_name"]
    tarballs = sorted(path for path in (work / "source").glob("*.tar.xz")
                      if not path.name.endswith(".debian.tar.xz"))
    if len(tarballs) != 1:
        raise ValueError(f"Expected one upstream source tarball, got {len(tarballs)}")
    source_fields = fields(dsc)
    if manifest["source"]["declared_build_depends"] not in source_fields.get("Build-Depends", ""):
        raise ValueError("source .dsc does not record the declared Build-Depends")

    checksums = {}
    for line in info_fields.get("Checksums-Sha256", "").splitlines():
        parts = line.split()
        if len(parts) == 3:
            checksums[parts[2]] = parts[0]
    for deb in debs:
        if checksums.get(deb.name) != digest(deb):
            raise ValueError("buildinfo does not bind the built .deb: " + deb.name)

    change_fields = fields(change)
    change_checksums = {}
    for line in change_fields.get("Checksums-Sha256", "").splitlines():
        parts = line.split()
        if len(parts) == 3:
            change_checksums[parts[2]] = parts[0]
    for deb in debs:
        if change_checksums.get(deb.name) != digest(deb):
            raise ValueError(".changes does not bind the built .deb: " + deb.name)
    if change_checksums.get(info.name) != digest(info):
        raise ValueError(".changes does not bind the .buildinfo")

    consumer = manifest.get("verification", {}).get("consumer")
    if consumer:
        if consumer != "ecm":
            raise ValueError("Unsupported consumer smoke: " + consumer)
        consumer_version = manifest.get("verification", {}).get("consumer_version")
        if not consumer_version:
            raise ValueError("ECM consumer smoke requires consumer_version")
        configs = list(unpacked.rglob("ECMConfig.cmake"))
        if len(configs) != 1:
            raise ValueError(f"Expected one ECMConfig.cmake, got {len(configs)}")
        consumer_src = work / "consumer-src"
        consumer_src.mkdir()
        (consumer_src / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.29)\n"
            "project(SupraLINUXECMConsumer NONE)\n"
            f"find_package(ECM {consumer_version} REQUIRED NO_MODULE)\n"
            "set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})\n"
            "include(KDEInstallDirs6)\n"
            "include(KDECMakeSettings)\n"
            "include(ECMSetupVersion)\n"
            "include(ECMGenerateHeaders)\n"
            f"if(NOT ECM_VERSION VERSION_EQUAL \"{consumer_version}\")\n"
            f"  message(FATAL_ERROR \"Expected ECM {consumer_version}, found ${{ECM_VERSION}}\")\n"
            "endif()\n"
            "message(STATUS \"SUPRALINUX_ECM_VERSION=${ECM_VERSION}\")\n"
        )
        completed = subprocess.run(
            ["cmake", "-S", str(consumer_src), "-B", str(work / "consumer-build"),
             f"-DECM_DIR={configs[0].parent}"],
            text=True, capture_output=True, check=False,
        )
        (work / "consumer-cmake.log").write_text(completed.stdout + completed.stderr)
        expected = "SUPRALINUX_ECM_VERSION=" + consumer_version
        if completed.returncode != 0 or expected not in completed.stdout:
            raise ValueError("ECM CMake consumer smoke failed")
        result["consumer_smoke"] = "PASS"
        result["consumer_cmake_log_sha256"] = digest(work / "consumer-cmake.log")

    base_packages = [
        line.split("\t", 1)[0]
        for line in (work / "base-packages.txt").read_text().splitlines()
        if "\t" in line
    ]
    result.update({
        "state": "PASS",
        "chroot_sha256": (work / "chroot-sha256.txt").read_text().split()[0],
        "source_dsc_sha256": digest(dsc),
        "source_tar_sha256": digest(tarballs[0]),
        "base_package_count": len(base_packages),
        "base_has_debhelper": "debhelper" in base_packages,
        "apt_simulation_debhelper": True,
        "installed_build_depends": deps.splitlines(),
        "installed_files_sha256": installed,
        "artifacts": artifacts,
    })
except Exception as error:
    result["error"] = str(error)

(work / "result.json").write_text(json.dumps(result, indent=2) + "\n")
PY

printf 'Guest result state: %s\n' "$(python3 -c 'import json; print(json.load(open("'"${RESULT}"'"))["state"])')"
