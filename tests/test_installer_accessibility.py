import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("atspi", ROOT / "tools/qa/guest/inspect-accessibility.py")
atspi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atspi)


class AccessibilityTests(unittest.TestCase):
    def test_parse_registry_children(self):
        raw = "([(':1.0', objectpath '/org/a11y/atspi/accessible/root'), (':1.2', '/org/a11y/atspi/accessible/root')],)"
        self.assertEqual(atspi.parse_refs(raw), [
            (":1.0", atspi.ROOT), (":1.2", atspi.ROOT)])
        self.assertEqual(atspi.parse_refs("([], )"), [])

    def test_parse_name_and_role(self):
        self.assertEqual(atspi.parse_string("(< 'Borrar todo el disco' >,)"), "Borrar todo el disco")
        self.assertEqual(atspi.parse_string("('push button',)"), "push button")

    def test_ref_validation(self):
        with self.assertRaises(ValueError):
            atspi.parse_refs("([('app', 'not-a-path')],)")
