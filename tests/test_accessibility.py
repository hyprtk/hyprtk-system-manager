import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from system_manager import paths, util
from system_manager.panels import accessibility
from system_manager.util import RunResult


class AccessibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sm-a11y-"))
        self.saved = (paths.GTK3_SETTINGS, paths.GTK4_SETTINGS)
        paths.GTK3_SETTINGS = self.tmp / "gtk-3.0" / "settings.ini"
        paths.GTK4_SETTINGS = self.tmp / "gtk-4.0" / "settings.ini"
        self.env = mock.patch.dict(os.environ, {"HOME": str(self.tmp)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        paths.GTK3_SETTINGS, paths.GTK4_SETTINGS = self.saved

    def _probe(self, values: dict[tuple[str, str], str], *, binaries=("gsettings", "pgrep")):
        def fake_run(argv, **kwargs):
            if argv[0] == "pgrep":
                return RunResult(1, "", "")
            return RunResult(0, values.get((argv[2], argv[3]), ""), "")

        with mock.patch.object(util, "which",
                               side_effect=lambda name: name if name in binaries else None), \
             mock.patch.object(util, "run", side_effect=fake_run):
            return accessibility.probe()

    @staticmethod
    def _rows(page):
        return {row.get("key") or row.get("label"): row
                for section in page["sections"] for row in section["rows"]}

    def test_probe_reads_preferences(self):
        page = self._probe({
            (accessibility.INTERFACE, "text-scaling-factor"): "1.25",
            (accessibility.INTERFACE, "cursor-size"): "36",
            (accessibility.INTERFACE, "enable-animations"): "false",
            (accessibility.A11Y_KB, "sticky-keys-enable"): "true",
            (accessibility.A11Y_IFACE, "reduced-motion"): "true",
        })
        rows = self._rows(page)
        self.assertEqual(rows["text_scaling"]["value"], 125)
        self.assertEqual(rows["preset"]["value"], "125")
        self.assertEqual(rows["cursor_size"]["value"], 36)
        self.assertFalse(rows["animations"]["value"])
        self.assertTrue(rows["reduced_motion"]["value"])
        self.assertTrue(rows["sticky_keys"]["value"])

    def test_probe_states_missing_effect_tools_honestly(self):
        page = self._probe({}, binaries=("gsettings",))
        notes = [row["text"] for section in page["sections"]
                 for row in section["rows"] if row["type"] == "note"]
        joined = " ".join(notes)
        self.assertIn("No accessibility settings daemon", joined)
        self.assertIn("Orca is not installed", joined)
        self.assertIn("No on-screen keyboard", joined)
        keys = {row.get("key") for section in page["sections"] for row in section["rows"]}
        self.assertNotIn("launch_reader", keys)

    def test_probe_offers_launchers_when_installed(self):
        with mock.patch.object(accessibility, "osk_binary", return_value="/usr/bin/squeekboard"), \
             mock.patch.object(accessibility, "reader_binary", return_value="/usr/bin/orca"), \
             mock.patch.object(accessibility, "daemon_running", return_value="kaccess"), \
             mock.patch.object(util, "which", return_value=None):
            page = accessibility.probe()
        actions = [row["action"] for section in page["sections"]
                   for row in section["rows"] if row["type"] == "action"]
        self.assertIn("accessibility.launch_reader", actions)
        self.assertIn("accessibility.launch_osk", actions)

    def test_apply_writes_toggles_and_scaling(self):
        calls = []
        with mock.patch.object(util, "which", return_value="/usr/bin/gsettings"), \
             mock.patch.object(util, "run",
                               side_effect=lambda argv, **kw: calls.append(argv) or RunResult(0, "", "")):
            result = accessibility.apply({
                "text_scaling": 150,
                "sticky_keys": True,
                "animations": False,
                "high_contrast": True,
            })
        self.assertTrue(result["ok"])
        self.assertIn(["gsettings", "set", accessibility.INTERFACE,
                       "text-scaling-factor", "1.50"], calls)
        self.assertIn(["gsettings", "set", accessibility.A11Y_KB,
                       "sticky-keys-enable", "true"], calls)
        self.assertIn(["gsettings", "set", accessibility.INTERFACE,
                       "enable-animations", "false"], calls)
        self.assertIn(["gsettings", "set", accessibility.A11Y_IFACE,
                       "high-contrast", "true"], calls)

    def test_apply_accepts_a_preset(self):
        calls = []
        with mock.patch.object(util, "which", return_value="/usr/bin/gsettings"), \
             mock.patch.object(util, "run",
                               side_effect=lambda argv, **kw: calls.append(argv) or RunResult(0, "", "")):
            result = accessibility.apply({"preset": "115"})
        self.assertTrue(result["ok"])
        self.assertIn(["gsettings", "set", accessibility.INTERFACE,
                       "text-scaling-factor", "1.15"], calls)

    def test_apply_fails_without_gsettings(self):
        with mock.patch.object(util, "which", return_value=None):
            result = accessibility.apply({"sticky_keys": True})
        self.assertFalse(result["ok"])
        self.assertIn("gsettings", result["message"])

    def test_apply_reports_rejected_key(self):
        with mock.patch.object(util, "which", return_value="/usr/bin/gsettings"), \
             mock.patch.object(util, "run", return_value=RunResult(1, "", "no such key")):
            result = accessibility.apply({"mouse_keys": True})
        self.assertFalse(result["ok"])
        self.assertIn("mousekeys-enable", result["message"])

    def test_launch_actions(self):
        with mock.patch.object(accessibility, "reader_binary", return_value=""), \
             mock.patch.object(util, "spawn") as spawn:
            self.assertFalse(accessibility.action("accessibility.launch_reader", {})["ok"])
            spawn.assert_not_called()

        with mock.patch.object(accessibility, "reader_binary", return_value="/usr/bin/orca"), \
             mock.patch.object(accessibility, "osk_binary", return_value="/usr/bin/squeekboard"), \
             mock.patch.object(util, "spawn", return_value=True) as spawn:
            self.assertTrue(accessibility.action("accessibility.launch_reader", {})["ok"])
            self.assertTrue(accessibility.action("accessibility.launch_osk", {})["ok"])
        self.assertEqual([call.args[0] for call in spawn.call_args_list],
                         [["/usr/bin/orca"], ["/usr/bin/squeekboard"]])


if __name__ == "__main__":
    unittest.main()
