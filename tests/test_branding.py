import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BrandingTests(unittest.TestCase):
    def test_required_brand_assets_exist(self):
        required = [
            "branding/grub/supralinux/theme.txt",
            "branding/grub/supralinux/background.png",
            "branding/supralinux/logos/supralinux-color.svg",
            "branding/supralinux/logos/supralinux-color-512.png",
            "branding/supralinux/logos/supralinux-white-blue.svg",
            "branding/supralinux/logos/supralinux-white-blue-512.png",
            "branding/supralinux/wallpapers/SupraLINUX/metadata.json",
            "branding/supralinux/wallpapers/SupraLINUX/contents/images/1920x1080.png",
            "branding/xdg-user-dirs/README.md",
        ]
        for relative in required:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file(), relative)

    def test_branding_package_installs_the_expected_trees(self):
        install = (ROOT / "packages/desktop/supralinux-branding/debian/install").read_text()
        for entry in ["usr/share/grub", "usr/share/plymouth", "usr/share/wallpapers", "usr/share/icons"]:
            with self.subTest(entry=entry):
                self.assertIn(entry, install)
                self.assertTrue((ROOT / "packages/desktop/supralinux-branding" / entry).is_dir())

    def test_theme_package_installs_the_expected_trees(self):
        install = (ROOT / "packages/desktop/supralinux-theme/debian/install").read_text()
        for entry in [
            "etc/xdg/gtk-3.0", "etc/xdg/gtk-4.0", "usr/share/color-schemes",
            "usr/share/plasma", "usr/share/sddm", "usr/share/sounds",
            "usr/share/themes",
        ]:
            with self.subTest(entry=entry):
                self.assertIn(entry, install)
                self.assertTrue((ROOT / "packages/desktop/supralinux-theme" / entry).is_dir())

    def test_icon_package_installs_the_expected_trees(self):
        base = ROOT / "packages/desktop/supralinux-icons"
        install = (base / "debian/install").read_text()
        self.assertIn("usr/share/icons", install)
        for theme in ["SupraLINUX-Dark", "SupraLINUX-Light"]:
            with self.subTest(theme=theme):
                self.assertTrue((base / "usr/share/icons" / theme / "index.theme").is_file())

    def test_no_generated_build_metadata_is_versioned(self):
        patterns = ["*.deb", "*.changes", "*.buildinfo", "*.substvars",
                    "debhelper-build-stamp", "files", "*.debhelper"]
        for package in ["supralinux-branding", "supralinux-theme", "supralinux-icons"]:
            base = ROOT / "packages/desktop" / package
            for pattern in patterns:
                for path in base.rglob(pattern):
                    with self.subTest(path=path):
                        self.fail(f"generated build metadata: {path.relative_to(ROOT)}")

    def test_theme_uses_the_branding_package_version(self):
        control = (ROOT / "packages/desktop/supralinux-theme/debian/control").read_text()
        self.assertIn("supralinux-branding (>= 1.2.0)", control)
        self.assertIn("Package: supralinux-theme", control)

    def test_branding_changelog_and_copyright_are_present(self):
        for package in ["supralinux-branding", "supralinux-theme", "supralinux-icons"]:
            base = ROOT / "packages/desktop" / package / "debian"
            with self.subTest(package=package):
                self.assertTrue((base / "changelog").is_file())
                self.assertTrue((base / "copyright").is_file())
                self.assertIn("GPL-2.0-or-later", (base / "copyright").read_text())


if __name__ == "__main__":
    unittest.main()
