import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "manifests/iso-1.0.0.json").read_text())


class IsoOneZeroTests(unittest.TestCase):
    def test_iso_is_validated_but_not_a_release(self):
        self.assertEqual(DATA["scope"], "iso-release-validation")
        self.assertEqual(DATA["status"], "PASS")
        self.assertFalse(DATA["release_ready"])
        self.assertIn("LUKS2", " ".join(DATA["limitations"]))

    def test_iso_is_pinned_by_sha256_and_size(self):
        self.assertEqual(DATA["iso"]["sha256"],
                         "be806212d0e979b2f45839517e2b15610e36467d466a10064d8c98f6d2216d8d")
        self.assertGreater(DATA["iso"]["bytes"], 2 * 1024**3)
        self.assertEqual(DATA["iso"]["name"], "supralinux-aurora-1.0.0-amd64.iso")

    def test_bios_uefi_btrfs_and_first_boot_passed(self):
        tests = {item["id"]: item for item in DATA["tests"]}
        for name in ["ISO-BIOS-BOOT", "ISO-UEFI-SB", "INSTALL-BTRFS-OFFLINE",
                     "FIRST-BOOT-BTRFS", "TARGET-CLEANUP"]:
            with self.subTest(name=name):
                self.assertEqual(tests[name]["state"], "PASS")
                self.assertFalse(tests[name]["evidence"].startswith("/"))

    def test_target_observed_btrfs_and_no_installer(self):
        self.assertEqual(DATA["observed"]["filesystem"], "btrfs")
        self.assertEqual(DATA["observed"]["subvolume"], "/@")
        self.assertIn("calamares", DATA["observed"]["installer_removed"])
        self.assertIn("casper", DATA["observed"]["installer_removed"])
        self.assertEqual(DATA["inputs"]["installer"], "supralinux-calamares-config 1.0.1")
        self.assertEqual(DATA["inputs"]["kernel"], "7.0.0-43-generic")

    def test_no_absolute_host_paths(self):
        text = (ROOT / "manifests/iso-1.0.0.json").read_text()
        self.assertNotIn("/mnt/RAID0/", text)
        self.assertNotRegex(text, r"\"/home/")


if __name__ == "__main__":
    unittest.main()
