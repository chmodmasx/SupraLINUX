import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "manifests/release-key.json").read_text())


class ReleaseKeyTests(unittest.TestCase):
    def test_public_key_is_present_and_not_private(self):
        path = ROOT / DATA["key"]["public_key"]
        self.assertTrue(path.is_file())
        text = path.read_text()
        self.assertIn("BEGIN PGP PUBLIC KEY BLOCK", text)
        self.assertNotIn("BEGIN PGP PRIVATE KEY", text)

    def test_public_key_fingerprint_matches_metadata(self):
        path = ROOT / DATA["key"]["public_key"]
        result = subprocess.run(
            ["gpg", "--batch", "--with-colons", "--show-keys", str(path)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        fingerprints = [
            line.split(":")[9]
            for line in result.stdout.splitlines()
            if line.startswith("fpr:")
        ]
        self.assertIn(DATA["key"]["fingerprint"], fingerprints)

    def test_security_docs_publish_the_fingerprint(self):
        for name in ["SECURITY.md", "SECURITY.en.md"]:
            text = (ROOT / name).read_text()
            self.assertIn(DATA["key"]["fingerprint"], text, name)

    def test_private_key_is_not_in_the_repository(self):
        for path in ROOT.rglob("*"):
            if path.is_file() and path.suffix in {".asc", ".key", ".gpg"}:
                if path == ROOT / DATA["key"]["public_key"]:
                    continue
                text = path.read_text(errors="ignore")
                self.assertNotIn("BEGIN PGP PRIVATE KEY", text, str(path))


if __name__ == "__main__":
    unittest.main()
