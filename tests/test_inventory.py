import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package_inventory", ROOT / "tools/package_inventory.py")
INVENTORY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INVENTORY)


class InventoryTests(unittest.TestCase):
    def test_inventory_covers_all_packaging_areas(self):
        data = INVENTORY.inventory()
        self.assertEqual(data["scope"], "source-inventory")
        self.assertEqual(data["status"], "packaging")
        self.assertEqual(data["areas"], {
            "kde": 68, "plasma": 61, "gear": 20, "gear-extras": 15,
            "desktop": 7, "apps": 2, "fonts": 1, "system": 2,
        })
        self.assertEqual(len(data["packages"]), 176)
        self.assertNotIn("supralinux-build-test", [item["source"] for item in data["packages"]])

    def test_inventory_paths_and_versions_are_real(self):
        data = INVENTORY.inventory()
        for item in data["packages"]:
            with self.subTest(source=item["source"]):
                path = ROOT / item["path"]
                self.assertTrue((path / "debian/control").is_file())
                self.assertTrue(item["binaries"])
                self.assertIn("licenses", item)
                self.assertTrue(item["version"])

    def test_committed_inventory_matches_the_tree(self):
        path = ROOT / "manifests/packages-1.0.0.json"
        self.assertTrue(path.is_file())
        committed = json.loads(path.read_text())
        generated = INVENTORY.inventory()
        self.assertEqual(committed, generated)


if __name__ == "__main__":
    unittest.main()
