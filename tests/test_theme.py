import configparser
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "packages/desktop/supralinux-theme"
ICONS = THEME / "usr/share/icons"

THEMES = {
    "SupraLINUX-Dark": ("SupraLINUX Oscuro", "breeze-dark,hicolor", "breeze-dark"),
    "SupraLINUX-Light": ("SupraLINUX Claro", "breeze,hicolor", "breeze"),
}
OLD_THEMES = ["Supralinux", "Supralinux-Light"]


def read_index(name):
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(ICONS / name / "index.theme", encoding="utf-8")
    return parser


class ThemeIconTests(unittest.TestCase):
    def test_icon_theme_ids_are_canonical(self):
        for name, (display, inherits, _) in THEMES.items():
            with self.subTest(theme=name):
                self.assertTrue((ICONS / name / "index.theme").is_file())
                index = read_index(name)["Icon Theme"]
                self.assertEqual(index["Name"], display)
                self.assertEqual(index["Inherits"], inherits)
                self.assertEqual(index["FollowsColorScheme"], "true")

    def test_old_icon_theme_ids_are_gone(self):
        for name in OLD_THEMES:
            with self.subTest(theme=name):
                self.assertFalse((ICONS / name).exists())

    def test_icon_theme_metadata_covers_every_declared_directory(self):
        for name in THEMES:
            with self.subTest(theme=name):
                parser = read_index(name)
                index = parser["Icon Theme"]
                directories = [item for item in index["Directories"].split(",") if item]
                scaled = [item for item in index.get("ScaledDirectories", "").split(",") if item]
                self.assertEqual(len(directories), 47)
                self.assertEqual(len(scaled), 38)
                for entry in directories + scaled:
                    with self.subTest(theme=name, entry=entry):
                        self.assertTrue(parser.has_section(entry), entry)
                        for key in ["Size", "Context", "Type"]:
                            self.assertIn(key, parser[entry])

    def test_icon_theme_symlinks_mirror_breeze(self):
        for name, (_, _, breeze) in THEMES.items():
            with self.subTest(theme=name):
                theme = ICONS / name
                links = [path for path in theme.rglob("*") if path.is_symlink()]
                self.assertEqual(len(links), 19852)
                invalid = []
                for link in links:
                    relative = link.relative_to(theme).as_posix()
                    target = os.readlink(link)
                    resolved = os.path.normpath(os.path.join(link.parent, target))
                    expected = os.path.normpath(ICONS / breeze / relative)
                    if os.path.isabs(target) or resolved != expected:
                        invalid.append(f"{relative} -> {target}")
                self.assertEqual(invalid, [])

    def test_icon_defaults_use_the_new_ids(self):
        references = {
            "usr/share/plasma/look-and-feel/org.kde.supralinux.aurora.desktop/contents/defaults":
                ("[kdeglobals][Icons]", "Theme", "SupraLINUX-Dark"),
            "usr/share/plasma/look-and-feel/org.kde.supralinux.aurora.light.desktop/contents/defaults":
                ("[kdeglobals][Icons]", "Theme", "SupraLINUX-Light"),
            "etc/xdg/gtk-3.0/settings.ini":
                ("[Settings]", "gtk-icon-theme-name", "SupraLINUX-Dark"),
            "etc/xdg/gtk-4.0/settings.ini":
                ("[Settings]", "gtk-icon-theme-name", "SupraLINUX-Dark"),
        }
        for relative, (section, key, expected) in references.items():
            with self.subTest(path=relative):
                text = (THEME / relative).read_text()
                self.assertIn(section, text)
                self.assertIn(f"{key}={expected}", text)
                for old in OLD_THEMES:
                    self.assertNotIn(f"{key}={old}\n", text)


if __name__ == "__main__":
    unittest.main()
