import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "archive_probe", Path(__file__).resolve().parents[1] / "tools/live/check-testing-archive.py"
)
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


class TestingArchiveTests(unittest.TestCase):
    def test_madison_retains_multiple_versions(self):
        text = " a | 1 | archive\n a | 2 | archive\n b | 3 | archive\n"
        self.assertEqual(archive.parse_madison(text), {"a": {"1", "2"}, "b": {"3"}})

    def test_report_distinguishes_desktop_gaps(self):
        report = archive.archive_report({"a": "2", "b": "3", "c": "4"},
                                        {"a", "b"}, {"a": {"1"}, "b": {"3"}})
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["matching_binaries"], 1)
        self.assertEqual(report["desktop_profile_gaps"], 1)
        self.assertEqual(report["gaps"][1]["available"], [])

    def test_matching_archive_is_not_iso_certification(self):
        report = archive.archive_report({"a": "1"}, {"a"}, {"a": {"1", "2"}})
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["scope"], "signed testing archive versions only")

    def test_inventory_duplicate_rejected(self):
        inventory = {"packages": [{"version": "1", "binaries": ["a"]},
                                  {"version": "2", "binaries": ["a"]}]}
        with self.assertRaises(ValueError):
            archive.expected_versions(inventory)
