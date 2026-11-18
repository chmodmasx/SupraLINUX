import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "manifests/package-smoke-results-1.0.0.json"


class PackageSmokeResultsTests(unittest.TestCase):
    def test_results_are_partial_and_list_two_smokes(self):
        data = json.loads(RESULTS.read_text())
        self.assertEqual(data["scope"], "package-smoke-results")
        self.assertEqual(data["status"], "partial")
        self.assertEqual(data["smoke_count"], 2)
        self.assertEqual([item["package"] for item in data["smokes"]],
                         ["supralinux-build-test", "supralinux-base-files"])

    def test_each_smoke_has_manifest_artifact_and_cleanup(self):
        data = json.loads(RESULTS.read_text())
        for smoke in data["smokes"]:
            with self.subTest(package=smoke["package"]):
                self.assertEqual(smoke["state"], "PASS")
                self.assertRegex(smoke["artifact"]["sha256"], r"^[a-f0-9]{64}$")
                self.assertFalse(smoke["artifact"]["name"].startswith("/"))
                self.assertFalse(smoke["evidence"].startswith("/"))
                manifest = json.loads((ROOT / smoke["manifest"]).read_text())
                self.assertEqual(manifest["package"], smoke["package"])
                self.assertEqual(manifest["version"], smoke["version"])
                self.assertEqual(smoke["cleanup"]["process_absent"], True)
                self.assertEqual(smoke["cleanup"]["overlay_absent"], True)
                self.assertEqual(smoke["cleanup"]["run_directory_absent"], True)

    def test_conffile_failure_is_recorded(self):
        data = json.loads(RESULTS.read_text())
        self.assertEqual(len(data["infra_invalid_attempts"]), 1)
        self.assertEqual(data["infra_invalid_attempts"][0]["state"], "INFRA_INVALID")

    def test_no_absolute_paths(self):
        text = RESULTS.read_text()
        self.assertNotIn("/mnt/RAID0/", text)
        self.assertNotIn("/var/lib/", text)


if __name__ == "__main__":
    unittest.main()
