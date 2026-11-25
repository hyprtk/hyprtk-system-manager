import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from system_manager import form, jsonconf, paths, util
from system_manager.panels import bar
from system_manager.util import RunResult

CONFIG = {
    "position": "top",
    "height": 34,
    "opacity": 0.92,
    "radius": 12,
    "use_pywal": True,
    "fontSize": 12,
    "themeSource": "",
    "themeAccent": "",
    "theme": {"source": "", "name": "", "accent": ""},
    "font": {"family": "Noto Sans", "size": 12},
    "animations": {"mode": "high", "durationMs": 140},
    "layoutLeft": ["start_button", "workspaces"],
    "quicklinks": [{"glyph": "x", "command": "hyprtk-edit"}],
    "monitors": [{"name": "DP-1", "scale": 1.0}],
}


class BarProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sm-bar-"))
        self.saved = paths.BAR_CONFIG
        paths.BAR_CONFIG = self.tmp / "config.json"
        paths.BAR_CONFIG.write_text(json.dumps(CONFIG))

    def tearDown(self):
        paths.BAR_CONFIG = self.saved

    def test_page_is_valid_and_grouped(self):
        model = bar.probe()
        self.assertEqual(form.validate(model), [])
        titles = [section["title"] for section in model["sections"]]
        self.assertIn("Theme", titles)
        self.assertIn("Font", titles)
        self.assertIn("The bar's own editors", titles)

    def test_toggle_and_slider_types(self):
        rows = {row.get("key"): row for section in bar.probe()["sections"]
                for row in section["rows"] if row.get("key")}
        self.assertEqual(rows["use_pywal"]["type"], "toggle")
        self.assertEqual(rows["opacity"]["type"], "slider")
        self.assertEqual(rows["fontSize"]["type"], "number")

    def test_structured_lists_link_to_the_bar_settings(self):
        model = bar.probe()
        section = next(item for item in model["sections"] if item["title"] == "Quicklinks")
        self.assertTrue(any(row["type"] == "note" for row in section["rows"]))

    def test_missing_config_is_a_read_only_page(self):
        paths.BAR_CONFIG.unlink()
        model = bar.probe()
        self.assertEqual(model["status"], "read")
        self.assertEqual(form.validate(model), [])


class BarApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sm-bar-"))
        self.saved = paths.BAR_CONFIG
        paths.BAR_CONFIG = self.tmp / "config.json"
        paths.BAR_CONFIG.write_text(json.dumps(CONFIG))

    def tearDown(self):
        paths.BAR_CONFIG = self.saved

    def test_nested_and_flat_theme_keys_are_written_together(self):
        result = bar.apply({"theme.accent": "#ff0000"})
        self.assertTrue(result["ok"], result)
        data = jsonconf.load()
        self.assertEqual(data["theme"]["accent"], "#ff0000")
        self.assertEqual(data["themeAccent"], "#ff0000")

    def test_scalar_types_are_coerced(self):
        bar.apply({"height": "40", "use_pywal": "false", "radius": 8.4})
        data = jsonconf.load()
        self.assertEqual(data["height"], 40)
        self.assertFalse(data["use_pywal"])
        self.assertEqual(data["radius"], 8)

    def test_ranges_are_clamped(self):
        bar.apply({"opacity": 3, "fontSize": 2})
        data = jsonconf.load()
        self.assertEqual(data["opacity"], 1.0)
        self.assertEqual(data["fontSize"], 8)

    def test_lists_round_trip_through_comma_text(self):
        bar.apply({"layoutLeft": "start_button, tasklist , clock"})
        self.assertEqual(jsonconf.load()["layoutLeft"],
                         ["start_button", "tasklist", "clock"])

    def test_unknown_keys_are_ignored(self):
        result = bar.apply({"nope": 1})
        self.assertTrue(result["ok"])
        self.assertNotIn("nope", jsonconf.load())

    def test_preview_declared(self):
        self.assertEqual(bar.PREVIEW, "files")


if __name__ == "__main__":
    unittest.main()
