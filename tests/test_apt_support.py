import shlex
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "packages/desktop/supralinux-defaults"
TEMPLATE = BASE / "usr/share/python-apt/templates/supralinux.info"
CONTROL = BASE / "debian/control"

try:
    import apt_pkg
    from aptsources.distro import Distribution
    from aptsources.sourceslist import SourcesList
    HAVE_APTSOURCES = True
except ImportError:
    HAVE_APTSOURCES = False


def os_release(path):
    values = {}
    for line in path.read_text().splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = " ".join(shlex.split(value)) if value.strip() else ""
    return values


class AptSupportTests(unittest.TestCase):
    def setUp(self):
        self.os_release = os_release(
            ROOT / "packages/desktop/supralinux-base-files/usr/lib/os-release")

    def test_template_name_matches_distribution_id(self):
        self.assertEqual(TEMPLATE.name, self.os_release["ID"] + ".info")

    def test_root_suite_matches_version_codename(self):
        suites = [line.split(":", 1)[1].strip()
                  for line in TEMPLATE.read_text().splitlines()
                  if line.startswith("Suite:")]
        self.assertTrue(suites)
        self.assertEqual(suites[0], self.os_release["VERSION_CODENAME"])

    def test_template_declares_all_ubuntu_components(self):
        text = TEMPLATE.read_text()
        for component in ["main", "universe", "restricted", "multiverse"]:
            with self.subTest(component=component):
                self.assertIn(f"Component: {component}", text)
        self.assertIn("RepositoryType: deb-src", text)

    def test_control_depends_on_python_apt_common(self):
        self.assertIn("python-apt-common", CONTROL.read_text())

    @unittest.skipUnless(HAVE_APTSOURCES, "python-apt/aptsources is not installed")
    def test_template_is_accepted_by_aptsources(self):
        apt_pkg.init()
        sources = SourcesList(matcherPath=str(TEMPLATE.parent), deb822=True)
        distro = Distribution(
            "supralinux", "resolute", "SupraLINUX Aurora 1.0.0", "26.04",
            ["ubuntu", "debian"], {})
        distro.get_sources(sources)
        self.assertEqual(distro.source_template.name, "resolute")
        self.assertEqual(distro.source_template.distribution, "supralinux")
        self.assertEqual(
            [component.name for component in distro.source_template.components],
            ["main", "universe", "restricted", "multiverse"])


if __name__ == "__main__":
    unittest.main()
