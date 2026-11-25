import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from system_manager import paths, util
from system_manager.panels import displays

MONITORS = [
    {"name": "DP-1", "width": 3840, "height": 1080, "refreshRate": 60.0,
     "x": 0, "y": 0, "scale": 1.0, "transform": 0, "vrr": 0, "mirror": "",
     "disabled": False, "mode": "3840x1080@60.00", "bitdepth": "auto", "cm": "auto"},
    {"name": "HDMI-A-1", "width": 1920, "height": 1080, "refreshRate": 60.0,
     "x": 3840, "y": 0, "scale": 1.0, "transform": 0, "vrr": 2, "mirror": "",
     "disabled": False, "mode": "1920x1080@60.00", "bitdepth": "10", "cm": "auto"},
]


class DisplayProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sm-displays-"))
        self.saved = paths.CONFIG_ROOT
        paths.CONFIG_ROOT = self.tmp / "state"

    def tearDown(self):
        paths.CONFIG_ROOT = self.saved

    def test_save_keeps_only_layout_keys(self):
        result = displays.action("displays.profile_save",
                                 {"name": "Desk", "monitors": MONITORS})
        self.assertTrue(result["ok"], result)
        stored = json.loads((paths.CONFIG_ROOT / "displays.json").read_text())
        monitors = stored["profiles"]["Desk"]["monitors"]
        self.assertEqual([mon["name"] for mon in monitors], ["DP-1", "HDMI-A-1"])
        self.assertNotIn("width", monitors[0])
        self.assertEqual(monitors[1]["vrr"], 2)

    def test_invalid_names_are_refused(self):
        for name in ("", "a/b", "x" * 41, "   "):
            with self.subTest(name=name):
                result = displays.action("displays.profile_save",
                                         {"name": name, "monitors": MONITORS})
                self.assertFalse(result["ok"])

    def test_names_are_trimmed(self):
        displays.action("displays.profile_save", {"name": "  Desk  ", "monitors": MONITORS})
        stored = json.loads((paths.CONFIG_ROOT / "displays.json").read_text())
        self.assertIn("Desk", stored["profiles"])

    def test_profile_with_no_enabled_monitor_is_refused(self):
        off = [dict(MONITORS[0], disabled=True)]
        result = displays.action("displays.profile_save", {"name": "Blank", "monitors": off})
        self.assertFalse(result["ok"])

    def test_apply_writes_the_stored_layout(self):
        displays.action("displays.profile_save", {"name": "Desk", "monitors": MONITORS})
        with mock.patch.object(displays, "_write_layout",
                               return_value={"ok": True, "message": "applied"}) as write:
            result = displays.action("displays.profile_apply", {"name": "Desk"})
        self.assertTrue(result["ok"])
        monitors = write.call_args[0][0]
        self.assertEqual([mon["name"] for mon in monitors], ["DP-1", "HDMI-A-1"])

    def test_apply_unknown_profile_is_refused(self):
        with mock.patch.object(displays, "_write_layout") as write:
            result = displays.action("displays.profile_apply", {"name": "Nope"})
        self.assertFalse(result["ok"])
        write.assert_not_called()

    def test_delete_removes_only_that_profile(self):
        displays.action("displays.profile_save", {"name": "Desk", "monitors": MONITORS})
        displays.action("displays.profile_save", {"name": "Movie", "monitors": MONITORS})
        displays.action("displays.profile_delete", {"name": "Desk"})
        stored = json.loads((paths.CONFIG_ROOT / "displays.json").read_text())
        self.assertEqual(list(stored["profiles"]), ["Movie"])

    def test_probe_lists_profiles(self):
        displays.action("displays.profile_save", {"name": "Desk", "monitors": MONITORS})
        with mock.patch.object(displays, "_live_monitors", return_value=MONITORS), \
             mock.patch.object(util, "which", return_value="/usr/bin/hyprctl"):
            page = displays.probe()
        self.assertEqual(page["profiles"][0]["name"], "Desk")
        self.assertEqual(page["profiles"][0]["count"], 2)


if __name__ == "__main__":
    unittest.main()
