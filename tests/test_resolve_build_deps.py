import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("resolve_build_deps", ROOT / "tools/resolve_build_deps.py")
RESOLVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESOLVER)


class ResolveBuildDepsTests(unittest.TestCase):
    def test_normalizes_debian_build_depends(self):
        self.assertEqual(
            RESOLVER.build_depends_names(
                "debhelper-compat (= 13), cmake (>= 3.29), ninja-build, python3"
            ),
            ["debhelper", "cmake", "ninja-build", "python3"],
        )
        self.assertEqual(
            RESOLVER.build_depends_names("libfoo-dev:any [amd64] | libbar-dev, libbaz"),
            ["libfoo-dev", "libbaz"],
        )

    def test_extra_packages_join_the_resolution_without_changing_build_depends(self):
        self.assertEqual(
            RESOLVER.install_names("debhelper-compat (= 13), cmake", ["python3", "python3", "libwayland-bin"]),
            ["debhelper", "cmake", "python3", "libwayland-bin"],
        )
        with self.assertRaisesRegex(ValueError, "Invalid extra package"):
            RESOLVER.install_names("debhelper-compat (= 13)", ["../../etc/passwd"])

    def test_parses_new_and_upgraded_packages(self):
        text = (
            "Inst libsmartcols1 [2.41.3-3ubuntu2] (2.41.3-3ubuntu2.2 Ubuntu:26.04/resolute-updates [amd64])\n"
            "Inst cmake (4.2.3-2ubuntu2 Ubuntu:26.04/resolute [amd64])\n"
            "Conf libsmartcols1 (2.41.3-3ubuntu2.2 Ubuntu:26.04/resolute-updates [amd64])\n"
        )
        self.assertEqual(RESOLVER.parse_installs(text), [
            {"name": "libsmartcols1", "version": "2.41.3-3ubuntu2.2"},
            {"name": "cmake", "version": "4.2.3-2ubuntu2"},
        ])

    def test_refuses_a_removal(self):
        with self.assertRaisesRegex(RuntimeError, "remove"):
            RESOLVER.parse_installs("Remv old-package [1.0]\n")

    def test_apt_options_are_owned_and_architecture_pinned(self):
        options = RESOLVER.apt_options(Path("/tmp/lists"), Path("/tmp/cache"),
                                       Path("/tmp/sources"), Path("/tmp/status"))
        joined = " ".join(options)
        self.assertIn("Dir::State::lists=/tmp/lists", joined)
        self.assertIn("Dir::Etc::sourceparts=-", joined)
        self.assertIn("Dir::State::status=/tmp/status", joined)
        self.assertIn("APT::Architecture=amd64", joined)
        self.assertNotIn("preferences", joined)

    def test_apt_preferences_replace_the_host_configuration(self):
        options = RESOLVER.apt_options(Path("/tmp/lists"), Path("/tmp/cache"),
                                       Path("/tmp/sources"), Path("/tmp/status"),
                                       Path("/tmp/preferences"))
        joined = " ".join(options)
        self.assertIn("Dir::Etc::preferences=/tmp/preferences", joined)
        self.assertIn("Dir::Etc::preferencesparts=-", joined)

    def test_extracts_status_from_a_rootfs_tarball(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tar_path = root / "rootfs.tar"
            with tarfile.open(tar_path, "w") as archive:
                data = b"Package: base-files\nStatus: install ok installed\n"
                info = tarfile.TarInfo("./var/lib/dpkg/status")
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            self.assertIn(b"base-files", RESOLVER.extract_status(tar_path))

    def test_counts_only_installed_packages(self):
        status = (
            b"Package: base-files\nStatus: install ok installed\n\n"
            b"Package: removed\nStatus: deinstall ok config-files\n\n"
            b"Package: helper\nStatus: install ok installed\n"
        )
        self.assertEqual(RESOLVER.installed_package_count(status), 2)


if __name__ == "__main__":
    unittest.main()
