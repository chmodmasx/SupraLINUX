import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("boot_installed", ROOT / "tools/qa/boot-installed.py")
boot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boot)


class GreeterEvidenceTests(unittest.TestCase):
    def test_blank_and_cursor_only_are_not_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "frame.ppm"
            header = b"P6\n320 200\n255\n"
            path.write_bytes(header + bytes(320 * 200 * 3))
            self.assertFalse(boot.visible_frame(path)["nonblank"])
            path.write_bytes(header + bytes([255] * 30) + bytes(320 * 200 * 3 - 30))
            self.assertFalse(boot.visible_frame(path)["nonblank"])

    def test_nonuniform_visible_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "frame.ppm"
            raw = bytes(c for i in range(320 * 200) for c in (i % 256, 128, 80))
            path.write_bytes(b"P6\n320 200\n255\n" + raw)
            self.assertTrue(boot.visible_frame(path)["nonblank"])
            path.write_bytes(b"P6\n320 200\n255\n" + raw[:-1])
            with self.assertRaises(ValueError):
                boot.visible_frame(path)
