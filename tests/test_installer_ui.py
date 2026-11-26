import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer_ui", ROOT / "tools/qa/installer_ui.py")
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)


class InstallerUITests(unittest.TestCase):
    def test_observed_sidebar_selection(self):
        raw = bytearray(ui.WIDTH * ui.HEIGHT * 3)
        for i,y in enumerate(range(100,374,39)):
            off = (y * ui.WIDTH + 10)*3
            raw[off:off+3] = ui.SELECTED if i == 4 else ui.UNSELECTED
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frame.ppm"
            path.write_bytes(b"P6\n1280 800\n255\n" + raw)
            self.assertEqual(ui.page(path), "users")
            self.assertEqual(len(ui.crop_digest(path, 0, 0, 10, 10)),64)
            path.write_bytes(b"P6\n1280 800\n255\n")
            with self.assertRaises(ValueError):
                ui.page(path)

    def test_welcome_requires_unobscured_logo_and_active_next(self):
        with patch.object(ui, "page", return_value="welcome"), patch.object(ui, "crop_digest") as digest:
            digest.side_effect = [ui.WELCOME_LOGO, ui.WELCOME_NEXT]
            self.assertTrue(ui.welcome_ready(Path("frame")))
            digest.side_effect = ["obscured"]
            self.assertFalse(ui.welcome_ready(Path("frame")))
            digest.side_effect = [ui.WELCOME_LOGO, "inactive"]
            self.assertFalse(ui.welcome_ready(Path("frame")))
        with patch.object(ui, "page", return_value="location"):
            self.assertFalse(ui.welcome_ready(Path("frame")))

    def test_click_separates_motion_press_release(self):
        qmp = Mock()
        with patch.object(ui.time, "sleep"):
            ui.click(qmp, 1136, 736)
        events = [call.args[1]["events"] for call in qmp.call.call_args_list]
        self.assertEqual([[e["type"] for e in batch] for batch in events],
                         [["abs", "abs"], ["btn"], ["btn"]])
        self.assertTrue(events[1][0]["data"]["down"])
        self.assertFalse(events[2][0]["data"]["down"])
        with self.assertRaises(ValueError):
            ui.click(qmp, -1, 736)

    def test_key_events_release_in_reverse_order(self):
        qmp = Mock()
        with patch.object(ui.time, "sleep"):
            ui.key(qmp, "ctrl", "a")
        events = [call.args[1]["events"] for call in qmp.call.call_args_list]
        self.assertEqual([[e["data"]["key"]["data"] for e in batch] for batch in events],
                         [["ctrl", "a"], ["a", "ctrl"]])
        self.assertTrue(all(e["data"]["down"] for e in events[0]))
        self.assertTrue(all(not e["data"]["down"] for e in events[1]))

    def test_field_clears_previous_value_and_waits_after_typing(self):
        qmp = Mock()
        with patch.object(ui.time, "sleep") as sleep, patch.object(ui, "click"), patch.object(ui, "key") as key:
            ui.field(qmp, 300, 110, "supraqa")
        self.assertEqual([call.args[1:] for call in key.call_args_list],
                         [("ctrl", "a"), ("backspace",), *[(c,) for c in "supraqa"]])
        self.assertEqual(sleep.call_args.args, (0.70,))
