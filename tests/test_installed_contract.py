import argparse
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "installed_contract", Path(__file__).resolve().parents[1] / "tools/qa/installed-contract.py"
)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


class InstalledContractTests(unittest.TestCase):
    def test_zram_size_policy_multiple_memory_sizes(self):
        for gib in (2, 4, 8, 16, 32, 64):
            with self.subTest(gib=gib):
                meminfo = f"MemTotal: {gib * 1024 * 1024} kB\n"
                size = int(min(gib / 2, 8) * 1024**3)
                result = contract.zram_policy(meminfo, str(size), "lzo [lz4] zstd",
                    "Filename Type Size Used Priority\n/dev/zram0 partition 1024 0 100\n")
                self.assertEqual(result["capacity_bytes"], size)

    def test_zram_rejects_old_policy_and_inactive_swap(self):
        meminfo = "MemTotal: 16777216 kB\n"
        good = str(8 * 1024**3)
        swaps = "Filename Type Size Used Priority\n/dev/zram0 partition 1024 0 100\n"
        for size, algorithms, active in ((str(4 * 1024**3), "[lz4]", swaps),
                                        (good, "lz4 [zstd]", swaps),
                                        (good, "[lz4]", swaps.replace("100", "99")),
                                        (good, "[lz4]", swaps.splitlines()[0])):
            with self.assertRaises(ValueError):
                contract.zram_policy(meminfo, size, algorithms, active)

    def test_expected_package_versions_are_explicit(self):
        self.assertEqual(contract.expected_package("supralinux-defaults=1.2.7"),
                         ("supralinux-defaults", "1.2.7"))
        with self.assertRaises(argparse.ArgumentTypeError):
            contract.expected_package("supralinux-defaults")
