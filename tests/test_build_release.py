import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_release", ROOT / "tools/build_release.py")
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class BuildReleaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.directory.name)
        self.saved_workspace = BUILD.WORKSPACE
        BUILD.WORKSPACE = self.workspace

    def tearDown(self):
        BUILD.WORKSPACE = self.saved_workspace
        self.directory.cleanup()

    def test_parse_result_accepts_trailing_warnings(self):
        payload = {"state": "PASS", "artifact": {"sha256": "a" * 64}}
        self.assertEqual(BUILD.parse_result(json.dumps(payload)), payload)
        self.assertEqual(BUILD.parse_result("warning\n" + json.dumps(payload) + "\n"), payload)
        self.assertIsNone(BUILD.parse_result("only text"))

    def test_artifact_is_retained_checks_path_and_hash(self):
        data = b"artifact"
        target = self.workspace / "artifact.deb"
        target.write_bytes(data)
        entry = {"artifact": {"path": str(target), "sha256": sha(data)}}
        self.assertTrue(BUILD.artifact_is_retained(entry))
        self.assertFalse(BUILD.artifact_is_retained(
            {"artifact": {"path": str(target), "sha256": "0" * 64}}))
        self.assertFalse(BUILD.artifact_is_retained({"artifact": {"path": str(target)}}))

    def test_package_state_records_manifest_and_version(self):
        repo = self.workspace / "repo"
        repo.mkdir()
        manifest = repo / "demo.json"
        manifest.write_text(json.dumps({"version": "1.0.0"}) + "\n")
        saved_root = BUILD.ROOT
        BUILD.ROOT = repo
        try:
            state = BUILD.package_state({"state": "PASS"}, manifest)
        finally:
            BUILD.ROOT = saved_root
        self.assertEqual(state["manifest_sha256"], sha(manifest.read_bytes()))
        self.assertEqual(state["version"], "1.0.0")
        self.assertEqual(state["state"], "PASS")


if __name__ == "__main__":
    unittest.main()
