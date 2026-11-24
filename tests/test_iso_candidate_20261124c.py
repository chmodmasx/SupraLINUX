import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "manifests/iso-candidate-20261124c.json").read_text())


class IsoCandidate20261124CTests(unittest.TestCase):
    def test_candidate_is_not_a_release(self):
        self.assertEqual(DATA["scope"], "iso-candidate-validation")
        self.assertEqual(DATA["status"], "PASS")
        self.assertFalse(DATA["release_ready"])
        self.assertIn("Candidato de testing", DATA["note"])

    def test_iso_is_pinned_by_hash_and_size(self):
        self.assertEqual(DATA["iso"]["sha256"],
                         "dac7a4ab419e125b217de68ffad634a12f927156aa22c71909b5e6d5f177c9ff")
        self.assertEqual(DATA["iso"]["name"],
                         "supralinux-aurora-1.0.0-amd64-20261124T223750Z-g2aa0f53.iso")
        self.assertEqual(DATA["iso"]["bytes"], 3180441600)

    def test_required_inputs_are_pinned(self):
        self.assertEqual(DATA["inputs"]["aptly_snapshot"],
                         "supralinux-testing-1.0.0-20261124d")
        self.assertEqual(DATA["inputs"]["theme"], "supralinux-theme 1.3.1")
        self.assertEqual(DATA["inputs"]["icons"], "supralinux-icons 1.3.0")

    def test_candidate_tests_passed(self):
        tests = {item["id"]: item for item in DATA["tests"]}
        for name in ["L3-BIOS", "L3-UEFI-SB", "L3-COLORS"]:
            with self.subTest(name=name):
                self.assertEqual(tests[name]["state"], "PASS")
                self.assertFalse(tests[name]["evidence"].startswith("/"))

    def test_no_absolute_host_paths(self):
        text = (ROOT / "manifests/iso-candidate-20261124c.json").read_text()
        self.assertNotIn("/mnt/RAID0/", text)
        self.assertNotRegex(text, r"\"/home/")


if __name__ == "__main__":
    unittest.main()
