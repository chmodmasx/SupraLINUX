import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "packages/desktop/supralinux-recovery-gui"


class RecoveryGuiTests(unittest.TestCase):
    def test_package_metadata(self):
        control = (BASE / "debian/control").read_text()
        self.assertIn("Package: supralinux-recovery-gui", control)
        self.assertIn("Architecture: any", control)
        self.assertIn("qt6-base-dev", control)
        self.assertIn("qt6-declarative-dev", control)
        self.assertIn("pkexec", control)
        self.assertIn("qml6-module-org-kde-kirigami", control)

    def test_desktop_and_autostart_entries(self):
        desktop = (BASE / "data/supralinux-recovery.desktop").read_text()
        self.assertIn("Exec=supralinux-recovery-gui", desktop)
        self.assertIn("Icon=supralinux-recovery", desktop)
        self.assertIn("Terminal=false", desktop)
        autostart = (BASE / "data/autostart/supralinux-recovery.desktop").read_text()
        self.assertIn("Exec=supralinux-recovery-gui --autostart", autostart)
        self.assertIn("OnlyShowIn=KDE;", autostart)

    def test_qml_uses_the_backend_and_kirigami(self):
        qml = (BASE / "qml/Main.qml").read_text()
        self.assertIn("import org.kde.kirigami", qml)
        self.assertIn("Backend.refreshDevices", qml)
        self.assertIn("Backend.restore", qml)
        self.assertIn("Backend.recoveryMode", qml)
        self.assertNotIn("Terminal", qml)

    def test_polkit_action_and_live_rule(self):
        policy = (BASE / "data/com.supralinux.recovery.policy").read_text()
        self.assertIn("com.supralinux.recovery.run", policy)
        self.assertIn("/usr/libexec/supralinux-recovery-helper", policy)
        rules = (BASE / "data/49-supralinux-recovery.rules").read_text()
        self.assertIn("subject.user == \"supralinux\"", rules)
        self.assertIn("polkit.Result.YES", rules)

    def test_helper_executes_the_backend(self):
        helper = (BASE / "data/supralinux-recovery-helper").read_text()
        self.assertIn("/usr/local/sbin/supralinux-recover", helper)
        self.assertIn("exec /usr/local/sbin/supralinux-recover", helper)

    def test_live_integration(self):
        customize = (ROOT / "tools/live/customize-rootfs.sh").read_text()
        self.assertIn("supralinux-recovery-gui", customize)
        self.assertIn("27supralinux-recovery-icon", customize)
        self.assertIn("SUPRALINUX_REQUIRE_RECOVERY_GUI", customize)
        build = (ROOT / "tools/live/build-iso.sh").read_text()
        self.assertIn("supralinux.recovery=1", build)
        self.assertNotIn("systemd.unit=multi-user.target", build)
        seal = (ROOT / "tools/live/seal-rootfs.sh").read_text()
        self.assertIn("usr/bin/pkexec", seal)
        self.assertIn("expected 4755", seal)

    def test_target_removes_gui_and_helper(self):
        text = (ROOT / "packages/desktop/supralinux-calamares-config/"
                "etc/calamares/modules/shellprocess_supralinux.conf").read_text()
        self.assertIn("dpkg --purge supralinux-recovery-gui", text)
        self.assertIn("/usr/libexec/supralinux-recovery-helper", text)
        self.assertIn("/usr/local/sbin/supralinux-recover", text)


if __name__ == "__main__":
    unittest.main()
