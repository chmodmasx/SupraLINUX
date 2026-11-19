import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "packages/desktop/supralinux-calamares-config"


class CalamaresConfigTests(unittest.TestCase):
    def test_package_contains_settings_modules_and_branding(self):
        for relative in [
            "etc/calamares/settings.conf",
            "etc/calamares/modules/partition.conf",
            "etc/calamares/modules/users.conf",
            "etc/calamares/branding/supralinux/branding.desc",
            "etc/calamares/branding/supralinux/show.qml",
            "usr/share/applications/kubuntu-calamares.desktop",
            "lang/es_AR/python.po",
        ]:
            with self.subTest(relative=relative):
                self.assertTrue((BASE / relative).is_file(), relative)

    def test_settings_use_the_supralinux_branding(self):
        settings = (BASE / "etc/calamares/settings.conf").read_text()
        self.assertIn("branding: supralinux", settings)
        self.assertIn("shellprocess@cleanup", settings)
        branding = (BASE / "etc/calamares/branding/supralinux/branding.desc").read_text()
        self.assertIn("versionedName:       SupraLINUX Aurora 1.0.0", branding)
        self.assertIn("productUrl:          https://supralinux.com/", branding)
        self.assertIn("supportUrl:          https://supralinux.com/", branding)

    def test_target_removes_only_installed_installer_packages(self):
        packages = (BASE / "etc/calamares/modules/packages.conf").read_text()
        for name in ["supralinux-calamares-config", "calamares", "calamares-data",
                     "libcalamaresui3.3", "cifs-utils", "casper"]:
            with self.subTest(name=name):
                self.assertIn(name, packages)
        for name in ["calamares-settings-kubuntu", "calamares-settings-ubuntu-common",
                     "calamares-settings-ubuntu-common-data"]:
            with self.subTest(foreign=name):
                self.assertNotIn(name, packages)

    def test_control_conflicts_with_foreign_settings_packages(self):
        control = (BASE / "debian/control").read_text()
        self.assertIn("Depends: ${misc:Depends}, calamares", control)
        self.assertIn("Conflicts: calamares-settings-kubuntu, calamares-settings-ubuntu-common", control)
        self.assertIn("Replaces: calamares-settings-kubuntu, calamares-settings-ubuntu-common", control)

    def test_catalog_compiles_with_msgfmt(self):
        source = BASE / "lang/es_AR/python.po"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "calamares-python.mo"
            result = subprocess.run(["msgfmt", "-o", str(output), str(source)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)

    def test_no_previous_workspace_paths(self):
        for path in BASE.rglob("*"):
            if not path.is_file() or path.suffix in {".png", ".qm", ".svg"}:
                continue
            text = path.read_text(errors="ignore")
            self.assertNotIn("/mnt/RAID0/" + "SupraLINUX_OS", text, path)


if __name__ == "__main__":
    unittest.main()
