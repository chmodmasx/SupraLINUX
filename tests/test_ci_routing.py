import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "ci_routing", Path(__file__).resolve().parents[1] / "tools/ci/select-jobs.py"
)
routing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routing)


class CiRoutingTests(unittest.TestCase):
    def test_docs_and_icons_do_not_select_expensive_jobs(self):
        self.assertEqual(routing.classify(["docs/design.md", "packages/desktop/supralinux-icons/icon.svg"]), set())

    def test_go_package_selects_go_only(self):
        self.assertEqual(routing.classify(["packages/apps/supralinux-kdeconnect-sftp/debian/control"]), {"kdeconnect"})

    def test_installer_selects_kvm_only(self):
        self.assertEqual(routing.classify(["packages/desktop/supralinux-calamares-config/etc/calamares/settings.conf"]), {"kvm"})

    def test_ci_changes_select_all(self):
        self.assertEqual(routing.classify([".github/workflows/testing-ci.yml"]), set(routing.JOBS))

    def test_manual_and_missing_base_select_all(self):
        self.assertEqual(routing.plan("workflow_dispatch", "a", "b")[0], set(routing.JOBS))
        self.assertEqual(routing.plan("push", "", "b")[0], set(routing.JOBS))

    def test_failed_diff_selects_all(self):
        with patch.object(routing.subprocess, "check_output", side_effect=subprocess.CalledProcessError(128, "git")):
            self.assertEqual(routing.plan("push", "a", "b")[0], set(routing.JOBS))

    def test_diff_includes_deleted_and_renamed_paths(self):
        with patch.object(routing.subprocess, "check_output", return_value=b"packages/apps/supralinux-kdeconnect-sftp/debian/control\x00installer/recovery/script.sh\x00") as diff:
            self.assertEqual(routing.plan("pull_request", "a", "b")[0], set(routing.JOBS))
            self.assertIn("--no-renames", diff.call_args.args[0])
