import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "manifests/stack-builds-1.0.0.json"


class StackBuildResultsTests(unittest.TestCase):
    def test_scope_is_partial_and_covers_all_three_layers(self):
        data = json.loads(RESULTS.read_text())
        self.assertEqual(data["scope"], "stack-clean-build-results")
        self.assertEqual(data["status"], "partial")
        self.assertIn("Frameworks", data["note"])
        self.assertIn("Plasma", data["note"])
        self.assertIn("Gear", data["note"])
        self.assertEqual(data["build_count"], 4)
        packages = [item["package"] for item in data["builds"]]
        self.assertEqual(packages, ["extra-cmake-modules", "libkf6coreaddons6", "libkwin6", "dolphin"])

    def test_results_have_artifact_manifest_and_cleanup(self):
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

    def test_no_absolute_workspace_paths(self):
        text = RESULTS.read_text()
        self.assertNotIn("/mnt/RAID0/", text)
        self.assertNotIn("/var/lib/", text)


if __name__ == "__main__":
    unittest.main()
