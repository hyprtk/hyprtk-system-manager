import unittest
from unittest import mock

from system_manager import form, util
from system_manager.panels import hyprland
from system_manager.util import RunResult

SCHEMA = {"pages": [
    {"id": "general", "title": "General", "description": "Gaps and borders",
     "options": [
         {"path": "general.gaps_in", "label": "Inner gaps", "type": "int",
          "default": 5, "min": 0, "max": 60},
         {"path": "general.border_size", "label": "Border size", "type": "int",
          "default": 2, "min": 0, "max": 20},
         {"path": "general.resize_on_border", "label": "Resize on border",
          "type": "bool", "default": True},
         {"path": "general.layout", "label": "Layout", "type": "enum",
          "choices": [{"value": "dwindle", "label": "dwindle"},
                      {"value": "master", "label": "master"}]},
     ]},
    {"id": "decoration", "title": "Decoration", "description": "",
     "options": [
         {"path": "decoration.active_opacity", "label": "Active opacity",
          "type": "float", "default": 1.0, "min": 0.0, "max": 1.0},
     ]},
]}

DUMP = {"config": {"general": {"gaps_in": 7, "border_size": 3,
                              "resize_on_border": False, "layout": "master"},
                   "decoration": {"active_opacity": 0.95}}}


def fake_run(argv, **kwargs):
    if argv[:2] == ["config-manager", "schema"]:
        return RunResult(0, json_dump(SCHEMA), "")
    if argv[:2] == ["config-manager", "dump"]:
        return RunResult(0, json_dump(DUMP), "")
    if argv[:3] == ["config-manager", "set", "general.gaps_in"]:
        return RunResult(0, "verified", "")
    return RunResult(1, "", "unexpected command " + " ".join(argv))


def json_dump(data):
    import json
    return json.dumps(data)


class OptionRowTests(unittest.TestCase):
    def test_int_with_bounds_is_a_number(self):
        row = hyprland.option_row(SCHEMA["pages"][0]["options"][0], 7)
        self.assertEqual(row["type"], "number")
        self.assertEqual(row["min"], 0)
        self.assertEqual(row["value"], 7)

    def test_float_with_bounds_is_a_slider(self):
        row = hyprland.option_row(SCHEMA["pages"][1]["options"][0], 0.95)
        self.assertEqual(row["type"], "slider")
        self.assertAlmostEqual(row["max"], 1.0)

    def test_bool_is_a_toggle(self):
        row = hyprland.option_row(SCHEMA["pages"][0]["options"][2], False)
        self.assertEqual(row["type"], "toggle")
        self.assertFalse(row["value"])

    def test_enum_uses_the_schema_choices(self):
        row = hyprland.option_row(SCHEMA["pages"][0]["options"][3], "master")
        self.assertEqual(row["type"], "choice")
        self.assertEqual([item["value"] for item in row["choices"]],
                         ["dwindle", "master"])

    def test_missing_value_falls_back_to_the_default(self):
        row = hyprland.option_row(SCHEMA["pages"][0]["options"][0], None)
        self.assertEqual(row["value"], 5)


class HyprlandProbeTests(unittest.TestCase):
    def test_pages_are_rendered_with_values(self):
        with mock.patch.object(util, "which", return_value="/usr/bin/config-manager"), \
             mock.patch.object(util, "run", side_effect=fake_run):
            model = hyprland.probe()
        self.assertEqual(form.validate(model), [])
        titles = [section["title"] for section in model["sections"]]
        self.assertIn("General", titles)
        gaps = next(row for section in model["sections"]
                    for row in section["rows"] if row.get("key") == "general.gaps_in")
        self.assertEqual(gaps["value"], 7)
        self.assertEqual(model["status"], "full")

    def test_without_config_manager_the_page_links(self):
        with mock.patch.object(util, "which", return_value=None):
            model = hyprland.probe()
        self.assertEqual(model["status"], "link")
        self.assertEqual(form.validate(model), [])

    def test_a_read_error_is_reported_not_hidden(self):
        def broken(argv, **kwargs):
            if argv[:2] == ["config-manager", "schema"]:
                return RunResult(0, json_dump(SCHEMA), "")
            return RunResult(0, json_dump({"error": "no hyprland.lua"}), "")

        with mock.patch.object(util, "which", return_value="/usr/bin/config-manager"), \
             mock.patch.object(util, "run", side_effect=broken):
            model = hyprland.probe()
        self.assertEqual(model["sections"][0]["title"], "Could not read the config")


class HyprlandApplyTests(unittest.TestCase):
    def test_apply_uses_config_manager_with_the_schema_kind(self):
        with mock.patch.object(util, "which", return_value="/usr/bin/config-manager"), \
             mock.patch.object(util, "run", side_effect=fake_run) as run:
            result = hyprland.apply({"general.gaps_in": 9})
        self.assertTrue(result["ok"], result)
        self.assertIn(["config-manager", "set", "general.gaps_in", "9",
                       "--kind", "int"], [call[0][0] for call in run.call_args_list])

    def test_unknown_option_is_refused_before_writing(self):
        with mock.patch.object(util, "which", return_value="/usr/bin/config-manager"), \
             mock.patch.object(util, "run", side_effect=fake_run):
            result = hyprland.apply({"general.nope": 1})
        self.assertFalse(result["ok"])

    def test_a_failure_stops_the_rest(self):
        def failing(argv, **kwargs):
            if argv[:2] == ["config-manager", "schema"]:
                return RunResult(0, json_dump(SCHEMA), "")
            return RunResult(1, "", "rejected")

        with mock.patch.object(util, "which", return_value="/usr/bin/config-manager"), \
             mock.patch.object(util, "run", side_effect=failing):
            result = hyprland.apply({"general.gaps_in": 9})
        self.assertFalse(result["ok"])
        self.assertIn("rejected", result["message"])

    def test_preview_is_not_offered(self):
        self.assertEqual(hyprland.PREVIEW, "")


if __name__ == "__main__":
    unittest.main()
