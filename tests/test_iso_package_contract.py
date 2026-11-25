import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "verify_packages", Path(__file__).resolve().parents[1] / "tools/live/verify-packages.py"
)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


class IsoPackageContractTests(unittest.TestCase):
    def setUp(self):
        self.expected = {"defaults": "1.2.7", "calamares": "1.0.3", "optional": "2"}
        self.required = {"defaults", "calamares"}

    def test_exact_versions_and_unrelated_packages(self):
        status = "defaults\t1.2.7\tinstalled\ncalamares\t1.0.3\tinstalled\nubuntu\t99\tinstalled"
        self.assertEqual(contract.verify(self.expected, self.required, status), (2, []))

    def test_old_and_missing_packages_are_rejected(self):
        status = "defaults\t1.2.6\tinstalled\ncalamares\t1.0.3\tconfig-files"
        count, errors = contract.verify(self.expected, self.required, status)
        self.assertEqual(count, 1)
        self.assertEqual(len(errors), 2)
        self.assertIn("calamares", errors[0])
        self.assertIn("1.2.6", errors[1])

    def test_installed_optional_and_multiarch_versions_are_checked(self):
        status = "defaults\t1.2.7\tinstalled\ndefaults\t1.2.6\tinstalled\ncalamares\t1.0.3\tinstalled\noptional\t1\tinstalled"
        count, errors = contract.verify(self.expected, self.required, status)
        self.assertEqual(count, 3)
        self.assertEqual(len(errors), 2)

    def test_profile_comments_and_inventory_exclusions(self):
        self.assertEqual(contract.profile_packages("defaults # comment\n# line\ncalamares\n"), self.required)
        inventory = {"packages": [
            {"version": "1", "binaries": ["a", "b"]},
            {"version": "2", "binaries": ["c"], "test_only": True},
        ]}
        self.assertEqual(contract.expected_packages(inventory), {"a": "1", "b": "1"})
        inventory["packages"].append({"version": "3", "binaries": ["a"]})
        with self.assertRaises(ValueError):
            contract.expected_packages(inventory)
