import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AREAS = {
    "kde": 68,
    "plasma": 61,
    "gear": 20,
    "gear-extras": 15,
}
GENERATED = [
    "*.deb", "*.changes", "*.buildinfo", "*.substvars",
    "debhelper-build-stamp", "files", "*.debhelper",
]


class PackagingTests(unittest.TestCase):
    def package_dirs(self, area):
        return sorted(path for path in (ROOT / "packages" / area).iterdir() if path.is_dir())

    def test_expected_package_areas_are_present(self):
        for area, minimum in AREAS.items():
            with self.subTest(area=area):
                self.assertGreaterEqual(len(self.package_dirs(area)), minimum)

    def test_every_package_has_the_minimum_debian_metadata(self):
        for area in AREAS:
            for package in self.package_dirs(area):
                debian = package / "debian"
                for name in ["control", "changelog", "copyright", "rules", "source/format"]:
                    with self.subTest(package=package.name, file=name):
                        self.assertTrue((debian / name).is_file(), f"{package}/{name}")

    def test_controls_are_sanitized(self):
        forbidden = ("Vcs-", "XSBC-", "Uploaders:", "Testsuite:")
        for area in AREAS:
            for package in self.package_dirs(area):
                control = (package / "debian/control").read_text()
                self.assertIn("Maintainer: SupraLINUX Project", control, package.name)
                for field in forbidden:
                    with self.subTest(package=package.name, field=field):
                        self.assertNotIn(field, control)

    def test_no_generated_build_metadata_is_versioned(self):
        for area in AREAS:
            for package in self.package_dirs(area):
                for pattern in GENERATED:
                    for path in package.rglob(pattern):
                        with self.subTest(path=path):
                            self.fail(f"generated build metadata: {path.relative_to(ROOT)}")

    def test_no_previous_workspace_paths_in_metadata(self):
        forbidden = ["/mnt/RAID0/" + "SupraLINUX_OS", "/var/lib/" + "supralinux"]
        for area in AREAS:
            for package in self.package_dirs(area):
                for name in ["control", "changelog", "copyright"]:
                    text = (package / "debian" / name).read_text(errors="ignore")
                    for value in forbidden:
                        with self.subTest(package=package.name, file=name):
                            self.assertNotIn(value, text)

    def test_gear_extras_replaces_the_old_complete_name(self):
        self.assertTrue((ROOT / "packages/gear-extras").is_dir())
        self.assertFalse((ROOT / "packages/complete").exists())


if __name__ == "__main__":
    unittest.main()
