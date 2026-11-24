import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "manifests/iso-candidate-20261124a.json").read_text())


class IsoCandidate20261124ATests(unittest.TestCase):
    def test_candidate_is_not_a_release(self):
        self.assertEqual(DATA["scope"], "iso-candidate-validation")
        self.assertEqual(DATA["status"], "PASS")
        self.assertFalse(DATA["release_ready"])
        self.assertIn("Candidato de testing", DATA["note"])

    def test_iso_is_pinned_by_hash_and_size(self):
        self.assertEqual(DATA["iso"]["sha256"],
                         "a218fc66420d855c624fbca5a3304336646c5a07152ec828f63f7cd65db9df99")
        self.assertEqual(DATA["iso"]["name"],
                         "supralinux-aurora-1.0.0-amd64-20261124T180005Z-gf724c1b.iso")
        self.assertGreater(DATA["iso"]["bytes"], 2 * 1024**3)

    def test_required_packages_and_snapshot_are_pinned(self):
        self.assertEqual(DATA["inputs"]["aptly_snapshot"],
                         "supralinux-testing-1.0.0-20261124a")
        self.assertEqual(DATA["inputs"]["defaults"], "supralinux-defaults 1.2.6")
        self.assertEqual(DATA["inputs"]["kdeconnect"], "kdeconnect 25.12.3-0supralinux8")
        self.assertEqual(DATA["inputs"]["theme"], "supralinux-theme 1.1.4")

    def test_candidate_tests_passed(self):
        tests = {item["id"]: item for item in DATA["tests"]}
        for name in ["L3-BIOS", "L3-UEFI-SB", "L3-PPA-INKSCAPE",
                     "L3-KDE-CONNECT", "L3-SDDM-LIGHT-ASSET"]:
            with self.subTest(name=name):
                self.assertEqual(tests[name]["state"], "PASS")
                self.assertFalse(tests[name]["evidence"].startswith("/"))

    def test_light_sddm_asset_matches_the_certified_theme(self):
        self.assertIn("b74bcbe4", json.dumps(DATA))
        self.assertIn("iso-theme-1.1.4-20261123", " ".join(DATA["limitations"]))

    def test_no_absolute_host_paths(self):
        text = (ROOT / "manifests/iso-candidate-20261124a.json").read_text()
        self.assertNotIn("/mnt/RAID0/", text)
        self.assertNotRegex(text, r"\"/home/")


if __name__ == "__main__":
    unittest.main()
