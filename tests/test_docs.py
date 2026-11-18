import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_relative_links_resolve(self):
        missing = []
        for path in sorted(list(ROOT.glob("*.md")) + list(ROOT.glob("docs/*.md"))):
            for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", path.read_text()):
                target = match.group(1)
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                resolved = (path.parent / target.split("#", 1)[0]).resolve()
                if not resolved.exists():
                    missing.append(f"{path.relative_to(ROOT)} -> {target}")
        self.assertEqual(missing, [])

    def test_documentation_index_lists_the_technical_docs(self):
        index = (ROOT / "docs/README.md").read_text()
        for name in ["clean-build.md", "live-image.md", "installer.md", "testing.md",
                     "release.md", "secure-boot.md", "provenance.md", "compatibility.md"]:
            with self.subTest(name=name):
                self.assertIn(f"({name})", index)

    def test_installer_and_live_docs_use_the_new_names(self):
        for name in ["docs/installer.md", "docs/live-image.md"]:
            text = (ROOT / name).read_text()
            self.assertIn("supralinux-calamares-config", text, name)
            self.assertNotIn("desktop-complete.list", text, name)

    def test_docs_do_not_promise_support_end(self):
        for path in sorted((ROOT / "docs").glob("*.md")):
            text = path.read_text()
            self.assertNotIn("SUPPORT_END=", text, path.name)


if __name__ == "__main__":
    unittest.main()
