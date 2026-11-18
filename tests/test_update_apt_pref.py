import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("update_apt_pref", ROOT / "tools/update-apt-pref.py")
PREF = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREF)


class UpdateAptPrefTests(unittest.TestCase):
    def test_package_names_are_sorted_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, packages in {
                "a": ["libdemo6", "demo"],
                "b": ["demo", "demo-data"],
            }.items():
                control = root / "packages" / name / "debian/control"
                control.parent.mkdir(parents=True)
                control.write_text(
                    "Source: demo\n\n"
                    + "".join(f"Package: {package}\nArchitecture: any\n\n" for package in packages)
                )
            saved = PREF.ROOT
            try:
                PREF.ROOT = root
                self.assertEqual(PREF.package_names(), ["demo", "demo-data", "libdemo6"])
            finally:
                PREF.ROOT = saved

    def test_pref_pins_only_local_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control = root / "packages/demo/debian/control"
            control.parent.mkdir(parents=True)
            control.write_text("Package: demo\nPackage: libdemo6\n")
            saved_root, saved_out = PREF.ROOT, PREF.OUT
            try:
                PREF.ROOT = root
                PREF.OUT = root / "installer/apt/90-supralinux.pref"
                with patch("sys.argv", ["update-apt-pref.py"]), contextlib.redirect_stdout(io.StringIO()):
                    PREF.main()
                text = PREF.OUT.read_text()
            finally:
                PREF.ROOT, PREF.OUT = saved_root, saved_out
            self.assertIn("Package: demo libdemo6", text)
            self.assertIn("Pin: release o=SupraLINUX", text)
            self.assertIn("Pin-Priority: 1001", text)
            self.assertNotIn("Package: *", text)


if __name__ == "__main__":
    unittest.main()
