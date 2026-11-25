"""Keep the Go minimum declared by the Debian package aligned with go.mod."""
import re
import subprocess
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / 'packages/apps/supralinux-kdeconnect-sftp'


class KdeConnectToolchainTests(unittest.TestCase):
    def test_debian_go_minimum_matches_module(self):
        module = (BASE / 'go.mod').read_text()
        control = (BASE / 'debian/control').read_text()
        go = re.search(r'^go (\d+)\.(\d+)(?:\.\d+)?$', module, re.M)
        dep = re.search(r'golang-go\s*\(>=\s*([^\s)]+)\)', control)
        self.assertIsNotNone(go)
        self.assertIsNotNone(dep)
        minimum = f'2:{go[1]}.{go[2]}~'
        subprocess.run(['dpkg', '--compare-versions', dep[1], 'ge', minimum], check=True)
