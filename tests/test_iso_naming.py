import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ISO_LIB = ROOT / "tools/live/iso-lib.sh"


def run_shell(script):
    return subprocess.run(
        ["sh", "-c", f'. "{ISO_LIB}"\n{script}'],
        capture_output=True,
        text=True,
    )


class IsoNamingTests(unittest.TestCase):
    def test_candidate_name_has_version_timestamp_and_commit(self):
        result = run_shell(
            "iso_candidate_name 1.0.0 aurora 20261120T044138Z c292031"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            "supralinux-aurora-1.0.0-amd64-20261120T044138Z-gc292031.iso",
        )

    def test_candidate_name_follows_the_product_version(self):
        result = run_shell(
            "iso_candidate_name 1.1.0 aurora 20270101T000000Z abcdef1"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            "supralinux-aurora-1.1.0-amd64-20270101T000000Z-gabcdef1.iso",
        )

    def test_candidate_path_reads_version_and_codename_from_os_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            os_release = root / "usr/lib/os-release"
            os_release.parent.mkdir(parents=True)
            os_release.write_text(
                'SUPRALINUX_VERSION="1.0.1"\n'
                'SUPRALINUX_CODENAME="aurora"\n'
            )
            result = run_shell(
                f'iso_candidate_path "{root}" "{ROOT}" "{root}"'
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            pattern = (
                re.escape(str(root))
                + r"/supralinux-aurora-1\.0\.1-amd64-"
                + r"\d{8}T\d{6}Z-g[0-9a-f]{7,}\.iso"
            )
            self.assertRegex(result.stdout.strip(), r"^" + pattern + r"$")

    def test_candidate_path_rejects_a_rootfs_without_product_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            os_release = root / "usr/lib/os-release"
            os_release.parent.mkdir(parents=True)
            os_release.write_text('PRETTY_NAME="Ubuntu 26.04"\n')
            result = run_shell(
                f'iso_candidate_path "{root}" "{ROOT}" "{root}"'
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SUPRALINUX_VERSION", result.stderr)

    def test_build_scripts_use_candidate_names_by_default(self):
        for name in ["build-iso.sh", "secureboot-efi.sh"]:
            with self.subTest(name=name):
                text = (ROOT / "tools/live" / name).read_text()
                self.assertIn("iso_candidate_path", text)
                self.assertIn("SUPRALINUX_ISO_NAME", text)


if __name__ == "__main__":
    unittest.main()
