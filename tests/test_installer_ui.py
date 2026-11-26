import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer_ui", ROOT / "tools/qa/installer_ui.py")
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)


class InstallerUITests(unittest.TestCase):
    def test_observed_sidebar_selection(self):
        raw = bytearray(ui.WIDTH * ui.HEIGHT * 3)
        for i,y in enumerate(range(100,374,39)):
            off = (y * ui.WIDTH + 10)*3
            raw[off:off+3] = ui.SELECTED if i == 4 else ui.UNSELECTED
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frame.ppm"
            path.write_bytes(b"P6\n1280 800\n255\n" + raw)
            self.assertEqual(ui.page(path), "users")
            self.assertEqual(len(ui.crop_digest(path, 0, 0, 10, 10)),64)
            path.write_bytes(b"P6\n1280 800\n255\n")
            with self.assertRaises(ValueError):
                ui.page(path)
