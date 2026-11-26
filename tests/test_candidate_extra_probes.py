import argparse
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("extra", ROOT / "tools/qa/candidate-extra-probes.py")
extra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extra)


class ExtraProbeTests(unittest.TestCase):
    def test_memory_matrix_is_offline_and_has_no_writable_disk(self):
        boot = extra.load_boot()
        # Stub the firmware-specific builder for this routing unit test.
        class Boot:
            @staticmethod
            def command_line(*args):
                return ["qemu", "-m", "6144", "-nic", "none"]
        for memory in extra.MEMORY_MIB:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                args = argparse.Namespace(iso=root / "test.iso", scenario=f"zram-{memory}")
                cmd = extra.command_line(Boot, args, root, root)
                self.assertEqual(cmd[cmd.index("-m")+1], str(memory))
                self.assertEqual(cmd[cmd.index("-nic")+1], "none")
                self.assertNotIn("-drive", cmd)
        self.assertTrue(callable(boot.command_line))

    def test_exchange_fixture_guards_precede_format(self):
        script = (ROOT / "tools/qa/guest/atomic-exchange.sh").read_text()
        subprocess.run(["sh", "-n"], input=script, text=True, check=True)
        self.assertIn("virtio-SUPRAQA-EXCHANGE", script)
        self.assertLess(script.index("test -z"), script.index("mkfs.btrfs"))
        self.assertLess(script.index("findmnt"), script.index("mkfs.btrfs"))
        self.assertIn("renameat2", script)
        self.assertIn("ATOMIC_EXCHANGE_PASS", script)
