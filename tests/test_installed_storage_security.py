import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("contract", ROOT / "tools/qa/installed-contract.py")
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


class StorageSecurityTests(unittest.TestCase):
    def test_secure_boot_requires_enabled_and_enrolled(self):
        def flag(value):
            return bytes((7, 0, 0, 0, value))
        self.assertEqual(contract.secure_boot_policy(flag(1), flag(0)),
                         {"SecureBoot": 1, "SetupMode": 0})
        for secure, setup in ((0, 0), (1, 1), (2, 0)):
            with self.assertRaises(ValueError):
                contract.secure_boot_policy(flag(secure), flag(setup))
        with self.assertRaises(ValueError):
            contract.efi_flag(b"\x01")

    def test_luks2_metadata_requires_encrypted_segment(self):
        self.assertTrue(contract.luks2_metadata('{"segments":{"0":{"type":"crypt"}}}'))
        for raw in ('{}', '{"segments":{}}', '{"segments":{"0":{"type":"linear"}}}'):
            with self.assertRaises(ValueError):
                contract.luks2_metadata(raw)

    def test_crypttab_matches_actual_mapping_and_uuid(self):
        uuid = "11111111-2222-3333-4444-555555555555"
        valid = f"# fixture\nroot UUID={uuid} none luks\n"
        self.assertEqual(contract.crypttab_entry(valid, "root", uuid),
                         {"mapping": "root", "luks_uuid": uuid})
        self.assertEqual(contract.crypttab_entry(f"root /dev/disk/by-uuid/{uuid} - luks", "root", uuid),
                         {"mapping": "root", "luks_uuid": uuid})
        for bad in ("", valid + valid, valid.replace(uuid, "other"),
                    valid.replace("none", "/path/to/key"), valid.replace("root ", "wrong ")):
            with self.assertRaises(ValueError):
                contract.crypttab_entry(bad, "root", uuid)

    def test_mount_device_uses_real_source_not_anonymous_btrfs_id(self):
        from unittest.mock import patch, MagicMock
        import stat
        import os
        block = MagicMock()
        block.stat.return_value.st_mode = stat.S_IFBLK
        block.stat.return_value.st_rdev = os.makedev(252, 2)
        path = MagicMock()
        path.resolve.return_value = block
        # /dev/block/252:2 is constructed via the final Path call.
        with patch.object(contract, "command", side_effect=[
                "/dev/vda2", "btrfs", "devid 1 size 100 used 20 path /dev/vda2"
        ]) as command, patch.object(contract, "Path", side_effect=[path, path, Path("/dev/block")]):
            self.assertEqual(contract.mount_device("/"), Path("/dev/block/252:2"))
            self.assertIn("--nofsroot", command.call_args_list[0].args)
