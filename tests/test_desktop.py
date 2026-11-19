import shlex
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def os_release(path):
    values = {}
    for line in path.read_text().splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = " ".join(shlex.split(value)) if value.strip() else ""
    return values


class DesktopIntegrationTests(unittest.TestCase):
    def test_identity_files_match_the_product_contract(self):
        base = ROOT / "packages/desktop/supralinux-base-files"
        values = os_release(base / "usr/lib/os-release")
        self.assertEqual(values["ID"], "supralinux")
        self.assertEqual(values["ID_LIKE"], "ubuntu debian")
        self.assertEqual(values["VERSION_ID"], "26.04")
        self.assertEqual(values["VERSION_CODENAME"], "resolute")
        self.assertEqual(values["UBUNTU_CODENAME"], "resolute")
        self.assertEqual(values["PRETTY_NAME"], "SupraLINUX Aurora 1.0.0")
        self.assertEqual(values["VERSION"], "1.0.0 (Aurora)")
        self.assertEqual(values["SUPRALINUX_VERSION"], "1.0.0")
        self.assertEqual(values["SUPRALINUX_CODENAME"], "aurora")
        self.assertNotIn("SUPPORT_END", values)
        self.assertIn("DISTRIB_ID=SupraLINUX", (base / "usr/share/supralinux/base-files/lsb-release").read_text())

    def test_base_files_use_dpkg_divert(self):
        base = ROOT / "packages/desktop/supralinux-base-files"
        preinst = (base / "debian/preinst").read_text()
        postrm = (base / "debian/postrm").read_text()
        for name in ["/usr/lib/os-release", "/etc/lsb-release", "/etc/issue", "/etc/issue.net", "/etc/legal",
                     "/etc/update-motd.d/10-help-text"]:
            with self.subTest(name=name):
                self.assertIn(name, preinst)
                self.assertIn(name, postrm)
        self.assertIn("dpkg-divert", preinst)
        self.assertIn("dpkg-divert", postrm)
        self.assertIn("/usr/share/supralinux/base-files", (base / "debian/postinst").read_text())
        self.assertNotIn("etc/", (base / "debian/install").read_text())
        for script in [base / "debian/preinst", base / "debian/postrm", base / "debian/postinst"]:
            result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_defaults_depend_on_the_new_branding_and_identity(self):
        control = (ROOT / "packages/desktop/supralinux-defaults/debian/control").read_text()
        self.assertIn("supralinux-branding (>= 1.2.0)", control)
        self.assertIn("supralinux-theme (>= 1.0.3)", control)
        self.assertIn("supralinux-base-files (>= 1.0.0)", control)

    def test_defaults_add_the_exact_firefox_apparmor_profile(self):
        base = ROOT / "packages/desktop/supralinux-defaults"
        profile = base / "etc/apparmor.d/firefox-supralinux"
        text = profile.read_text()
        self.assertIn("profile firefox-supralinux /usr/lib/firefox/firefox", text)
        self.assertIn("profile firefox-supralinux-bin /usr/lib/firefox/firefox-bin", text)
        self.assertIn("userns,", text)
        self.assertIn("etc/apparmor.d etc", (base / "debian/install").read_text())
        result = subprocess.run(["apparmor_parser", "-Q", "-K", str(profile)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_defaults_disable_obex_pbap_plugin(self):
        base = ROOT / "packages/desktop/supralinux-defaults"
        dropin = base / "etc/systemd/user/obex.service.d/10-supralinux-no-eds.conf"
        text = dropin.read_text()
        self.assertIn("ExecStart=", text)
        self.assertIn("ExecStart=/usr/libexec/bluetooth/obexd -P pbap,irmc", text)

    def test_defaults_keep_the_desktop_helpers(self):
        base = ROOT / "packages/desktop/supralinux-defaults"
        for relative in [
            "usr/lib/supralinux/fix-firefox-desktop",
            "usr/local/sbin/supralinux-btrfs-setup",
            "usr/local/sbin/supralinux-keyboard",
            "usr/local/sbin/supralinux-kwallet-setup",
            "usr/local/sbin/supralinux-locale-check",
            "usr/local/sbin/supralinux-xdg-dirs",
            "usr/share/supralinux/fastfetch-logo.txt",
            "etc/skel/.local/share/dbus-1/services/org.freedesktop.secrets.service",
        ]:
            with self.subTest(relative=relative):
                self.assertTrue((base / relative).is_file(), relative)

    def test_driver_version_matches_the_changelog(self):
        base = ROOT / "packages/apps/supralinux-drivers"
        version = (base / "usr/lib/python3/dist-packages/supralinux_drivers/__init__.py").read_text()
        self.assertIn('__version__ = "1.0.9"', version)
        self.assertIn("supralinux-drivers (1.0.9)", (base / "debian/changelog").read_text())

    def test_casper_keeps_the_noswap_patch(self):
        base = ROOT / "packages/system/casper"
        self.assertIn("0001-honor-noswap.patch", (base / "debian/patches/series").read_text())
        self.assertTrue((base / "debian/patches/0001-honor-noswap.patch").is_file())

    def test_ath9k_quirk_is_present(self):
        base = ROOT / "packages/system/supralinux-ath9k-ar9565"
        self.assertTrue((base / "debian/supralinux-ath9k-ar9565.initramfs-hook").is_file())
        self.assertTrue((base / "usr/lib/supralinux/ath9k-load").is_file())
        self.assertTrue((base / "etc/modprobe.d/ath9k-supralinux.conf").is_file())

    def test_emoji_font_is_present(self):
        font = ROOT / "packages/fonts/noto-color-emoji/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
        self.assertTrue(font.is_file())
        self.assertGreater(font.stat().st_size, 1024 * 1024)

    def test_kdeconnect_sftp_vendor_is_complete(self):
        base = ROOT / "packages/apps/supralinux-kdeconnect-sftp"
        self.assertTrue((base / "go.mod").is_file())
        self.assertTrue((base / "go.sum").is_file())
        self.assertTrue((base / "vendor/modules.txt").is_file())
        self.assertTrue((base / "internal/sftpserver/server.go").is_file())


if __name__ == "__main__":
    unittest.main()
