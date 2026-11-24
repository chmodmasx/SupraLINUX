import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "packages/gear/kdeconnect"
SERIES = BASE / "debian/patches/series"
PATCH = BASE / "debian/patches/0006-plugin-settings-apply-immediately.patch"
CHANGELOG = BASE / "debian/changelog"


class KdeConnectPluginToggleTests(unittest.TestCase):
    def test_patch_is_in_the_series(self):
        self.assertIn("0006-plugin-settings-apply-immediately.patch",
                      SERIES.read_text().splitlines())

    def test_patch_notifies_the_daemon(self):
        text = PATCH.read_text()
        self.assertIn("DeviceDbusInterface", text)
        self.assertIn("setPluginEnabled", text)
        self.assertIn("writeEntry", text)

    def test_patch_is_documented_as_not_forwarded(self):
        text = PATCH.read_text()
        self.assertIn("Forwarded: not-yet", text)
        self.assertIn("Description:", text)

    def test_changelog_documents_the_fix(self):
        text = CHANGELOG.read_text()
        self.assertIn("kdeconnect (25.12.3-0supralinux8)", text)
        self.assertIn("Device::setPluginEnabled", text)


if __name__ == "__main__":
    unittest.main()
