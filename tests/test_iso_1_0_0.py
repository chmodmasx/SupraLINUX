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
                         "4d39412b0e359ee9831d2ca0e1b81b2c114a0d58ed91dfc10343bb5fd310b1d7")
        self.assertGreater(DATA["iso"]["bytes"], 2 * 1024**3)
        self.assertEqual(DATA["iso"]["name"],
                         "supralinux-aurora-1.0.0-amd64.iso")

    def test_l3_l4_l6_matrix_passed(self):
        tests = {item["id"]: item for item in DATA["tests"]}
        for name in ["L3-BIOS", "L3-UEFI-SB", "L3-LIVE-DEFAULTS", "L3-SYSMON-COLORS",
                     "L3-KIOADMIN-HOME",
                     "L3-RECOVERY-AUTOSTART",
                     "L4-A-UEFI-BTRFS", "L4-B-BIOS-EXT4", "L4-C-LUKS2",
                     "L4-D1-SAME-DISK", "L4-D2-TWO-DISKS", "L4-E-RAID",
                     "L6-GUI", "L6-ROLLBACK", "L6-HOME-RETENTION",
                     "L6-BOOT-AFTER-ROLLBACK", "TARGET-CLEANUP"]:
            with self.subTest(name=name):
                self.assertEqual(tests[name]["state"], "PASS")
                self.assertFalse(tests[name]["evidence"].startswith("/"))

    def test_target_observed_matrix_and_no_installer(self):
        self.assertIn("btrfs", DATA["observed"]["filesystems"])
        self.assertIn("ext4", DATA["observed"]["filesystems"])
        self.assertIn("luks2", DATA["observed"]["filesystems"])
        self.assertEqual(DATA["observed"]["subvolume"], "/@")
        self.assertIn("calamares", DATA["observed"]["installer_removed"])
        self.assertIn("casper", DATA["observed"]["installer_removed"])
        self.assertIn("supralinux-recovery-gui", DATA["observed"]["installer_removed"])
        self.assertIn("gamemode", DATA["observed"]["user_groups"])
        self.assertEqual(DATA["inputs"]["installer"], "supralinux-calamares-config 1.0.2")
        self.assertEqual(DATA["inputs"]["base_files"], "supralinux-base-files 1.0.2")
        self.assertEqual(DATA["inputs"]["defaults"], "supralinux-defaults 1.2.4")
        self.assertEqual(DATA["inputs"]["theme"], "supralinux-theme 1.1.3")
        self.assertEqual(DATA["inputs"]["branding"], "supralinux-branding 1.3.2")
        self.assertEqual(DATA["inputs"]["kio_admin"], "kio-admin 25.12.3-0supralinux2")
        self.assertEqual(DATA["inputs"]["aptly_snapshot"],
                         "supralinux-testing-1.0.0-20261122f")
        self.assertEqual(DATA["inputs"]["recovery_gui"], "supralinux-recovery-gui 1.0.0")
        self.assertEqual(DATA["inputs"]["os_prober"], "os-prober 1.84ubuntu1")
        self.assertEqual(DATA["inputs"]["kernel"], "7.0.0-43-generic")

    def test_no_absolute_host_paths(self):
        text = (ROOT / "manifests/iso-1.0.0.json").read_text()
        self.assertNotIn("/mnt/RAID0/", text)
        self.assertNotRegex(text, r"\"/home/")


if __name__ == "__main__":
    unittest.main()
