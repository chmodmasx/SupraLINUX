import configparser
import hashlib
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / "packages/desktop/supralinux-icons/usr/share/icons"
BRAND = ROOT / "branding/supralinux/logos"
THEME = ROOT / "packages/desktop/supralinux-theme"

THEMES = {
    "SupraLINUX-Dark": ("SupraLINUX Oscuro", "breeze-dark"),
    "SupraLINUX-Light": ("SupraLINUX Claro", "breeze"),
}
OLD_THEMES = ["Supralinux", "Supralinux-Light"]
SIZES = ["16", "22", "24", "32", "48", "64", "96", "128", "256", "512"]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_index(name):
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(ICONS / name / "index.theme", encoding="utf-8")
    return parser


class ThemeIconTests(unittest.TestCase):
    def test_icon_theme_ids_are_canonical(self):
        for name, (display, _) in THEMES.items():
            with self.subTest(theme=name):
                parser = read_index(name)
                index = parser["Icon Theme"]
                self.assertEqual(index["Name"], display)
                self.assertEqual(index["Inherits"], "hicolor")
                self.assertEqual(index["FollowsColorScheme"], "true")
                self.assertEqual(index["Example"], "folder")

    def test_old_icon_theme_ids_are_gone(self):
        for name in OLD_THEMES:
            with self.subTest(theme=name):
                self.assertFalse((ICONS / name).exists())
                self.assertFalse((THEME / "usr/share/icons" / name).exists())

    def test_metadata_declares_every_icon_directory(self):
        for name in THEMES:
            with self.subTest(theme=name):
                theme = ICONS / name
                parser = read_index(name)
                index = parser["Icon Theme"]
                declared = set(item for item in index["Directories"].split(",") if item)
                scaled = set(item for item in index.get("ScaledDirectories", "").split(",") if item)
                actual = set()
                for path in theme.rglob("*"):
                    if path.is_symlink() and path.is_dir():
                        actual.add(path.relative_to(theme).as_posix())
                    elif path.is_file() or path.is_symlink():
                        parent = path.parent.relative_to(theme).as_posix()
                        if parent != ".":
                            actual.add(parent)
                self.assertEqual(actual, declared | scaled)
                for entry in declared | scaled:
                    with self.subTest(theme=name, entry=entry):
                        self.assertTrue(parser.has_section(entry), entry)
                        section = parser[entry]
                        for key in ["Size", "Context", "Type"]:
                            self.assertIn(key, section)
                        if entry in scaled:
                            self.assertIn("Scale", section)
                        if section["Type"] == "Scalable":
                            self.assertIn("MinSize", section)
                            self.assertIn("MaxSize", section)

    def test_icon_theme_is_self_contained(self):
        for name in THEMES:
            with self.subTest(theme=name):
                theme = (ICONS / name).resolve()
                links = [path for path in theme.rglob("*") if path.is_symlink()]
                self.assertGreater(len(links), 10000)
                broken = []
                external = []
                for link in links:
                    target = os.readlink(link)
                    self.assertFalse(os.path.isabs(target), f"absolute link: {link}")
                    try:
                        resolved = link.resolve(strict=True)
                    except FileNotFoundError:
                        broken.append(link)
                        continue
                    if not resolved.is_relative_to(theme):
                        external.append((link, resolved))
                self.assertEqual(broken, [])
                self.assertEqual(external, [])

    def test_complete_copy_has_real_icon_files(self):
        for name in THEMES:
            with self.subTest(theme=name):
                theme = ICONS / name
                regular = sum(1 for path in theme.rglob("*") if path.is_file() and not path.is_symlink())
                self.assertGreater(regular, 7000)

    def test_color_logo_is_the_only_brand_overlay(self):
        for name in THEMES:
            with self.subTest(theme=name):
                theme = ICONS / name
                for size in SIZES:
                    canonical = theme / "places" / size / "start-here.png"
                    self.assertTrue(canonical.is_file(), canonical)
                    self.assertEqual(sha256(canonical), sha256(BRAND / f"supralinux-color-{size}.png"))
                    for alias in ["start-here-kde.png", "start-here-kde-plasma.png"]:
                        link = theme / "places" / size / alias
                        self.assertTrue(link.is_symlink(), link)
                        self.assertEqual(link.resolve(), canonical.resolve())
                    for alias in ["org.kde.plasma.kickoff.png", "org.kde.plasma.kickofflegacy.png"]:
                        link = theme / "applets" / size / alias
                        self.assertTrue(link.is_symlink(), link)
                        self.assertEqual(link.resolve(), canonical.resolve())
                scalable = theme / "places/scalable/start-here.svg"
                self.assertTrue(scalable.is_file(), scalable)
                self.assertEqual(sha256(scalable), sha256(BRAND / "supralinux-color.svg"))
                for alias in ["start-here-kde.svg", "start-here-kde-plasma.svg"]:
                    link = theme / "places/scalable" / alias
                    self.assertTrue(link.is_symlink(), link)
                    self.assertEqual(link.resolve(), scalable.resolve())

    def test_default_icon_theme_stays_breeze_dark(self):
        dark = (THEME / "usr/share/plasma/look-and-feel/org.kde.supralinux.aurora.desktop/contents/defaults").read_text()
        light = (THEME / "usr/share/plasma/look-and-feel/org.kde.supralinux.aurora.light.desktop/contents/defaults").read_text()
        self.assertIn("Theme=breeze-dark", dark)
        self.assertIn("Theme=breeze", light)
        self.assertNotIn("Theme=SupraLINUX-Dark", dark)
        self.assertNotIn("Theme=SupraLINUX-Light", light)
        for relative in ["etc/xdg/gtk-3.0/settings.ini", "etc/xdg/gtk-4.0/settings.ini"]:
            self.assertIn("gtk-icon-theme-name=breeze-dark", (THEME / relative).read_text())

    def test_launcher_keeps_the_supralinux_logo(self):
        for relative in [
            "usr/share/plasma/look-and-feel/org.kde.supralinux.aurora.desktop/contents/layouts/org.kde.plasma.desktop-layout.js",
            "usr/share/plasma/look-and-feel/org.kde.supralinux.aurora.light.desktop/contents/layouts/org.kde.plasma.desktop-layout.js",
        ]:
            text = (THEME / relative).read_text()
            self.assertIn('kickoff.writeConfig("icon", "supralinux-color")', text)

    def test_light_chrome_uses_one_base_color(self):
        paths = [
            ROOT / "packages/desktop/supralinux-theme/usr/share/color-schemes/SupralinuxAuroraLight.colors",
            ROOT / "packages/desktop/supralinux-theme/usr/share/plasma/desktoptheme/org.kde.supralinux.light/colors",
        ]
        for path in paths:
            with self.subTest(path=path.name):
                parser = configparser.ConfigParser(interpolation=None, strict=False)
                parser.read(path)
                for group in ["Colors:Window", "Colors:Button", "Colors:Header", "Colors:Header][Inactive"]:
                    self.assertEqual(parser[group]["BackgroundNormal"], "233,238,245", group)
                    self.assertEqual(parser[group]["BackgroundAlternate"], "221,229,240", group)
                self.assertEqual(parser["Colors:View"]["BackgroundNormal"], "255,255,255")
                self.assertEqual(parser["WM"]["activeBackground"], "233,238,245")
                self.assertEqual(parser["WM"]["inactiveBackground"], "233,238,245")
                self.assertNotIn("AccentColor", parser["General"])

    def test_light_selection_and_highlight_roles_are_intentional(self):
        global_scheme = configparser.ConfigParser(interpolation=None, strict=False)
        global_scheme.read(ROOT / "packages/desktop/supralinux-theme/usr/share/color-schemes/SupralinuxAuroraLight.colors")
        plasma_style = configparser.ConfigParser(interpolation=None, strict=False)
        plasma_style.read(ROOT / "packages/desktop/supralinux-theme/usr/share/plasma/desktoptheme/org.kde.supralinux.light/colors")
        # Qt apps, icons and Plasma highlights keep the saturated brand
        # selection. Kickoff's pale rows come from the view/button roles.
        for parser in [global_scheme, plasma_style]:
            self.assertEqual(parser["Colors:Selection"]["BackgroundNormal"], "81,162,218")
            self.assertEqual(parser["Colors:Selection"]["BackgroundAlternate"], "111,182,228")
        for parser in [global_scheme, plasma_style]:
            for group in ["Colors:Button", "Colors:Header", "Colors:Header][Inactive",
                          "Colors:Selection", "Colors:Tooltip", "Colors:View", "Colors:Window"]:
                self.assertEqual(parser[group]["DecorationFocus"], "81,162,218", group)
                self.assertEqual(parser[group]["DecorationHover"], "62,147,204", group)

    def test_light_accent_lives_in_the_global_theme_only(self):
        light = (ROOT / "packages/desktop/supralinux-theme/usr/share/plasma/look-and-feel"
                 / "org.kde.supralinux.aurora.light.desktop/contents/defaults").read_text()
        dark = (ROOT / "packages/desktop/supralinux-theme/usr/share/plasma/look-and-feel"
                / "org.kde.supralinux.aurora.desktop/contents/defaults").read_text()
        self.assertIn("AccentColor=81,162,218", light)
        self.assertIn("AccentColor=116,172,216", dark)

    def test_light_plasma_progress_bar_uses_the_accent(self):
        path = (ROOT / "packages/desktop/supralinux-theme/usr/share/plasma/desktoptheme"
                / "org.kde.supralinux.light/widgets/bar_meter_horizontal.svgz")
        self.assertTrue(path.is_file())
        import gzip
        svg = gzip.decompress(path.read_bytes()).decode()
        self.assertIn("#51a2da", svg.lower())
        self.assertNotIn('class="ColorScheme-Highlight"', svg)

    def test_icon_package_is_independent_from_breeze(self):
        control = (ROOT / "packages/desktop/supralinux-icons/debian/control").read_text()
        package = control.split("Package: supralinux-icons", 1)[1]
        self.assertIn("hicolor-icon-theme", package)
        self.assertNotIn("breeze", package.split("Description:", 1)[0])
        install = (ROOT / "packages/desktop/supralinux-icons/debian/install").read_text()
        self.assertIn("usr/share/icons", install)
        theme_install = (THEME / "debian/install").read_text()
        self.assertNotIn("usr/share/icons", theme_install)


if __name__ == "__main__":
    unittest.main()
