import configparser
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "packages/desktop/supralinux-defaults/etc/systemd/zram-generator.conf"


class ZramPolicyTests(unittest.TestCase):
    def test_configuration(self):
        config = configparser.ConfigParser(interpolation=None)
        self.assertEqual(config.read(CONFIG), [str(CONFIG)])
        self.assertEqual(dict(config["zram0"]), {
            "host-memory-limit": "none",
            "zram-size": "min(ram / 2, 8192)",
            "compression-algorithm": "lz4",
            "swap-priority": "100",
        })
