import base64
import datetime
import hashlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package_smoke", ROOT / "tools/package_smoke.py")
SMOKE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SMOKE)
GUEST_SPEC = importlib.util.spec_from_file_location("guest_smoke", ROOT / "tools/guest_package_smoke.py")
GUEST = importlib.util.module_from_spec(GUEST_SPEC)
GUEST_SPEC.loader.exec_module(GUEST)


class PackageSmokeTests(unittest.TestCase):
    def manifest(self, root):
        test = root / "tests/fixture"
        test.parent.mkdir(parents=True, exist_ok=True)
        test.write_text("#!/bin/sh\nexit 0\n")
        return {
            "schema": 1,
            "scope": "offline-artifact-installation-smoke",
            "package": "demo",
            "version": "1.0.0",
            "architecture": "all",
            "artifact": {"path": "artifacts/demo.deb", "sha256": "a" * 64},
            "base_image": {"path": "images/base.qcow2", "sha256": "b" * 64, "format": "qcow2"},
            "test": {"path": "tests/fixture", "sha256": SMOKE.digest(test)},
            "installed_files": {"/usr/bin/demo": "c" * 64},
            "negative_test": {"path": "/usr/share/demo/proof"},
        }

    def test_manifest_accepts_a_pinned_local_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            path = root / "manifest.json"
            path.write_text(json.dumps(manifest))
            loaded = SMOKE.load_manifest(root=root, path=path)
            self.assertEqual(loaded["package"], "demo")
            self.assertEqual(loaded["test"]["sha256"], SMOKE.digest(root / "tests/fixture"))

    def test_manifest_rejects_an_unsafe_test_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            manifest["test"]["path"] = "../outside"
            path = root / "manifest.json"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Unsafe test path"):
                SMOKE.load_manifest(root=root, path=path)

    def test_manifest_rejects_a_changed_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            path = root / "manifest.json"
            path.write_text(json.dumps(manifest))
            (root / "tests/fixture").write_text("changed")
            with self.assertRaisesRegex(ValueError, "Imported test changed"):
                SMOKE.load_manifest(root=root, path=path)

    def test_restore_is_verified_independent_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / "source", root / "retained/copy"
            source.write_bytes(b"original bytes")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertFalse(SMOKE.restore_file(source, target, digest))
            self.assertNotEqual(source.stat().st_ino, target.stat().st_ino)
            self.assertEqual(target.stat().st_mode & 0o777, 0o444)
            self.assertTrue(SMOKE.restore_file(source, target, digest))
            source.write_bytes(b"source changed")
            self.assertEqual(target.read_bytes(), b"original bytes")

    def test_bad_source_is_not_admitted_or_left_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / "source", root / "retained/copy"
            source.write_bytes(b"wrong")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                SMOKE.restore_file(source, target, "0" * 64)
            self.assertFalse(target.exists())
            self.assertFalse(target.with_name("copy.partial").exists())

    def test_conflicting_destination_and_symlinks_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / "source", root / "copy"
            source.write_bytes(b"source")
            target.write_bytes(b"keep")
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                SMOKE.restore_file(source, target, "0" * 64)
            self.assertEqual(target.read_bytes(), b"keep")
            target.unlink()
            target.symlink_to(source)
            with self.assertRaisesRegex(ValueError, "symlink"):
                SMOKE.restore_file(source, target, SMOKE.digest(source))

    def test_release_records_exact_index_hashes_and_sizes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["Packages", "Packages.gz"]:
                (root / name).write_bytes(name.encode())
            text = SMOKE.release_metadata(root, datetime.datetime(2026, 10, 28, tzinfo=datetime.timezone.utc))
            for name in ["Packages", "Packages.gz"]:
                self.assertIn(f" {SMOKE.digest(root / name)} {(root / name).stat().st_size} {name}", text)
            self.assertIn("disposable-test-only", text)

    def test_qemu_has_no_network_shared_mount_or_software_fallback(self):
        args = SMOKE.qemu_command(Path("/owned/run/disk.qcow2"), Path("/owned/run/agent.sock"),
                                  Path("/owned/evidence/serial.log"), "smoke")
        self.assertEqual(args[args.index("-nic") + 1], "none")
        self.assertIn("q35,accel=kvm", args)
        for item in ["-netdev", "-virtfs", "-fsdev", "-daemonize", "-snapshot"]:
            self.assertNotIn(item, args)
        self.assertFalse(any("tcg" in arg or "hostfwd" in arg for arg in args))

    def test_qemu_option_injection_and_long_socket_are_rejected(self):
        for path in [Path("/run/disk,readonly=off"), Path("/run/disk\nbad")]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                SMOKE.qemu_command(path, Path("/run/a.sock"), Path("/run/log"), "smoke")
        with self.assertRaisesRegex(ValueError, "too long"):
            SMOKE.qemu_command(Path("/run/disk"), Path("/" + "a" * 110), Path("/run/log"), "smoke")

    def test_apt_uses_only_owned_local_source_and_pinned_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = GUEST.apt_options(root, root / "repository", "valid")
            self.assertIn("Dir::Etc::sourceparts=-", args)
            self.assertIn("Acquire::AllowInsecureRepositories=false", args)
            self.assertNotIn("--allow-unauthenticated", args)
            source = (root / "apt/valid.list").read_text()
            self.assertIn("file:", source)
            self.assertIn("signed-by=", source)
            self.assertNotIn("trusted=yes", source)
            self.assertNotIn("http", source)

    def agent_without_socket(self):
        return object.__new__(SMOKE.Agent)

    def test_partial_guest_write_is_rejected_and_handle_closed(self):
        agent = self.agent_without_socket()
        agent.call = Mock(side_effect=[11, {"count": 2}, {}])
        with self.assertRaisesRegex(ValueError, "Partial"):
            agent.put("/owned/file", b"four")
        self.assertEqual(agent.call.call_args.args, ("guest-file-close",))

    def test_guest_read_requires_matching_byte_count(self):
        agent = self.agent_without_socket()
        agent.call = Mock(side_effect=[11, {"count": 9, "buf-b64": base64.b64encode(b"x").decode(), "eof": True}, {}])
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            agent.get("/owned/file")
        self.assertEqual(agent.call.call_args.args, ("guest-file-close",))

    def test_guest_exec_refuses_truncated_evidence(self):
        agent = self.agent_without_socket()
        agent.call = Mock(side_effect=[{"pid": 22}, {"exited": True, "exitcode": 0, "out-truncated": True}])
        with self.assertRaisesRegex(ValueError, "truncated"):
            agent.execute("/bin/true", [])

    def test_guest_response_is_bounded_and_accepts_sync_delimiter(self):
        agent = self.agent_without_socket()
        agent.stream = io.BytesIO(b'\xff{"return": 1}\n')
        self.assertEqual(agent.receive(), {"return": 1})
        agent.stream = io.BytesIO(b'{"return": 1}')
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            agent.receive()

    def test_cleanup_stops_only_owned_process_when_guest_shutdown_fails(self):
        process = Mock()
        process.poll.side_effect = [None, None, -15]
        agent = Mock()
        agent.send.side_effect = OSError("disconnected")
        result = SMOKE.stop_guest(process, agent)
        process.terminate.assert_called_once()
        process.kill.assert_not_called()
        agent.close.assert_called_once()
        self.assertTrue(result["process_absent"])
        self.assertEqual(result["method"], "terminate-owned-process")

    def test_guest_shutdown_does_not_wait_for_a_nonexistent_agent_reply(self):
        process = Mock()
        process.poll.side_effect = [None, 0, 0]
        agent = Mock()
        result = SMOKE.stop_guest(process, agent)
        agent.send.assert_called_once_with("guest-shutdown", {"mode": "powerdown"})
        agent.call.assert_not_called()
        process.terminate.assert_not_called()
        self.assertTrue(result["process_absent"])

    def test_never_marks_new_package_build_certified(self):
        source = (ROOT / "tools/package_smoke.py").read_text()
        self.assertIn('"sbuild_invoked": False', source)
        self.assertIn('"new_package_build_certification": False', source)
        self.assertNotIn("api.github.com", source)
        self.assertNotIn("sudo", source)


if __name__ == "__main__":
    unittest.main()
