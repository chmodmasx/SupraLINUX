#!/usr/bin/env python3
"""Rebuild one pinned source package in a disposable, offline sbuild guest."""
import argparse
import base64
import datetime
import fcntl
import hashlib
import io
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = Path(os.environ.get("SUPRALINUX_WORKSPACE", ROOT.parent / "SupraLINUX-workspace")).expanduser().resolve()
DEFAULT_GUEST_TIMEOUT = 1800
sys.path.insert(0, str(ROOT / "tools"))
import package_smoke as smoke


def workspace_path(value):
    path = Path(value).expanduser()
    return (WORKSPACE / path).resolve() if not path.is_absolute() else path.resolve()


def cache_dir():
    path = WORKSPACE / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_workspace():
    for name in ["cache", "kvm/runs", "kvm/bases", "artifacts/sha256", "evidence"]:
        (WORKSPACE / name).mkdir(parents=True, exist_ok=True)



def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def control_fields(text):
    fields = {}
    key = None
    for line in text.splitlines():
        if line.startswith((" ", "\t")) and key:
            fields[key] = (fields[key] + "\n" if fields[key] else "") + line.strip()
        elif ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def load_manifest(path=None):
    path = Path(path) if path else ROOT / "manifests/clean-build.json"
    manifest = json.loads(path.read_text())
    smoke.require(manifest.get("schema") == 1 and manifest.get("scope") == "offline-clean-sbuild-build",
                  "Wrong clean-build scope")
    smoke.require(re.fullmatch(r"[a-z0-9][a-z0-9+.-]+", manifest["package"]), "Invalid package name")
    smoke.require(manifest["architecture"] in ("all", "amd64"), "Unsupported top-level architecture")
    source = (ROOT / manifest["source"]["path"]).resolve()
    smoke.require(source.is_relative_to(ROOT.resolve()) and source.is_dir() and not source.is_symlink(),
                  "Unsafe source path")
    smoke.require((source / "debian/control").is_file(), "Missing source packaging")
    kind = manifest["source"].get("kind", "native")
    smoke.require(kind in ("native", "quilt"), "Unsupported source kind")
    smoke.require(manifest["source"].get("dsc_name"), "Missing source .dsc name")
    if kind == "quilt":
        for field in ["source_package", "version", "upstream_version"]:
            smoke.require(manifest["source"].get(field), "Missing quilt source field: " + field)
        upstream = manifest["source"].get("upstream", {})
        for field in ["url", "sha256", "filename", "extracted_dir", "orig_filename"]:
            smoke.require(upstream.get(field), "Missing upstream source field: " + field)
        smoke.require(re.fullmatch(r"[a-f0-9]{64}", upstream["sha256"]), "Invalid upstream SHA-256")
        smoke.require(manifest["source"]["dsc_name"].endswith(".dsc"), "Invalid .dsc name")
    else:
        smoke.require(re.fullmatch(r"[a-f0-9]{40}", manifest["source"]["original_commit"]),
                      "Invalid source commit")
    for name, item in [("base_image", manifest["base_image"]), ("rootfs", manifest["rootfs"])]:
        smoke.require(re.fullmatch(r"[a-f0-9]{64}", item["sha256"]), "Invalid SHA-256")
        path = workspace_path(item["path"])
        if name == "base_image":
            retained = WORKSPACE / "kvm/bases" / (item["sha256"] + ".qcow2")
        else:
            retained = WORKSPACE / "artifacts/sha256" / item["sha256"] / path.name
        smoke.require(path.is_file() or retained.is_file(), "Missing input: " + str(path))
    smoke.require(manifest["base_image"]["format"] == "qcow2", "Expected a qcow2 base image")
    deps = manifest["build_dependencies"]["packages"]
    smoke.require(deps, "No build-dependency artifacts")
    names = [entry["filename"] for entry in deps]
    smoke.require(len(names) == len(set(names)), "Duplicate build-dependency filenames")
    dependency_source = workspace_path(manifest["build_dependencies"]["source_evidence"])
    for entry in deps:
        smoke.require(re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]), "Invalid dependency SHA-256")
        source = dependency_source / entry["sha256"] / entry["filename"]
        retained = WORKSPACE / "artifacts/sha256" / entry["sha256"] / entry["filename"]
        smoke.require(source.is_file() or retained.is_file(),
                      "Missing dependency artifact: " + entry["filename"])
    for filename, expected in manifest.get("expected_installed_files", {}).items():
        smoke.require(filename.startswith("/") and re.fullmatch(r"[a-f0-9]{64}", expected),
                      "Invalid expected installed file")
    for filename in manifest.get("verification", {}).get("expected_paths", []):
        smoke.require(filename.startswith("/"), "Invalid expected installed path")
    expected_binaries = manifest.get("expected_binaries", [])
    if expected_binaries:
        names = [entry.get("package") for entry in expected_binaries]
        smoke.require(all(names) and len(names) == len(set(names)), "Invalid expected binary list")
        smoke.require(all(entry.get("architecture") for entry in expected_binaries),
                      "Missing expected binary architecture")
    smoke.require(manifest["builder"]["chroot_mode"] == "unshare", "Expected sbuild unshare mode")
    smoke.require(manifest["builder"]["guest_network"].startswith("none"), "Guest network must be disabled")
    ram = manifest["builder"].get("guest_ram_mib", 2048)
    smoke.require(isinstance(ram, int) and not isinstance(ram, bool) and 1024 <= ram <= 16384,
                  "Invalid guest RAM size")
    vcpus = manifest["builder"].get("guest_vcpus", 2)
    smoke.require(isinstance(vcpus, int) and not isinstance(vcpus, bool) and 1 <= vcpus <= 8,
                  "Invalid guest vCPU count")
    manifest["builder"]["guest_ram_mib"] = ram
    manifest["builder"]["guest_vcpus"] = vcpus
    timeout = manifest["builder"].get("guest_timeout_seconds", DEFAULT_GUEST_TIMEOUT)
    smoke.require(isinstance(timeout, int) and not isinstance(timeout, bool)
                  and 600 <= timeout <= 7200, "Invalid guest timeout")
    manifest["builder"]["guest_timeout_seconds"] = timeout
    return manifest


def download(url, target, expected):
    request = urllib.request.Request(url, headers={"User-Agent": "SupraLINUX-source/1"})
    with urllib.request.urlopen(request, timeout=180) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output)
    smoke.require(digest(target) == expected, f"Source SHA-256 mismatch: {url}")


def prepare_source(run_dir, manifest):
    source_path = manifest["source"]["path"]
    kind = manifest["source"].get("kind", "native")
    with tempfile.TemporaryDirectory(prefix="clean-source-", dir=cache_dir()) as directory:
        temporary = Path(directory)
        if kind == "native":
            archive = subprocess.check_output(
                ["git", "-C", str(ROOT), "archive", "HEAD", source_path], timeout=120
            )
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
                tar.extractall(temporary, filter="data")
            package_dir = temporary / source_path
            smoke.require(package_dir.is_dir(), "Archived source tree is missing")
            subprocess.run(["dpkg-source", "-b", str(package_dir)], cwd=temporary, check=True,
                           capture_output=True, text=True, timeout=120)
            dsc = temporary / f"{manifest['package']}_{manifest['version']}.dsc"
            tarball = temporary / f"{manifest['package']}_{manifest['version']}.tar.xz"
            files = [dsc, tarball]
        else:
            source = manifest["source"]
            upstream = source["upstream"]
            tarball = temporary / upstream["orig_filename"]
            download(upstream["url"], tarball, upstream["sha256"])
            with tarfile.open(tarball) as archive:
                # Keep upstream symlink spellings exact; dpkg-source compares them
                # against the original tarball. The tarball is pinned by SHA-256.
                archive.extractall(temporary, filter="tar")
            extracted = temporary / upstream["extracted_dir"]
            smoke.require(extracted.is_dir(), "Extracted upstream source directory is missing")
            source_dir = temporary / f"{source['source_package']}-{source['upstream_version']}"
            extracted.rename(source_dir)
            # Native upstream tarballs may ship their own debian/ directory.
            # Quilt packaging must use the reviewed debian/ from this repository.
            upstream_debian = source_dir / "debian"
            if upstream_debian.exists():
                shutil.rmtree(upstream_debian)
            shutil.copytree(ROOT / source_path / "debian", source_dir / "debian")
            (source_dir / "debian/rules").chmod(0o755)
            subprocess.run(["dpkg-source", "-b", str(source_dir)], cwd=temporary,
                           check=True, capture_output=True, text=True, timeout=180)
            dsc = temporary / source["dsc_name"]
            debian_tar = temporary / (
                f"{source['source_package']}_{source['version'].split(':', 1)[-1]}.debian.tar.xz"
            )
            files = [dsc, tarball, debian_tar]
        smoke.require(all(path.is_file() for path in files),
                      "Source package creation did not create the expected files")
        target = run_dir / "source"
        target.mkdir()
        for path in files:
            shutil.copyfile(path, target / path.name)
            (target / path.name).chmod(0o444)
        result = {
            "dsc": target / dsc.name,
            "tar": target / tarball.name,
            "dsc_sha256": digest(target / dsc.name),
            "tar_sha256": digest(target / tarball.name),
            "kind": kind,
        }
        if kind == "quilt":
            result["debian_tar"] = target / debian_tar.name
            result["debian_tar_sha256"] = digest(target / debian_tar.name)
        return result


def prepare_rootfs(manifest):
    item = manifest["rootfs"]
    source = workspace_path(item["path"])
    target = WORKSPACE / "artifacts/sha256" / item["sha256"] / source.name
    reused = smoke.restore_file(source, target, item["sha256"])
    with tarfile.open(target) as archive:
        names = {name.lstrip("./"): name for name in archive.getnames()}
        smoke.require("var/lib/dpkg/status" in names, "Rootfs has no dpkg status")
        status = archive.extractfile(names["var/lib/dpkg/status"]).read().decode()
    packages = {}
    for paragraph in status.split("\n\n"):
        fields = control_fields(paragraph)
        if fields.get("Status") == "install ok installed":
            packages[fields["Package"]] = fields.get("Version")
    smoke.require(len(packages) == manifest["rootfs"]["installed_package_count"],
                  "Rootfs package count changed")
    smoke.require("debhelper" not in packages and "fakeroot" not in packages,
                  "Buildd rootfs must not preinstall debhelper/fakeroot")
    return target, reused, len(packages)


def prepare_dependencies(manifest, run_dir):
    source_evidence = workspace_path(manifest["build_dependencies"]["source_evidence"])
    paths = []
    for entry in manifest["build_dependencies"]["packages"]:
        source = source_evidence / entry["sha256"] / entry["filename"]
        retained = WORKSPACE / "artifacts/sha256" / entry["sha256"] / entry["filename"]
        if not source.is_file() and retained.is_file():
            source = retained
        target = WORKSPACE / "artifacts/sha256" / entry["sha256"] / entry["filename"]
        smoke.restore_file(source, target, entry["sha256"])
        identity = smoke.command(
            ["dpkg-deb", "-f", str(target), "Package", "Version", "Architecture"]
        )
        expected = (f"Package: {entry['name']}\nVersion: {entry['version']}\n"
                    f"Architecture: {entry['architecture']}\n")
        smoke.require(identity == expected, "Dependency identity mismatch: " + entry["filename"])
        paths.append(target)
    repository = run_dir / "repository"
    fingerprint = smoke.signed_repository(paths, repository)
    shutil.copyfile(run_dir / "archive-key.gpg", repository / "archive-key.gpg")
    for name in ["Packages", "Packages.gz", "Release", "InRelease", "Release.gpg"]:
        smoke.require((repository / name).is_file(), "Repository metadata missing: " + name)
    return paths, repository, fingerprint


def build_input_image(staging, runtime):
    total = sum(path.stat().st_size for path in staging.rglob("*") if path.is_file())
    size_mib = max(640, math.ceil(total / 1024**2) + 128)
    image = runtime / "inputs.img"
    with image.open("wb") as handle:
        handle.truncate(size_mib * 1024**2)
    smoke.command(["mkfs.ext4", "-q", "-F", "-L", "SUPRAINPUTS", "-d", str(staging), str(image)],
                  timeout=900)
    smoke.command(["e2fsck", "-fn", str(image)], timeout=900)
    return image, {"bytes": image.stat().st_size, "sha256": digest(image), "size_mib": size_mib}


def qemu_command(overlay, inputs, agent_socket, console, name, ram_mib=2048, vcpus=2):
    for path in [overlay, inputs, agent_socket, console]:
        smoke.require(not any(char in str(path) for char in [",", "\n", "\0"]),
                      "Unsafe QEMU option path")
    smoke.require(len(str(agent_socket).encode()) < 100, "Unix socket path too long")
    smoke.require(1024 <= ram_mib <= 16384 and 1 <= vcpus <= 8, "Unsafe QEMU resource request")
    return ["qemu-system-x86_64", "-name", name, "-machine", "q35,accel=kvm", "-cpu", "host",
            "-m", str(ram_mib), "-smp", str(vcpus), "-nodefaults", "-display", "none", "-monitor", "none",
            "-nic", "none",
            "-drive", f"if=none,id=osdisk,file={overlay},format=qcow2",
            "-device", "virtio-blk-pci,drive=osdisk",
            "-drive", f"if=none,id=inputs,file={inputs},format=raw,readonly=on",
            "-device", "virtio-blk-pci,drive=inputs",
            "-device", "virtio-serial-pci",
            "-chardev", f"socket,path={agent_socket},server=on,wait=off,id=qga",
            "-device", "virtserialport,chardev=qga,name=org.qemu.guest_agent.0",
            "-serial", f"file:{console}"]


def retrieve(agent, remote, local, limit=32 * 1024 * 1024):
    try:
        data = agent.get(remote, limit=limit)
    except Exception:
        return False
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(data)
    return True


def verify_binaries(artifacts, manifest):
    expected = manifest.get("expected_binaries", [])
    actual = {}
    path_by_package = {}
    for artifact in artifacts:
        fields = dict(line.split(": ", 1) for line in smoke.command(
            ["dpkg-deb", "-f", str(artifact), "Package", "Version", "Architecture"]
        ).splitlines() if ": " in line)
        if fields.get("Version") != manifest["version"]:
            raise ValueError("Built binary version mismatch: " + artifact.name)
        actual[fields["Package"]] = fields
        path_by_package[fields["Package"]] = artifact
    if expected:
        wanted = {entry["package"]: entry["architecture"] for entry in expected}
        if set(actual) != set(wanted):
            raise ValueError(f"Built binary set mismatch: expected {sorted(wanted)}, got {sorted(actual)}")
        for name, architecture in wanted.items():
            if actual[name]["Architecture"] != architecture:
                raise ValueError("Built binary architecture mismatch: " + name)
    else:
        smoke.require(len(artifacts) == 1, "Expected exactly one built binary")
        if actual.get(manifest["package"], {}).get("Architecture") != manifest["architecture"]:
            raise ValueError("Built binary identity mismatch")
    with tempfile.TemporaryDirectory(prefix="verify-deb-", dir=cache_dir()) as directory:
        root = Path(directory)
        for artifact in artifacts:
            smoke.command(["dpkg-deb", "-x", str(artifact), str(root)])
        for name in manifest.get("verification", {}).get("expected_paths", []):
            path = root / name.lstrip("/")
            smoke.require(path.is_file() and not path.is_symlink(), "Built payload path missing: " + name)
        for name, expected_hash in manifest.get("expected_installed_files", {}).items():
            path = root / name.lstrip("/")
            smoke.require(path.is_file() and not path.is_symlink(), "Built payload missing: " + name)
            smoke.require(digest(path) == expected_hash, "Built payload hash mismatch: " + name)
    primary_name = manifest["package"] if manifest["package"] in actual else sorted(actual)[0]
    return actual, primary_name, path_by_package


def verify_build_outputs(build_dir, guest, manifest, source):
    debs = sorted(build_dir.glob("*.deb"))
    changes = sorted(build_dir.glob("*.changes"))
    infos = sorted(build_dir.glob("*.buildinfo"))
    smoke.require(debs and len(changes) == 1 and len(infos) == 1,
                  "Expected .deb artifacts, one .changes and one .buildinfo")
    change, info = changes[0], infos[0]
    actual, primary_name, path_by_package = verify_binaries(debs, manifest)
    primary = path_by_package[primary_name]
    info_fields = control_fields(info.read_text())
    deps = info_fields.get("Installed-Build-Depends", "")
    smoke.require(re.search(r"(?:^|,\s*)debhelper(?:\s|\()", deps),
                  "buildinfo does not record debhelper")
    smoke.require(not re.search(r"(?:^|,\s*)sbuild(?:\s|\()", deps),
                  "buildinfo records sbuild inside the build environment")
    checksums = {}
    for line in info_fields.get("Checksums-Sha256", "").splitlines():
        parts = line.split()
        if len(parts) == 3:
            checksums[parts[2]] = parts[0]
    for artifact in debs:
        smoke.require(checksums.get(artifact.name) == digest(artifact),
                      "buildinfo does not bind the .deb: " + artifact.name)
    change_fields = control_fields(change.read_text())
    change_checksums = {}
    for line in change_fields.get("Checksums-Sha256", "").splitlines():
        parts = line.split()
        if len(parts) == 3:
            change_checksums[parts[2]] = parts[0]
    for artifact in debs:
        smoke.require(change_checksums.get(artifact.name) == digest(artifact),
                      ".changes does not bind the .deb: " + artifact.name)
    smoke.require(change_checksums.get(info.name) == digest(info), ".changes does not bind the .buildinfo")
    dsc_fields = control_fields(source["dsc"].read_text())
    smoke.require(manifest["source"]["declared_build_depends"] in dsc_fields.get("Build-Depends", ""),
                  "source .dsc does not record Build-Depends")
    dsc_checksums = {}
    for line in dsc_fields.get("Checksums-Sha256", "").splitlines():
        parts = line.split()
        if len(parts) == 3:
            dsc_checksums[parts[2]] = parts[0]
    smoke.require(dsc_checksums.get(source["tar"].name) == source["tar_sha256"],
                  ".dsc does not bind the source tarball")
    if "debian_tar" in source:
        smoke.require(dsc_checksums.get(source["debian_tar"].name) == source["debian_tar_sha256"],
                      ".dsc does not bind the Debian tarball")
    return {"deb": primary, "debs": debs, "changes": change, "buildinfo": info,
            "sha256": digest(primary), "installed_build_depends": deps.splitlines(),
            "buildinfo_sha256": digest(info), "changes_sha256": digest(change)}


def build(manifest_path=None):
    smoke.require(os.geteuid() != 0, "Run on the host as an unprivileged KVM user, not root")
    smoke.require(not smoke.command(["git", "-C", str(ROOT), "status", "--porcelain"]).strip(),
                  "Commit reviewed inputs before execution")
    manifest_file = Path(manifest_path).resolve() if manifest_path else ROOT / "manifests/clean-build.json"
    manifest = load_manifest(manifest_file)
    ensure_workspace()
    for name in ["qemu-system-x86_64", "qemu-img", "dpkg-source", "dpkg-deb", "dpkg-scanpackages",
                 "gpg", "gpgconf", "gpgv", "mkfs.ext4", "e2fsck"]:
        smoke.require(shutil.which(name), "Missing existing tool: " + name)
    with open("/dev/kvm", "r+b", buffering=0) as device:
        smoke.require(fcntl.ioctl(device, 0xAE00, 0) == 12, "Unexpected KVM API")
    available = int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines()
                         if line.startswith("MemAvailable:")))
    guest_ram_mib = manifest["builder"]["guest_ram_mib"]
    smoke.require(available >= (guest_ram_mib + 1536) * 1024,
                  f"Not enough available RAM for a {guest_ram_mib} MiB guest plus margin")
    smoke.require(not list((WORKSPACE / "kvm/runs").iterdir()),
                  "Previous runtime state remains; inspect it before starting another VM")
    smoke.require(shutil.disk_usage(WORKSPACE).free >= 20 * 1024**3,
                  "Less than 20 GiB free: refuse build preparation")

    run_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:12]
    evidence = WORKSPACE / "evidence/clean-build" / run_id
    runtime = WORKSPACE / "kvm/runs" / run_id
    staging = WORKSPACE / "cache/clean-build" / run_id / "inputs"
    evidence.mkdir(parents=True, mode=0o700)
    runtime.mkdir(mode=0o700)
    staging.mkdir(parents=True, mode=0o700)
    overlay, socket_path = runtime / "disk.qcow2", runtime / "agent.sock"
    report = {
        "schema": 1, "scope": manifest["scope"], "state": "INFRA_INVALID", "run_id": run_id,
        "code_commit": smoke.command(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).strip(),
        "manifest_path": str(manifest_file), "manifest_sha256": digest(manifest_file),
        "host_network_modified": False, "sbuild_invoked": False,
        "package_attempt_consumed": False, "kde_or_distro_certification": False,
        "timings_seconds": {},
    }
    started = time.monotonic()
    process = agent = None
    base = WORKSPACE / "kvm/bases" / (manifest["base_image"]["sha256"] + ".qcow2")
    guest = None
    try:
        phase = time.monotonic()
        report["base_reused"] = smoke.restore_file(workspace_path(manifest["base_image"]["path"]), base,
                                                   manifest["base_image"]["sha256"])
        info = json.loads(smoke.command(["qemu-img", "info", "--output=json", "-f", "qcow2", str(base)]))
        smoke.require(not info.get("backing-filename") and info["format"] == "qcow2",
                      "Builder base must be standalone qcow2")
        smoke.command(["qemu-img", "check", "-f", "qcow2", str(base)])
        report["base_sha256"] = manifest["base_image"]["sha256"]
        report["timings_seconds"]["base_preparation"] = round(time.monotonic() - phase, 3)

        phase = time.monotonic()
        source = prepare_source(evidence, manifest)
        report["source"] = {"kind": source["kind"], "dsc_sha256": source["dsc_sha256"],
                            "tar_sha256": source["tar_sha256"],
                            "dsc_name": source["dsc"].name, "tar_name": source["tar"].name}
        if "debian_tar" in source:
            report["source"]["debian_tar_sha256"] = source["debian_tar_sha256"]
            report["source"]["debian_tar_name"] = source["debian_tar"].name
        rootfs, rootfs_reused, package_count = prepare_rootfs(manifest)
        report["rootfs"] = {"sha256": manifest["rootfs"]["sha256"], "reused": rootfs_reused,
                            "installed_package_count": package_count}
        deps, repository, fingerprint = prepare_dependencies(manifest, evidence)
        report["dependency_repository"] = {"count": len(deps), "key_fingerprint": fingerprint,
                                           "sha256": digest(repository / "Packages")}
        report["timings_seconds"]["source_and_inputs"] = round(time.monotonic() - phase, 3)

        phase = time.monotonic()
        (staging / "source").mkdir()
        (staging / "repo").mkdir()
        (staging / "rootfs").mkdir()
        (staging / "scripts").mkdir()
        for path in [source["dsc"], source["tar"]] + ([source["debian_tar"]] if "debian_tar" in source else []):
            shutil.copyfile(path, staging / "source" / path.name)
        shutil.copytree(repository, staging / "repo", dirs_exist_ok=True)
        shutil.copyfile(manifest_file, staging / "manifest.json")
        shutil.copyfile(ROOT / "tools/guest_clean_build.sh", staging / "scripts" / "build.sh")
        try:
            os.link(rootfs, staging / "rootfs" / "resolute-amd64.tar")
        except OSError:
            shutil.copyfile(rootfs, staging / "rootfs" / "resolute-amd64.tar")
        inputs_image, inputs_info = build_input_image(staging, runtime)
        report["inputs_image"] = inputs_info
        report["timings_seconds"]["input_image"] = round(time.monotonic() - phase, 3)

        phase = time.monotonic()
        smoke.command(["qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b", str(base), str(overlay)])
        args = qemu_command(overlay, inputs_image, socket_path, evidence / "console.log",
                            "supralinux-clean-build-" + run_id,
                            manifest["builder"]["guest_ram_mib"],
                            manifest["builder"]["guest_vcpus"])
        (evidence / "qemu-command.json").write_text(json.dumps(args, indent=2) + "\n")
        with (evidence / "qemu.log").open("wb") as log:
            process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        agent = smoke.wait_agent(socket_path, process)
        report["timings_seconds"]["boot_and_agent"] = round(time.monotonic() - phase, 3)

        phase = time.monotonic()
        script = (ROOT / "tools/guest_clean_build.sh").read_bytes()
        agent.put("/run/supralinux-clean-build.sh", script)
        smoke.require(agent.get("/run/supralinux-clean-build.sh") == script,
                      "Guest build script readback mismatch")
        completed = agent.execute("/bin/bash", ["/run/supralinux-clean-build.sh"],
                                  timeout=manifest["builder"]["guest_timeout_seconds"])
        report["guest_exit_code"] = completed.get("exitcode")
        (evidence / "guest-shell.log").write_bytes(
            base64.b64decode(completed.get("out-data", ""), validate=True) +
            base64.b64decode(completed.get("err-data", ""), validate=True)
        )
        for remote, local in [
            ("/srv/supralinux-clean-build/run.log", evidence / "guest-run.log"),
            ("/srv/supralinux-clean-build/sbuild.log", evidence / "sbuild.log"),
            ("/srv/supralinux-clean-build/apt-update.log", evidence / "apt-update.log"),
            ("/srv/supralinux-clean-build/apt-simulation.log", evidence / "apt-simulation.log"),
            ("/srv/supralinux-clean-build/base-packages.txt", evidence / "base-packages.txt"),
            ("/srv/supralinux-clean-build/chroot-sha256.txt", evidence / "chroot-sha256.txt"),
            ("/srv/supralinux-clean-build/consumer-cmake.log", evidence / "consumer-cmake.log"),
            ("/srv/supralinux-clean-build/result.json", evidence / "guest-result.json"),
        ]:
            retrieve(agent, remote, local)
        if (evidence / "guest-result.json").is_file():
            guest = json.loads((evidence / "guest-result.json").read_text())
            report["guest_state"] = guest.get("state")
            report["guest_sbuild_exit_code"] = guest.get("sbuild_exit_code")
            report["sbuild_invoked"] = "sbuild_exit_code" in guest
            report["package_attempt_consumed"] = report["sbuild_invoked"]
        else:
            raise RuntimeError("Guest did not produce result.json")
        if guest.get("state") == "PASS" and completed.get("exitcode") != 0:
            raise RuntimeError("Guest reported PASS but the build script exited non-zero")
        if guest.get("state") == "PASS" and not report["sbuild_invoked"]:
            raise RuntimeError("Guest reported PASS without an sbuild attempt")
        build_dir = evidence / "build"
        if guest.get("artifacts"):
            build_dir.mkdir()
            for entry in guest["artifacts"]:
                target = build_dir / entry["name"]
                smoke.require(retrieve(agent, "/srv/supralinux-clean-build/out/" + entry["name"], target,
                                       limit=512 * 1024 * 1024),
                              "Could not retrieve build artifact: " + entry["name"])
                smoke.require(digest(target) == entry["sha256"] and target.stat().st_size == entry["bytes"],
                              "Retrieved build artifact differs: " + entry["name"])
            report["build_artifacts_retrieved"] = len(guest["artifacts"])
        if guest.get("state") == "PASS":
            verified = verify_build_outputs(build_dir, guest, manifest, source)
            if manifest.get("verification", {}).get("consumer"):
                smoke.require(guest.get("consumer_smoke") == "PASS",
                              "Guest consumer smoke did not pass")
            retained_artifacts = []
            for artifact in verified["debs"]:
                artifact_hash = digest(artifact)
                retained = WORKSPACE / "artifacts/sha256" / artifact_hash / artifact.name
                if not retained.exists():
                    retained.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(artifact, retained)
                    retained.chmod(0o444)
                smoke.require(digest(retained) == artifact_hash, "Retained build artifact changed")
                retained_artifacts.append({"path": str(retained), "sha256": artifact_hash})
            report["build"] = {"deb": verified["deb"].name, "deb_sha256": verified["sha256"],
                               "debs": [dict(item, name=path.name) for item, path in
                                        zip(retained_artifacts, verified["debs"])],
                               "buildinfo_sha256": verified["buildinfo_sha256"],
                               "changes_sha256": verified["changes_sha256"],
                               "consumer_smoke": guest.get("consumer_smoke", "not-run")}
            report["artifact"] = next(item for item in retained_artifacts
                                      if Path(item["path"]).name == verified["deb"].name)
            report["artifacts"] = retained_artifacts
            report["state"] = "PASS"
        else:
            report["state"] = guest.get("state", "FAIL")
            report["error"] = guest.get("error") or "guest build did not pass"
        report["timings_seconds"]["guest_build"] = round(time.monotonic() - phase, 3)
    except Exception as error:
        report["error"] = str(error)
    finally:
        phase = time.monotonic()
        report["cleanup"] = smoke.stop_guest(process, agent)
        if report["cleanup"]["process_absent"]:
            overlay.unlink(missing_ok=True)
            socket_path.unlink(missing_ok=True)
            (runtime / "inputs.img").unlink(missing_ok=True)
            try:
                runtime.rmdir()
            except OSError:
                pass
        shutil.rmtree(staging, ignore_errors=True)
        try:
            (WORKSPACE / "cache/clean-build" / run_id).rmdir()
        except OSError:
            pass
        report["cleanup"]["overlay_absent"] = not overlay.exists()
        report["cleanup"]["run_directory_absent"] = not runtime.exists()
        if base.exists():
            report["base_unchanged"] = digest(base) == manifest["base_image"]["sha256"]
        if (not all(report["cleanup"][key] for key in
                    ["process_absent", "overlay_absent", "run_directory_absent"])
                or report.get("base_unchanged") is not True):
            report["state"] = "INFRA_INVALID"
        report["timings_seconds"]["cleanup_and_parent_check"] = round(time.monotonic() - phase, 3)
        report["timings_seconds"]["total"] = round(time.monotonic() - started, 3)
        evidence_files = {str(p.relative_to(evidence)): digest(p)
                          for p in sorted(evidence.rglob("*")) if p.is_file()}
        report["files_sha256"] = evidence_files
        (evidence / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"state": report["state"], "evidence": str(evidence),
                          "error": report.get("error"), "timings_seconds": report["timings_seconds"],
                          "cleanup": report["cleanup"], "artifact": report.get("artifact")}, indent=2))
    return int(report["state"] != "PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, help="alternate pinned clean-build manifest")
    args = parser.parse_args()

    def interrupted(signum, frame):
        raise KeyboardInterrupt(f"Interrupted by signal {signum}")

    for signum in [signal.SIGTERM, signal.SIGHUP]:
        signal.signal(signum, interrupted)
    ensure_workspace()
    lock_path = WORKSPACE / "cache/clean-build.lock"
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("BLOCKED: another local clean build owns the execution slot")
        return build(args.manifest)


if __name__ == "__main__":
    raise SystemExit(main())
