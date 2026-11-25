import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "boot_live", Path(__file__).resolve().parents[1] / "tools/ci/boot-live.py"
)
boot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boot)


class LiveBootTests(unittest.TestCase):
    def test_bios_command_uses_real_kvm_and_no_network_or_writable_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            command = boot.command_line(path / "test.iso", path, path, "bios")
        self.assertIn("q35,accel=kvm", command)
        self.assertEqual(command[command.index("-nic") + 1], "none")
        self.assertNotIn("-drive", command)
        self.assertIn("-qmp", command)
        self.assertIn("virtserialport,chardev=qga0,name=org.qemu.guest_agent.0", command)

    def test_guest_check_requires_live_wayland_session(self):
        for required in ("kwin_wayland", "plasmashell", "/cdrom/casper",
                         "loginctl show-session", "wayland", "supralinux",
                         "ksplashqml", "org.kde.plasmashell", "org.freedesktop.DBus.Peer Ping"):
            self.assertIn(required, boot.CHECK)
