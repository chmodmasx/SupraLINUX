import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "manifests/aptly-publication-1.0.0.json").read_text())
INVENTORY = json.loads((ROOT / "manifests/packages-1.0.0.json").read_text())

# Publication 20261124c includes the current inventory plus retained versions
# of the desktop packages and kio-admin. The repo keeps older versions of
# theme, defaults, branding and kio-admin in both indexes.
PENDING_PUBLICATION = set()


class AptlyPublicationTests(unittest.TestCase):
    def test_publication_is_pinned_but_not_a_release(self):
        self.assertEqual(DATA["scope"], "aptly-publication")
        self.assertEqual(DATA["status"], "PASS")
        self.assertFalse(DATA["release_ready"])
        self.assertEqual(DATA["snapshot"], "supralinux-testing-1.0.0-20261124e")

    def test_counts_match_the_source_inventory(self):
        published = [item for item in INVENTORY["packages"]
                     if item["source"] not in PENDING_PUBLICATION]
        # The repo keeps extra versions of the desktop packages and kio-admin:
        # 22 extra binary and 19 extra source entries in the published indexes.
        binaries = sum(len(item["binaries"]) for item in published) + 22
        sources = len(published) + 19
        self.assertEqual(DATA["counts"], {
            "binary_packages": binaries,
            "source_packages": sources,
            "total": binaries + sources,
        })

    def test_publication_has_the_release_key_and_source_endpoint(self):
        self.assertEqual(DATA["key"]["fingerprint"],
                         "9BAD7A4B1826213B3BE271E208780B9EEC43C2B8")
        self.assertTrue((ROOT / DATA["key"]["public_file"]).is_file())
        sources = (ROOT / "installer/apt/supralinux-testing.sources").read_text()
        self.assertIn(DATA["endpoints"]["shipped_source"], sources)
        self.assertEqual(DATA["verification"]["inrelease_signature"], "PASS")

    def test_no_absolute_host_paths(self):
        text = (ROOT / "manifests/aptly-publication-1.0.0.json").read_text()
        self.assertNotIn("/mnt/RAID0/", text)
        self.assertNotRegex(text, r"\"/home/")


if __name__ == "__main__":
    unittest.main()
