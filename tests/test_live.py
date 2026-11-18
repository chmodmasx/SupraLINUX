import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LiveImageTests(unittest.TestCase):
    def test_live_scripts_parse(self):
        for path in sorted((ROOT / "tools/live").glob("*.sh")):
            with self.subTest(path=path.name):
                result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_desktop_profile_uses_the_new_names_and_packages(self):
        profile = [
            line.strip()
            for line in (ROOT / "packages/desktop/desktop-packages.list").read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertIn("supralinux-base-files", profile)
        self.assertIn("supralinux-calamares-config", profile)
        self.assertIn("supralinux-drivers", profile)
        self.assertIn("firefox-l10n-es-ar", profile)
        self.assertNotIn("calamares-settings-kubuntu", profile)
        self.assertFalse((ROOT / "packages/desktop/desktop-complete.list").exists())
        self.assertEqual(len(profile), len(set(profile)), "duplicate packages in desktop profile")

    def test_setup_repo_uses_official_mozilla_and_a_local_key(self):
        text = (ROOT / "tools/live/setup-repo.sh").read_text()
        self.assertIn("SUPRALINUX_APT_CHANNEL", text)
        self.assertIn("supralinux-archive-key.asc", text)
        self.assertIn("Missing", text)
        self.assertNotIn("repo.supralinux.com", text)
        self.assertIn("packages.mozilla.org", (ROOT / "installer/apt/mozilla.sources").read_text())
        self.assertNotIn("repo.supralinux.com", (ROOT / "installer/apt/mozilla.sources").read_text())

    def test_sources_are_channel_specific_and_signed(self):
        testing = (ROOT / "installer/apt/supralinux-testing.sources").read_text()
        stable = (ROOT / "installer/apt/supralinux-stable.sources").read_text()
        for text, host, suite in [
            (testing, "https://testing.supralinux.com/", "testing"),
            (stable, "https://stable.supralinux.com/", "stable"),
        ]:
            with self.subTest(suite=suite):
                self.assertIn(host, text)
                self.assertIn(f"Suites: {suite}", text)
                self.assertIn("Signed-By: /usr/share/keyrings/supralinux-archive-key.asc", text)
                self.assertIn("Architectures: amd64", text)

    def test_identity_is_not_rewritten_in_the_seal_step(self):
        text = (ROOT / "tools/live/seal-rootfs.sh").read_text()
        self.assertIn("ID=supralinux", text)
        self.assertNotIn("ID=ubuntu", text)
        self.assertIn("supralinux-base-files", text)
        self.assertIn("supralinux-calamares-config", text)
        self.assertNotIn("calamares-settings-kubuntu", text)

    def test_customize_uses_the_packaged_calamares_config(self):
        text = (ROOT / "tools/live/customize-rootfs.sh").read_text()
        self.assertIn("desktop-packages.list", text)
        self.assertIn("supralinux-calamares-config", (ROOT / "packages/desktop/desktop-packages.list").read_text())
        self.assertNotIn("cp -a \"$repo_root/installer/calamares", text)

    def test_iso_defaults_to_the_1_0_0_live_tree(self):
        for name in ["build-iso.sh", "secureboot-efi.sh", "seal-rootfs.sh", "customize-rootfs.sh"]:
            text = (ROOT / "tools/live" / name).read_text()
            self.assertIn("live/1.0.0", text, name)
            self.assertNotIn("live-6.6.7", text, name)

    def test_recovery_helper_is_present(self):
        script = ROOT / "installer/recovery/supralinux-recover.sh"
        self.assertTrue(script.is_file())
        self.assertIn("@pre-rollback-", script.read_text())
        self.assertTrue((ROOT / "installer/recovery/supralinux-recovery.service").is_file())

    def test_no_previous_repository_key_is_shipped(self):
        keys = sorted(path.name for path in (ROOT / "installer/keys").iterdir())
        self.assertNotIn("supralinux-archive-key.asc", keys)
        self.assertIn("packages.mozilla.org.asc", keys)
        self.assertIn("README.md", keys)


if __name__ == "__main__":
    unittest.main()
