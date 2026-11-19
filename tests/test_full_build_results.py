import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = json.loads((ROOT / "manifests/full-build-results-1.0.0.json").read_text())
INVENTORY = json.loads((ROOT / "manifests/packages-1.0.0.json").read_text())


class FullBuildResultsTests(unittest.TestCase):
    def test_every_inventory_package_has_a_passing_build(self):
        builds = {item["package"]: item for item in RESULTS["builds"]}
        self.assertEqual(len(builds), 176)
        self.assertEqual(set(builds), {item["source"] for item in INVENTORY["packages"]})
        self.assertEqual(RESULTS["build_count"], 176)
        self.assertEqual(RESULTS["counts"], {"pass": 176, "fail": 0, "infra_invalid": 0})

    def test_results_do_not_claim_a_release(self):
        self.assertEqual(RESULTS["status"], "PASS")
        self.assertFalse(RESULTS["release_ready"])
        self.assertIn("no la ISO", RESULTS["note"])

    def test_builds_match_the_current_packaging_and_manifest(self):
        inventory = {item["source"]: item for item in INVENTORY["packages"]}
        for build in RESULTS["builds"]:
            package = inventory[build["package"]]
            self.assertEqual(build["version"], package["version"])
            self.assertEqual(build["area"], package["area"])
            manifest = json.loads((ROOT / build["manifest"]).read_text())
            self.assertEqual(manifest["version"], package["version"])
            self.assertEqual(manifest["source"]["path"], package["path"])
            self.assertEqual(build["artifact"]["name"], build["artifact"]["name"].split("/")[-1])
            self.assertRegex(build["artifact"]["sha256"], r"^[a-f0-9]{64}$")
            self.assertGreater(build["artifact"]["bytes"], 0)

    def test_evidence_is_relative_and_cleanup_is_complete(self):
        for build in RESULTS["builds"]:
            self.assertFalse(build["evidence"].startswith("/"))
            self.assertTrue(build["evidence"].startswith("evidence/clean-build/"))
            self.assertTrue(build["sbuild_invoked"])
            self.assertEqual(build["cleanup"], {
                "process_absent": True,
                "overlay_absent": True,
                "run_directory_absent": True,
            })

    def test_no_absolute_host_paths(self):
        text = (ROOT / "manifests/full-build-results-1.0.0.json").read_text()
        self.assertNotIn("/mnt/RAID0/", text)
        self.assertNotRegex(text, r"\"/home/")


if __name__ == "__main__":
    unittest.main()
