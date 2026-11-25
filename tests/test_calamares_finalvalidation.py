"""Static contract tests; the target checks themselves require a VM install."""
import re
import subprocess
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / 'packages/desktop/supralinux-calamares-config/etc/calamares'


class FinalValidationTests(unittest.TestCase):
    def test_order(self):
        settings = (BASE / 'settings.conf').read_text()
        self.assertIn('config: shellprocess_finalvalidation.conf', settings)
        self.assertLess(settings.index('  - shellprocess@kwallet'), settings.index('  - shellprocess@finalvalidation'))
        self.assertLess(settings.index('  - shellprocess@finalvalidation'), settings.index('  - shellprocess@noprompt'))
        self.assertLess(settings.index('  - shellprocess@finalvalidation'), settings.index('  - umount'))

    def test_shell_syntax(self):
        config = (BASE / 'modules/shellprocess_finalvalidation.conf').read_text()
        scripts = re.findall(r'^    - \|-\n((?:^      .*\n)+)', config, re.M)
        self.assertEqual(len(scripts), 5)
        for script in scripts:
            subprocess.run(['sh', '-n'], input=script, text=True, check=True)

    def test_purge_error_is_not_ignored(self):
        cleanup = (BASE / 'modules/shellprocess_supralinux.conf').read_text()
        self.assertIn('"dpkg --purge supralinux-recovery-gui"', cleanup)
        self.assertNotIn('dpkg --purge supralinux-recovery-gui 2>/dev/null || true', cleanup)
