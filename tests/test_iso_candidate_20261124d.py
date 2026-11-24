import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "manifests/iso-candidate-20261124d.json").read_text())


class IsoCandidate20261124DTests(unittest.TestCase):
    def test_candidate_is_not_a_release(self):
        self.assertEqual(DATA["scope"], "iso-candidate-validation")
        self.assertEqual(DATA["status"], "PASS")
        self.assertFalse(DATA["release_ready"])
        self.assertIn("Candidato de testing", DATA["note"])

    def test_iso_is_pinned_by_hash_and_size(self):
        self.assertEqual(DATA["iso"]["sha256"],
                         "e41d62e5fb77e4f14c298826a1f83de706904394128ee041a7cff6a4fa9501ba")
        self.assertEqual(DATA["iso"]["name"],
                         "supralinux-aurora-1.0.0-amd64-20261124T225655Z-gc020d3b.iso")
        self.assertEqual(DATA["iso"]["bytes"], 3180441600)

    def test_required_inputs_are_pinned(self):
        self.assertEqual(DATA["inputs"]["aptly_snapshot"],
                         "supralinux-testing-1.0.0-20261124e")
        self.assertEqual(DATA["inputs"]["theme"], "supralinux-theme 1.3.2")
        self.assertEqual(DATA["inputs"]["icons"], "supralinux-icons 1.3.0")

    def test_candidate_tests_passed(self):
        tests = {item["id"]: item for item in DATA["tests"]}
        for name in ["L3-BIOS", "L3-UEFI-SB", "L3-COLORS"]:
            with self.subTest(name=name):
                self.assertEqual(tests[name]["state"], "PASS")
                self.assertFalse(tests[name]["evidence"].startswith("/"))

    def test_no_absolute_host_paths(self):
        text = (ROOT / "manifests/iso-candidate-20261124d.json").read_text()
        self.assertNotIn("/mnt/RAID0/", text)
        self.assertNotRegex(text, r"\"/home/")


if __name__ == "__main__":
    unittest.main()
