import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("clean_build", ROOT / "tools/clean_build.py")
CLEAN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLEAN)


def sha(data=b"x"):
    return hashlib.sha256(data).hexdigest()


class CleanBuildTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        base = Path(self.directory.name)
        self.repo = base / "repo"
        self.workspace = base / "workspace"
        (self.repo / "packages/demo/debian").mkdir(parents=True)
        (self.repo / "packages/demo/debian/control").write_text(
            "Source: demo\nBuild-Depends: debhelper-compat (= 13)\n"
        )
        self.base_image = self.workspace / "artifacts/images/base.qcow2"
        self.base_image.parent.mkdir(parents=True)
        self.base_image.write_bytes(b"base")
        self.rootfs = self.workspace / "artifacts/rootfs/rootfs.tar"
        self.rootfs.parent.mkdir(parents=True)
        self.rootfs.write_bytes(b"rootfs")
        self.dep_sha = sha(b"dep")
        self.dep = self.workspace / "deps" / self.dep_sha / "demo.deb"
        self.dep.parent.mkdir(parents=True)
        self.dep.write_bytes(b"dep")
        self.manifest_path = self.workspace / "manifest.json"
        self.manifest_path.write_text(json.dumps(self.manifest()) + "\n")
        self.saved_root, self.saved_workspace = CLEAN.ROOT, CLEAN.WORKSPACE
        CLEAN.ROOT, CLEAN.WORKSPACE = self.repo, self.workspace

    def tearDown(self):
        CLEAN.ROOT, CLEAN.WORKSPACE = self.saved_root, self.saved_workspace
        self.directory.cleanup()

    def manifest(self):
        return {
            "schema": 1,
            "scope": "offline-clean-sbuild-build",
            "package": "demo",
            "version": "1.0.0",
            "architecture": "all",
            "source": {
                "kind": "native",
                "path": "packages/demo",
                "original_commit": "a" * 40,
                "dsc_name": "demo_1.0.0.dsc",
                "declared_build_depends": "debhelper-compat (= 13)",
            },
            "base_image": {
                "path": "artifacts/images/base.qcow2",
                "sha256": sha(b"base"),
                "format": "qcow2",
            },
            "rootfs": {
                "path": "artifacts/rootfs/rootfs.tar",
                "sha256": sha(b"rootfs"),
                "installed_package_count": 1,
            },
            "build_dependencies": {
                "declared": "debhelper-compat (= 13)",
                "source_evidence": "deps",
                "packages": [{
                    "name": "demo", "version": "1.0.0", "architecture": "all",
                    "filename": "demo.deb", "sha256": self.dep_sha,
                }],
            },
            "builder": {
                "sbuild_version": "0.91.2ubuntu3",
                "chroot_mode": "unshare",
                "distribution": "resolute",
                "architecture": "amd64",
                "guest_ram_mib": 2048,
                "guest_vcpus": 2,
                "guest_network": "none; loopback only",
                "guest_timeout_seconds": 1800,
            },
            "expected_binaries": [{"package": "demo", "architecture": "all"}],
            "verification": {"expected_paths": ["/usr/bin/demo"]},
        }

    def write(self, manifest):
        self.manifest_path.write_text(json.dumps(manifest) + "\n")
        return self.manifest_path

    def test_manifest_accepts_relative_workspace_paths(self):
        manifest = CLEAN.load_manifest(self.manifest_path)
        self.assertEqual(manifest["package"], "demo")
        self.assertEqual(manifest["builder"]["chroot_mode"], "unshare")
        self.assertEqual(manifest["builder"]["guest_timeout_seconds"], 1800)

    def test_manifest_timeout_defaults_when_missing(self):
        manifest = self.manifest()
        del manifest["builder"]["guest_timeout_seconds"]
        loaded = CLEAN.load_manifest(self.write(manifest))
        self.assertEqual(loaded["builder"]["guest_timeout_seconds"], CLEAN.DEFAULT_GUEST_TIMEOUT)

    def test_manifest_rejects_a_network_and_duplicate_dependencies(self):
        manifest = self.manifest()
        manifest["builder"]["guest_network"] = "user"
        with self.assertRaisesRegex(ValueError, "network"):
            CLEAN.load_manifest(self.write(manifest))
        manifest = self.manifest()
        manifest["build_dependencies"]["packages"].append(
            dict(manifest["build_dependencies"]["packages"][0])
        )
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            CLEAN.load_manifest(self.write(manifest))

    def test_manifest_rejects_unsafe_source_and_missing_inputs(self):
        manifest = self.manifest()
        manifest["source"]["path"] = "../outside"
        with self.assertRaisesRegex(ValueError, "Unsafe source path"):
            CLEAN.load_manifest(self.write(manifest))
        manifest = self.manifest()
        self.base_image.unlink()
        with self.assertRaisesRegex(ValueError, "Missing input"):
            CLEAN.load_manifest(self.write(manifest))

    def test_qemu_has_a_read_only_input_disk_and_no_network(self):
        args = CLEAN.qemu_command(Path("/run/disk.qcow2"), Path("/run/inputs.img"),
                                  Path("/run/agent.sock"), Path("/run/console"), "clean")
        self.assertEqual(args[args.index("-nic") + 1], "none")
        drives = [args[index + 1] for index, value in enumerate(args) if value == "-drive"]
        self.assertEqual(len(drives), 2)
        input_drive = next(drive for drive in drives if "id=inputs" in drive)
        self.assertIn("readonly=on", input_drive)
        self.assertIn("format=raw", input_drive)
        for forbidden in ["-netdev", "-virtfs", "-fsdev", "-snapshot", "-daemonize"]:
            self.assertNotIn(forbidden, args)
        self.assertFalse(any("tcg" in arg or "hostfwd" in arg for arg in args))

    def test_qemu_uses_the_manifest_resources(self):
        args = CLEAN.qemu_command(Path("/run/disk.qcow2"), Path("/run/inputs.img"),
                                  Path("/run/agent.sock"), Path("/run/console"), "clean",
                                  4096, 4)
        self.assertEqual(args[args.index("-m") + 1], "4096")
        self.assertEqual(args[args.index("-smp") + 1], "4")
        for values in [(512, 2), (2048, 0), (2048, 9)]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                CLEAN.qemu_command(Path("/run/disk.qcow2"), Path("/run/inputs.img"),
                                   Path("/run/agent.sock"), Path("/run/console"), "clean", *values)

    def test_qemu_rejects_option_injection(self):
        for path in [Path("/run/disk,readonly=off"), Path("/run/disk\nbad")]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                CLEAN.qemu_command(path, Path("/run/inputs.img"), Path("/run/agent.sock"),
                                   Path("/run/console"), "clean")

    def test_control_fields_preserve_multiline_installed_dependencies(self):
        fields = CLEAN.control_fields(
            "Source: demo\n"
            "Installed-Build-Depends: build-essential (= 1),\n"
            " debhelper (= 13.31ubuntu1),\n"
            " libc6 (= 1)\n"
            "Checksums-Sha256:\n"
            " " + "a" * 64 + " 10 demo.deb\n"
        )
        self.assertIn("build-essential", fields["Installed-Build-Depends"])
        self.assertIn("debhelper", fields["Installed-Build-Depends"])
        self.assertEqual(fields["Checksums-Sha256"], "a" * 64 + " 10 demo.deb")


if __name__ == "__main__":
    unittest.main()
