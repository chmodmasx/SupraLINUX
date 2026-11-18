#!/usr/bin/env python3
"""Restore one pinned artifact, test signed APT installation offline, clean up."""
import argparse
import base64
import datetime
import fcntl
import gzip
import hashlib
import json
import os
import re
import signal
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = Path(os.environ.get("SUPRALINUX_WORKSPACE", ROOT.parent / "SupraLINUX-workspace")).expanduser().resolve()
GUEST_RAM_MIB = 3072


def workspace_path(value):
    path = Path(value).expanduser()
    return (WORKSPACE / path).resolve() if not path.is_absolute() else path.resolve()


def ensure_workspace():
    for name in ["cache", "kvm/runs", "kvm/bases", "artifacts/sha256", "evidence"]:
        (WORKSPACE / name).mkdir(parents=True, exist_ok=True)



def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def command(args, cwd=None, binary=False, timeout=120):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=not binary, timeout=timeout)
    if result.returncode:
        error = result.stderr.decode(errors="replace") if binary else result.stderr
        raise RuntimeError(f"{Path(args[0]).name} failed ({result.returncode}): {error[-2000:]}")
    return result.stdout


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_manifest(root=ROOT, path=None):
    manifest_path = Path(path) if path else root / "manifests/package-smoke.json"
    manifest = json.loads(manifest_path.read_text())
    require(manifest["schema"] == 1 and manifest["scope"] == "offline-artifact-installation-smoke", "Wrong smoke scope")
    require(re.fullmatch(r"[a-z0-9][a-z0-9+.-]+", manifest["package"]), "Invalid package name")
    require(manifest["base_image"]["format"] == "qcow2", "Expected a pinned qcow2 image")
    for item in [manifest["artifact"], manifest["base_image"], manifest["test"], *manifest.get("repository_artifacts", [])]:
        require(re.fullmatch(r"[a-f0-9]{64}", item["sha256"]), "Invalid SHA-256")
    test = root / manifest["test"]["path"]
    require(test.resolve().is_relative_to(root.resolve()) and not test.is_symlink(), "Unsafe test path")
    require(digest(test) == manifest["test"]["sha256"], "Imported test changed")
    return manifest


def restore_file(source, target, expected):
    require(not target.is_symlink(), "Refusing a symlink destination")
    if target.exists():
        require(target.is_file() and digest(target) == expected, "Conflicting retained file: " + str(target))
        return True
    require(source.is_file() and not source.is_symlink(), "Missing regular input: " + str(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".partial")
    require(not temporary.exists(), "Unresolved partial import: " + str(temporary))
    try:
        shutil.copyfile(source, temporary)
        require(digest(temporary) == expected, "Input digest mismatch: " + str(source))
        temporary.chmod(0o444)
        temporary.rename(target)
    finally:
        temporary.unlink(missing_ok=True)
    return False


def release_metadata(repository, now):
    rows = ["Origin: SupraLINUX-Local-Smoke", "Label: disposable-test-only",
            "Suite: local-smoke", "Codename: local-smoke", "Architectures: amd64 all",
            "Date: " + now.strftime("%a, %d %b %Y %H:%M:%S +0000"), "SHA256:"]
    for name in ["Packages", "Packages.gz"]:
        path = repository / name
        rows.append(f" {digest(path)} {path.stat().st_size} {name}")
    return "\n".join(rows) + "\n"


def signed_repository(artifacts, output):
    if isinstance(artifacts, (str, Path)):
        artifacts = [artifacts]
    artifacts = [Path(artifact) for artifact in artifacts]
    require(artifacts, "At least one repository artifact is required")
    names = [artifact.name for artifact in artifacts]
    require(len(names) == len(set(names)), "Repository artifact names must be unique")
    output.mkdir()
    for artifact in artifacts:
        require(artifact.is_file() and not artifact.is_symlink(), "Missing repository artifact: " + str(artifact))
        shutil.copyfile(artifact, output / artifact.name)
    packages = command(["dpkg-scanpackages", "--multiversion", ".", "/dev/null"], cwd=output)
    (output / "Packages").write_text(packages)
    (output / "Packages.gz").write_bytes(gzip.compress(packages.encode(), mtime=0))
    (output / "Release").write_text(release_metadata(output, datetime.datetime.now(datetime.timezone.utc)))
    # The private test key never enters the evidence tree or a persistent keyring.
    with tempfile.TemporaryDirectory(prefix="supra-key-") as directory:
        home = Path(directory)
        gpg = ["gpg", "--batch", "--yes", "--homedir", str(home)]
        try:
            command(gpg + ["--pinentry-mode", "loopback", "--passphrase", "", "--quick-generate-key",
                           "SupraLINUX smoke ONLY <smoke@supralinux.invalid>", "ed25519", "sign", "1d"])
            records = command(gpg + ["--with-colons", "--list-keys"])
            fingerprints = [line.split(":")[9] for line in records.splitlines() if line.startswith("fpr:")]
            require(len(fingerprints) == 1, "Ambiguous ephemeral signing key")
            fingerprint = fingerprints[0]
            public = command(gpg + ["--export", fingerprint], binary=True)
            (output.parent / "archive-key.gpg").write_bytes(public)
            command(gpg + ["--local-user", fingerprint, "--digest-algo", "SHA256", "--output",
                           str(output / "InRelease"), "--clearsign", str(output / "Release")])
            command(gpg + ["--local-user", fingerprint, "--digest-algo", "SHA256", "--armor", "--output",
                           str(output / "Release.gpg"), "--detach-sign", str(output / "Release")])
            command(["gpgv", "--homedir", str(home), "--keyring", str(output.parent / "archive-key.gpg"),
                     str(output / "InRelease")])
        finally:
            subprocess.run(["gpgconf", "--homedir", str(home), "--kill", "gpg-agent"], capture_output=True, timeout=10)
    return fingerprint


class Agent:
    def __init__(self, path):
        self.connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.connection.settimeout(5)
        self.stream = None
        try:
            self.connection.connect(str(path))
            self.stream = self.connection.makefile("rb")
            marker = int(time.time_ns() % (2**31))
            self.connection.sendall(b"\xff")
            self.send("guest-sync-delimited", {"id": marker})
            for _ in range(8):
                if self.receive().get("return") == marker:
                    break
            else:
                raise RuntimeError("Guest-agent synchronization failed")
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.stream:
            self.stream.close()
        self.connection.close()

    def send(self, name, arguments):
        self.connection.sendall(json.dumps({"execute": name, "arguments": arguments}).encode() + b"\n")

    def receive(self):
        raw = self.stream.readline(2 * 1024 * 1024)
        require(raw and raw.endswith(b"\n"), "Incomplete/oversized guest-agent response")
        return json.loads(raw.lstrip(b"\xff"))

    def call(self, name, **arguments):
        self.send(name, arguments)
        response = self.receive()
        if "error" in response:
            raise RuntimeError(f"Guest agent rejected {name}: {response['error'].get('desc', 'unknown error')}")
        return response["return"]

    def put(self, path, data):
        handle = self.call("guest-file-open", path=path, mode="wb")
        try:
            for start in range(0, len(data), 48 * 1024):
                chunk = data[start:start + 48 * 1024]
                written = self.call("guest-file-write", handle=handle,
                                    **{"buf-b64": base64.b64encode(chunk).decode(), "count": len(chunk)})
                require(written["count"] == len(chunk), "Partial guest-file-write")
            self.call("guest-file-flush", handle=handle)
        finally:
            self.call("guest-file-close", handle=handle)

    def get(self, path, limit=32 * 1024 * 1024):
        handle = self.call("guest-file-open", path=path, mode="rb")
        data = bytearray()
        try:
            while True:
                result = self.call("guest-file-read", handle=handle, count=64 * 1024)
                chunk = base64.b64decode(result.get("buf-b64", ""), validate=True)
                require(result["count"] == len(chunk), "Guest-file-read count mismatch")
                data.extend(chunk)
                require(len(data) <= limit, "Guest output exceeds evidence budget")
                if result["eof"]:
                    return bytes(data)
                require(chunk, "Guest-file-read made no progress")
        finally:
            self.call("guest-file-close", handle=handle)

    def execute(self, path, args, timeout=180):
        pid = self.call("guest-exec", path=path, arg=args, **{"capture-output": True})["pid"]
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.call("guest-exec-status", pid=pid)
            if result["exited"]:
                require(not result.get("out-truncated") and not result.get("err-truncated"), "Guest output truncated")
                return result
            time.sleep(0.2)
        raise TimeoutError("Guest command exceeded the smoke time budget")


def qemu_command(overlay, agent_socket, console, name):
    for path in [overlay, agent_socket, console]:
        require(not any(char in str(path) for char in [",", "\n", "\0"]), "Unsafe QEMU option path")
    require(len(str(agent_socket).encode()) < 100, "Unix socket path too long")
    return ["qemu-system-x86_64", "-name", name, "-machine", "q35,accel=kvm", "-cpu", "host",
            "-m", str(GUEST_RAM_MIB), "-smp", "2", "-nodefaults", "-display", "none", "-monitor", "none",
            "-nic", "none", "-drive", f"if=none,id=osdisk,file={overlay},format=qcow2",
            "-device", "virtio-blk-pci,drive=osdisk", "-device", "virtio-serial-pci",
            "-chardev", f"socket,path={agent_socket},server=on,wait=off,id=qga",
            "-device", "virtserialport,chardev=qga,name=org.qemu.guest_agent.0", "-serial", f"file:{console}"]


def wait_agent(path, process, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        require(process.poll() is None, "QEMU exited before the guest agent was ready")
        agent = None
        try:
            agent = Agent(path)
            probe = agent.execute("/usr/bin/test", ["-f", "/etc/os-release"], timeout=10)
            if probe.get("exitcode") == 0:
                return agent
            agent.close()
        except (OSError, ValueError, RuntimeError, TimeoutError):
            if agent is not None:
                agent.close()
        time.sleep(0.5)
    raise TimeoutError("Guest agent did not become ready")


def stop_guest(process, agent):
    method = "already-exited" if process is not None else "not-started"
    if process is not None and process.poll() is None:
        if agent is not None:
            try:
                method = "guest-powerdown"
                # Successful guest-shutdown deliberately has no agent reply.
                agent.send("guest-shutdown", {"mode": "powerdown"})
                process.wait(timeout=30)
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
                pass
        if process.poll() is None:
            method = "terminate-owned-process"
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                method = "kill-owned-process"
                process.kill()
                process.wait(timeout=10)
    if agent is not None:
        agent.close()
    return {"process_absent": process is None or process.poll() is not None, "method": method}


def smoke(manifest_path=None):
    require(os.geteuid() != 0, "Run on the host as an unprivileged KVM user, not root")
    require(not command(["git", "-C", str(ROOT), "status", "--porcelain"]).strip(), "Commit reviewed inputs before execution")
    manifest_file = Path(manifest_path).resolve() if manifest_path else ROOT / "manifests/package-smoke.json"
    manifest = load_manifest(path=manifest_file)
    for name in ["qemu-system-x86_64", "qemu-img", "dpkg-deb", "dpkg-scanpackages", "gpg", "gpgconf", "gpgv"]:
        require(shutil.which(name), "Missing existing tool: " + name)
    with open("/dev/kvm", "r+b", buffering=0) as device:
        require(fcntl.ioctl(device, 0xAE00, 0) == 12, "Unexpected KVM API")
    available = int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemAvailable:")))
    require(available >= (GUEST_RAM_MIB + 1024) * 1024,
            f"Not enough available RAM for a {GUEST_RAM_MIB} MiB guest plus host margin")
    ensure_workspace()
    require(not list((WORKSPACE / "kvm/runs").iterdir()), "Previous runtime state remains; inspect it before starting another VM")
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:12]
    evidence = WORKSPACE / "evidence/package-smoke" / run_id
    runtime = WORKSPACE / "kvm/runs" / run_id
    evidence.mkdir(parents=True, mode=0o700)
    runtime.mkdir(mode=0o700)
    overlay, socket_path = runtime / "disk.qcow2", runtime / "agent.sock"
    report = {"schema": 1, "scope": manifest["scope"], "state": "INFRA_INVALID", "run_id": run_id,
              "code_commit": command(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).strip(),
              "manifest_path": str(manifest_file), "manifest_sha256": digest(manifest_file),
              "sbuild_invoked": False, "new_package_build_certification": False,
              "host_network_modified": False, "timings_seconds": {}}
    started = time.monotonic()
    process = agent = None
    base = WORKSPACE / "kvm/bases" / (manifest["base_image"]["sha256"] + ".qcow2")
    try:
        phase = time.monotonic()
        require(shutil.disk_usage(WORKSPACE).free >= 15 * 1024**3, "Less than 15 GiB free: refuse image preparation")
        report["base_reused"] = restore_file(workspace_path(manifest["base_image"]["path"]), base, manifest["base_image"]["sha256"])
        info = json.loads(command(["qemu-img", "info", "--output=json", "-f", "qcow2", str(base)]))
        require(not info.get("backing-filename") and info["format"] == "qcow2", "Smoke base must be standalone qcow2")
        command(["qemu-img", "check", "-f", "qcow2", str(base)])
        report["base_sha256"] = manifest["base_image"]["sha256"]
        report["timings_seconds"]["base_preparation"] = round(time.monotonic() - phase, 3)
        phase = time.monotonic()
        artifact_source = workspace_path(manifest["artifact"]["path"])
        artifact = WORKSPACE / "artifacts/sha256" / manifest["artifact"]["sha256"] / artifact_source.name
        report["artifact_reused"] = restore_file(artifact_source, artifact, manifest["artifact"]["sha256"])
        identity = command(["dpkg-deb", "-f", str(artifact), "Package", "Version", "Architecture"])
        expected = f"Package: {manifest['package']}\nVersion: {manifest['version']}\nArchitecture: {manifest['architecture']}\n"
        require(identity == expected, "Retained binary identity mismatch")
        report["artifact_sha256"] = digest(artifact)
        repository_artifacts = {artifact: True}
        for item in manifest.get("repository_artifacts", []):
            source = workspace_path(item["path"])
            target = WORKSPACE / "artifacts/sha256" / item["sha256"] / source.name
            restore_file(source, target, item["sha256"])
            repository_artifacts[target] = True
        report["repository_artifact_count"] = len(repository_artifacts)
        report["test_key_fingerprint"] = signed_repository(list(repository_artifacts), evidence / "repository")
        (evidence / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        report["timings_seconds"]["artifact_and_repository"] = round(time.monotonic() - phase, 3)
        command(["qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b", str(base), str(overlay)])
        args = qemu_command(overlay, socket_path, evidence / "console.log", "supralinux-smoke-" + run_id)
        (evidence / "qemu-command.json").write_text(json.dumps(args, indent=2) + "\n")
        phase = time.monotonic()
        with (evidence / "qemu.log").open("wb") as log:
            process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        agent = wait_agent(socket_path, process)
        report["timings_seconds"]["boot_and_agent"] = round(time.monotonic() - phase, 3)
        phase = time.monotonic()
        result = agent.execute("/bin/mkdir", ["-p", "/run/supralinux-package-smoke/repository"])
        require(result.get("exitcode") == 0, "Guest workspace creation failed")
        files = {"manifest.json": evidence / "manifest.json", "archive-key.gpg": evidence / "archive-key.gpg",
                 "smoke": ROOT / manifest["test"]["path"], "probe.py": ROOT / "tools/guest_package_smoke.py"}
        files.update({"repository/" + p.name: p for p in (evidence / "repository").iterdir()})
        for relative, path in sorted(files.items()):
            target = "/run/supralinux-package-smoke/" + relative
            raw = path.read_bytes()
            agent.put(target, raw)
            require(agent.get(target, limit=512 * 1024 * 1024) == raw, "Guest input readback mismatch: " + relative)
        completed = agent.execute("/usr/bin/python3", ["/run/supralinux-package-smoke/probe.py"], timeout=240)
        output = base64.b64decode(completed.get("out-data", ""), validate=True)
        errors = base64.b64decode(completed.get("err-data", ""), validate=True)
        (evidence / "guest.log").write_bytes(output + errors)
        require(completed.get("exitcode") == 0, "Guest smoke failed; inspect retained guest.log")
        raw_result = agent.get("/run/supralinux-package-smoke/result.json")
        (evidence / "guest-result.json").write_bytes(raw_result)
        guest = json.loads(raw_result)
        require(guest["state"] == "PASS" and guest["interfaces"] == ["lo"], "Guest result scope mismatch")
        report["guest_result_sha256"] = digest(evidence / "guest-result.json")
        report["timings_seconds"]["transfer_and_tests"] = round(time.monotonic() - phase, 3)
        with tempfile.TemporaryDirectory(prefix="smoke-restore-", dir=WORKSPACE / "cache") as directory:
            restored = Path(directory) / artifact.name
            require(not restored.exists(), "Restore destination is not empty")
            shutil.copyfile(artifact, restored)
            require(digest(restored) == manifest["artifact"]["sha256"], "Empty-destination artifact restoration failed")
        report["empty_destination_restore"] = "PASS"
        report["state"] = "PASS"
    except Exception as error:
        report["error"] = str(error)
    finally:
        phase = time.monotonic()
        report["cleanup"] = stop_guest(process, agent)
        if report["cleanup"]["process_absent"]:
            overlay.unlink(missing_ok=True)
            socket_path.unlink(missing_ok=True)
            try:
                runtime.rmdir()
            except OSError:
                pass
        report["cleanup"]["overlay_absent"] = not overlay.exists()
        report["cleanup"]["run_directory_absent"] = not runtime.exists()
        if base.exists():
            report["base_unchanged"] = digest(base) == manifest["base_image"]["sha256"]
        if not all(report["cleanup"][key] for key in ["process_absent", "overlay_absent", "run_directory_absent"]) or report.get("base_unchanged") is not True:
            report["state"] = "INFRA_INVALID"
        report["timings_seconds"]["cleanup_and_parent_check"] = round(time.monotonic() - phase, 3)
        report["timings_seconds"]["total"] = round(time.monotonic() - started, 3)
        hashes = {str(p.relative_to(evidence)): digest(p) for p in sorted(evidence.rglob("*")) if p.is_file()}
        report["files_sha256"] = hashes
        (evidence / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"state": report["state"], "evidence": str(evidence), "error": report.get("error"),
                          "timings_seconds": report["timings_seconds"], "cleanup": report["cleanup"]}, indent=2))
    return int(report["state"] != "PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, help="alternate pinned smoke manifest")
    args = parser.parse_args()

    def interrupted(signum, frame):
        raise KeyboardInterrupt(f"Interrupted by signal {signum}")

    for signum in [signal.SIGTERM, signal.SIGHUP]:
        signal.signal(signum, interrupted)
    ensure_workspace()
    lock_path = WORKSPACE / "cache/package-smoke.lock"
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("BLOCKED: another local package smoke owns the execution slot")
        return smoke(args.manifest)


if __name__ == "__main__":
    raise SystemExit(main())
