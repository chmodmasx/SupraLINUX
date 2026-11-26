import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("live_probes", ROOT / "tools/qa/recovery-live-metrics.py")
probes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probes)


class LiveProbeTests(unittest.TestCase):
    def test_guest_modules_parse(self):
        for mode in probes.GUEST_SCRIPTS:
            subprocess.run(["sh", "-n"], input=probes.probe_script(mode), text=True, check=True)

    def test_recovery_targets_only_dedicated_disposable_disk(self):
        script = probes.probe_script("recovery")
        self.assertIn("/dev/disk/by-id/virtio-SUPRAQA-ROLLBACK", script)
        self.assertLess(script.index("test -z"), script.index("mkfs.btrfs"))
        self.assertLess(script.index("findmnt"), script.index("mkfs.btrfs"))
        self.assertIn("ROLLBACK_PASS:", script)

    def test_metrics_module_is_read_only(self):
        script = probes.probe_script("metrics")
        self.assertIn("MemAvailable", script)
        self.assertIn("/proc/swaps", script)
        self.assertNotIn("mkfs", script)
        self.assertNotIn("mount -o", script)

    def test_boot_helper_is_from_current_source(self):
        self.assertTrue(callable(probes.load_boot().command_line))
