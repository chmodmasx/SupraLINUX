import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("import_framework", ROOT / "tools/import_framework.py")
IMPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORT)


class ImportFrameworkTests(unittest.TestCase):
    def test_control_is_sanitized_without_losing_build_depends(self):
        text = (
            "Source: kf6-demo\n"
            "Maintainer: Ubuntu Developers <ubuntu@example.invalid>\n"
            "XSBC-Original-Maintainer: Debian <debian@example.invalid>\n"
            "Uploaders: A <a@example.invalid>,\n"
            "           B <b@example.invalid>\n"
            "Build-Depends: debhelper-compat (= 13),\n"
            "               cmake (>= 3.16~),\n"
            "               extra-cmake-modules (>= 6.24.0~),\n"
            "Testsuite: autopkgtest\n"
            "Standards-Version: 4.7.0\n\n"
            "Package: libdemo\n"
            "Architecture: any\n"
            "Description: demo\n"
        )
        result = IMPORT.sanitize_control(text)
        self.assertIn("Maintainer: SupraLINUX Project", result)
        self.assertNotIn("Uploaders", result)
        self.assertNotIn("XSBC-Original-Maintainer", result)
        self.assertNotIn("Testsuite", result)
        self.assertIn("extra-cmake-modules (>= 6.24.0~)\nStandards-Version", result)

    def test_rules_disable_qch_only(self):
        self.assertEqual(
            IMPORT.sanitize_rules("dh_auto_configure -- -DBUILD_QCH=ON -DBUILD_TESTING=ON"),
            "dh_auto_configure -- -DBUILD_QCH=OFF -DBUILD_TESTING=ON",
        )

    def test_binary_architectures_are_mapped_to_the_build_architecture(self):
        control = (
            "Package: libdemo-data\nArchitecture: all\n\n"
            "Package: libdemo-dev\nArchitecture: any\n\n"
            "Package: libdemo6\nArchitecture: linux-any\n"
        )
        self.assertEqual(IMPORT.package_architectures(control), [
            ("libdemo-data", "all"), ("libdemo-dev", "amd64"), ("libdemo6", "amd64"),
        ])

    def test_copy_packaging_drops_unsupported_ci_and_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            (source / "control").write_text("Source: demo\nMaintainer: old\nBuild-Depends: debhelper-compat (= 13)\n")
            (source / "rules").write_text("#!/usr/bin/make -f\n%:\n\tdh $@\n")
            (source / "salsa-ci.yml").write_text("stages: []\n")
            (source / "tests").mkdir()
            (source / "salsa").mkdir()
            IMPORT.copy_packaging(source, target)
            self.assertTrue((target / "control").is_file())
            self.assertFalse((target / "salsa-ci.yml").exists())
            self.assertFalse((target / "tests").exists())
            self.assertFalse((target / "salsa").exists())


    def test_manifest_uses_relative_workspace_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            base = workspace / "artifacts/images/base.qcow2"
            base.parent.mkdir(parents=True)
            base.write_bytes(b"base")
            rootfs = workspace / "artifacts/rootfs/rootfs.tar"
            rootfs.parent.mkdir(parents=True)
            rootfs.write_bytes(b"rootfs")
            manifest_path = root / "manifest.json"
            args = SimpleNamespace(
                upstream=Path("kf6-demo-6.24.0.tar.xz"),
                upstream_version="6.24.0",
                upstream_url="https://example.invalid/kf6-demo-6.24.0.tar.xz",
                dsc_name=None,
                orig_filename=None,
                source_name="kf6-demo",
                version="6.24.0-0supralinux1",
                main_package="libdemo6",
                package_dir="packages/demo",
                base_image=base,
                base_image_sha256=hashlib.sha256(b"base").hexdigest(),
                rootfs=rootfs,
                sbuild_version="0.91.2ubuntu3",
                guest_ram_mib=4096,
                guest_vcpus=4,
                timeout=5400,
                expected_path=["/usr/lib/libdemo.so.6"],
                manifest=str(manifest_path),
            )
            record = {
                "source_evidence": "deps",
                "generated_at": "2026-11-18T00:00:00+00:00",
                "sources": {"sha256": "a" * 64},
                "packages": [],
                "rootfs": {"installed_package_count": 123},
            }
            control = "Package: libdemo6\nArchitecture: any\n"
            saved = IMPORT.WORKSPACE
            try:
                IMPORT.WORKSPACE = workspace
                manifest = IMPORT.write_manifest(
                    args, None, record, "debhelper-compat (= 13)", "b" * 64, control
                )
            finally:
                IMPORT.WORKSPACE = saved
            self.assertEqual(manifest["base_image"]["path"], "artifacts/images/base.qcow2")
            self.assertEqual(manifest["rootfs"]["path"], "artifacts/rootfs/rootfs.tar")
            self.assertEqual(manifest["rootfs"]["installed_package_count"], 123)
            self.assertEqual(manifest["expected_binaries"],
                             [{"package": "libdemo6", "architecture": "amd64"}])
            self.assertEqual(json.loads(manifest_path.read_text()), manifest)


if __name__ == "__main__":
    unittest.main()
