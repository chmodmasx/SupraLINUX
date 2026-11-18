import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "manifests/smoke-iso-1.0.0.json").read_text())


class SmokeIsoTests(unittest.TestCase):
    def test_iso_is_explicitly_a_smoke_not_a_release(self):
        self.assertEqual(DATA["scope"], "smoke-iso-result")
        self.assertEqual(DATA["status"], "smoke")
        self.assertFalse(DATA["release_ready"])
        self.assertIn("No es un build limpio", DATA["note"])
        self.assertIn("No se publicó", " ".join(DATA["limitations"]))

    def test_iso_has_a_sha256_and_relative_workspace_path(self):
        self.assertRegex(DATA["iso"]["sha256"], r"^[a-f0-9]{64}$")
        self.assertFalse(DATA["iso"]["workspace_path"].startswith("/"))
        self.assertGreater(DATA["iso"]["bytes"], 1024 * 1024)

    def test_bios_and_secure_boot_tests_passed(self):
        tests = {item["id"]: item for item in DATA["tests"]}
        self.assertEqual(tests["SMOKE-BIOS"]["state"], "PASS")
        self.assertEqual(tests["SMOKE-UEFI-SB"]["state"], "PASS")
        for item in DATA["tests"]:
            self.assertFalse(item["evidence"].startswith("/"))
            self.assertIn("evidence/smoke-iso/", item["evidence"])

    def test_no_absolute_host_paths(self):
        text = (ROOT / "manifests/smoke-iso-1.0.0.json").read_text()
        self.assertNotIn("/mnt/RAID0/", text)


if __name__ == "__main__":
    unittest.main()
