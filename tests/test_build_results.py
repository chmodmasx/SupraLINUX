import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "manifests/native-builds-1.0.0.json"


class NativeBuildResultsTests(unittest.TestCase):
    def test_results_are_partial_and_do_not_claim_release_validation(self):
        data = json.loads(RESULTS.read_text())
        self.assertEqual(data["scope"], "native-clean-build-results")
        self.assertEqual(data["status"], "partial")
        self.assertIn("Frameworks", data["note"])
        self.assertEqual(data["build_count"], 10)

    def test_every_build_matches_its_manifest(self):
        data = json.loads(RESULTS.read_text())
        for build in data["builds"]:
            with self.subTest(package=build["package"]):
                self.assertEqual(build["state"], "PASS")
                self.assertTrue(build["sbuild_invoked"])
                self.assertRegex(build["artifact"]["sha256"], r"^[a-f0-9]{64}$")
                self.assertFalse(build["artifact"]["name"].startswith("/"))
                self.assertFalse(build["evidence"].startswith("/"))
                manifest = json.loads((ROOT / build["manifest"]).read_text())
                self.assertEqual(manifest["package"], build["package"])
                self.assertEqual(manifest["version"], build["version"])
                self.assertEqual(build["cleanup"]["process_absent"], True)
                self.assertEqual(build["cleanup"]["overlay_absent"], True)
                self.assertEqual(build["cleanup"]["run_directory_absent"], True)

    def test_test_package_is_not_part_of_the_release(self):
        data = json.loads(RESULTS.read_text())
        test_builds = [item for item in data["builds"] if item["test_only"]]
        self.assertEqual([item["package"] for item in test_builds], ["supralinux-build-test"])

    def test_failed_infrastructure_attempt_is_recorded(self):
        data = json.loads(RESULTS.read_text())
        self.assertEqual(len(data["infra_invalid_attempts"]), 1)
        self.assertEqual(data["infra_invalid_attempts"][0]["state"], "INFRA_INVALID")
        self.assertIn("result.json", data["infra_invalid_attempts"][0]["error"])

    def test_no_absolute_workspace_paths(self):
        text = RESULTS.read_text()
        self.assertNotIn("/mnt/RAID0/", text)
        self.assertNotIn("/var/lib/", text)


if __name__ == "__main__":
    unittest.main()
