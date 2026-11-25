import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "stage_overlays", Path(__file__).resolve().parents[1] / "tools/live/stage-overlays.py"
)
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class StageOverlayTests(unittest.TestCase):
    def setUp(self):
        self.versions = {name: "1.0" for name in stage.OVERLAYS}
        self.files = {Path(name + ".deb"): (name, "1.0", arch)
                      for name, arch in stage.OVERLAYS.items()}

    def test_all_expected(self):
        self.assertEqual(set(stage.select(self.files, self.versions, self.files.__getitem__)),
                         set(stage.OVERLAYS))

    def test_missing_or_duplicate(self):
        paths = list(self.files)
        for invalid in (paths[:-1], paths + paths[:1]):
            with self.assertRaises(ValueError):
                stage.select(invalid, self.versions, self.files.__getitem__)

    def test_wrong_version_or_architecture(self):
        path = next(iter(self.files))
        name, version, arch = self.files[path]
        for replacement in ((name, "0.9", arch), (name, version, "arm64")):
            with self.subTest(replacement=replacement):
                self.files[path] = replacement
                with self.assertRaises(ValueError):
                    stage.select(self.files, self.versions, self.files.__getitem__)
