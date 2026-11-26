import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "boot_installed", Path(__file__).resolve().parents[1] / "tools/qa/boot-installed.py")
boot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boot)


class InstalledBootHarnessTests(unittest.TestCase):
    def test_disk_only_offline_boot_and_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            command = boot.command_line(root / "target.qcow2", root, root, "bios")
        self.assertNotIn("-cdrom", command)
        self.assertIn("-snapshot", command)
        self.assertEqual(command[command.index("-boot") + 1], "c")
        self.assertEqual(command[command.index("-nic") + 1], "none")
        self.assertIn("q35,accel=kvm", command)

    def test_uefi_requires_installation_variables(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(OSError):
                boot.command_line(root / "target.qcow2", root, root, "uefi")

    def test_contract_arguments_pin_versions(self):
        inventory = {"packages": [
            {"source": "supralinux-defaults", "version": "1.2.7"},
            {"source": "supralinux-kdeconnect-sftp", "version": "1.0.3"}]}
        args = boot.contract_arguments("uefi", "btrfs", "qa", "live-id", inventory)
        self.assertIn("supralinux-defaults=1.2.7", args)
        self.assertIn("supralinux-kdeconnect-sftp=1.0.3", args)
        self.assertIn("live-id", args)
        with self.assertRaises(ValueError):
            boot.contract_arguments("bios", "ext4", "qa", "live-id", {"packages": []})
