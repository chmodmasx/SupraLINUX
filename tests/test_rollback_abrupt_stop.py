import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cut", ROOT / "tools/qa/rollback-abrupt-stop.py")
cut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cut)


class AbruptStopTests(unittest.TestCase):
    def test_isolated_raw_disk_and_offline_vm(self):
        class Boot:
            @staticmethod
            def command_line(*args):
                return ["qemu", "-nic", "none", "-cdrom", "candidate.iso"]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            cmd = cut.command_line(Boot, p/"candidate.iso", p/"fixture.raw", p, p)
            self.assertIn("format=raw,cache=none", cmd[cmd.index("-drive")+1])
            self.assertIn("serial=SUPRAQA-CUT", cmd[cmd.index("-device")+1])
            self.assertNotIn("-snapshot", cmd)
            self.assertEqual(cmd[cmd.index("-nic")+1], "none")

    def test_guest_script_guard_and_boundaries(self):
        source = cut.GUEST.read_text()
        subprocess.run(["sh", "-n"], input=source, text=True, check=True)
        self.assertLess(source.index("SUPRAQA-CUT"), source.index("mkfs.btrfs"))
        self.assertLess(source.index("test -z"), source.index("mkfs.btrfs"))
        for phase in cut.PHASES:
            self.assertIn(phase, source)
        self.assertIn("CUT_PASS:", source)
        self.assertIn("home-marker", source)
        self.assertIn("original:changed|changed:original", source)
