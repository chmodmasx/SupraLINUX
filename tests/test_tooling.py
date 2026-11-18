import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ToolingTests(unittest.TestCase):
    def test_shell_scripts_parse(self):
        scripts = [
            ROOT / "tools/check-host.sh",
            ROOT / "tools/guest_clean_build.sh",
            ROOT / "tests/fixtures/package-smoke",
            ROOT / "packages/supralinux-build-test/debian/tests/smoke",
            ROOT / "packages/supralinux-build-test/src/supralinux-build-test",
        ]
        for script in scripts:
            with self.subTest(script=script.name):
                result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_tools_do_not_keep_previous_workspace_paths(self):
        forbidden = ["/mnt/RAID0/" + "SupraLINUX_OS", "/var/lib/" + "supralinux/"]
        for directory in ["tools", "tests", "packages", "manifests"]:
            for path in (ROOT / directory).rglob("*"):
                if not path.is_file() or "__pycache__" in path.parts:
                    continue
                text = path.read_text(errors="ignore")
                for value in forbidden:
                    with self.subTest(path=path, value=value):
                        self.assertNotIn(value, text)

    def test_build_test_package_is_not_in_the_desktop_profile(self):
        desktop = ROOT / "packages/desktop/desktop-packages.list"
        if desktop.exists():
            self.assertNotIn("supralinux-build-test", desktop.read_text())


if __name__ == "__main__":
    unittest.main()
