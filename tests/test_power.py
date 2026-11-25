import tempfile
import unittest
from pathlib import Path
from unittest import mock

from system_manager import form, priv, util
from system_manager.panels import power
from system_manager.util import RunResult

PPD_LIST = """\
  performance:
    Driver:     amd_pstate
    Platform driver: amd-pstate
  balanced:
    Driver:     amd_pstate
* power-saver:
    Driver:     amd_pstate
"""


class ParsePowerProfilesTests(unittest.TestCase):
    def test_marker_marks_the_active_profile(self):
        choices, active = power.parse_powerprofiles(PPD_LIST)
        self.assertEqual(active, "power-saver")
        self.assertEqual([item["value"] for item in choices],
                         ["performance", "balanced", "power-saver"])

    def test_driver_lines_are_ignored(self):
        choices, _ = power.parse_powerprofiles(PPD_LIST)
        self.assertNotIn("Driver", [item["value"] for item in choices])

    def test_empty_output_has_no_choices(self):
        self.assertEqual(power.parse_powerprofiles(""), ([], ""))


class PowerApplyTests(unittest.TestCase):
    def test_profile_apply_calls_powerprofilesctl(self):
        with mock.patch.object(util, "which", return_value="/usr/bin/powerprofilesctl"), \
             mock.patch.object(util, "run", return_value=RunResult(0, "", "")) as run:
            result = power.apply({"ppd_profile": "balanced"})
        self.assertTrue(result["ok"])
        run.assert_called_with(["powerprofilesctl", "set", "balanced"], timeout=20)

    def test_unknown_profile_is_refused(self):
        with mock.patch.object(util, "which", return_value="/usr/bin/powerprofilesctl"):
            result = power.apply({"ppd_profile": "turbo"})
        self.assertFalse(result["ok"])

    def test_missing_powerprofilesctl_is_refused(self):
        with mock.patch.object(util, "which", return_value=None):
            result = power.apply({"ppd_profile": "balanced"})
        self.assertFalse(result["ok"])
        self.assertIn("not installed", result["message"])

    def test_charge_limit_writes_the_kernel_threshold(self):
        tmp = Path(tempfile.mkdtemp(prefix="sm-batt-"))
        (tmp / "charge_control_end_threshold").write_text("100\n")
        entry = {"name": "BAT0", "type": "Battery", "online": "", "capacity": "80",
                 "status": "Discharging", "path": tmp}
        with mock.patch.object(power, "_supplies", return_value=[entry]), \
             mock.patch.object(priv, "run_priv", return_value=RunResult(0, "", "")) as run:
            result = power.apply({"charge_limit::BAT0": 80})
        self.assertTrue(result["ok"])
        target = str(tmp / "charge_control_end_threshold")
        run.assert_called_with(["tee", target], input="80\n", timeout=30,
                               action="power")

    def test_charge_limit_reports_a_denied_write(self):
        tmp = Path(tempfile.mkdtemp(prefix="sm-batt-"))
        (tmp / "charge_control_end_threshold").write_text("100\n")
        entry = {"name": "BAT0", "type": "Battery", "online": "", "capacity": "80",
                 "status": "Discharging", "path": tmp}
        with mock.patch.object(power, "_supplies", return_value=[entry]), \
             mock.patch.object(priv, "run_priv", return_value=RunResult(1, "", "denied")):
            result = power.apply({"charge_limit::BAT0": 60})
        self.assertFalse(result["ok"])
        self.assertEqual(result["requires"], "root")

    def test_battery_health_and_threshold_rows(self):
        tmp = Path(tempfile.mkdtemp(prefix="sm-batt-"))
        (tmp / "energy_full").write_text("48000000\n")
        (tmp / "energy_full_design").write_text("60000000\n")
        (tmp / "charge_control_end_threshold").write_text("85\n")
        (tmp / "cycle_count").write_text("132\n")
        entry = {"name": "BAT0", "type": "Battery", "online": "", "capacity": "80",
                 "status": "Discharging", "path": tmp}
        rows = power._battery_rows(entry)
        values = [row.get("value") for row in rows]
        self.assertIn("80% of design capacity", values)
        self.assertIn("132", values)
        slider = next(row for row in rows if row["type"] == "slider")
        self.assertEqual(slider["key"], "charge_limit::BAT0")
        self.assertEqual(slider["value"], 85)


class PowerPageTests(unittest.TestCase):
    def test_page_with_a_battery_and_profiles(self):
        tmp = Path(tempfile.mkdtemp(prefix="sm-batt-"))
        entry = {"name": "BAT0", "type": "Battery", "online": "", "capacity": "80",
                 "status": "Charging", "path": tmp}
        with mock.patch.object(power, "_supplies", return_value=[entry]), \
             mock.patch.object(power, "_power_profiles",
                               return_value={"available": True,
                                             "choices": [{"value": "balanced",
                                                          "label": "Balanced"}],
                                             "active": "balanced"}):
            model = power.probe()
        self.assertEqual(form.validate(model), [])
        self.assertEqual(model["status"], "full")
        keys = [row.get("key") for section in model["sections"]
                for row in section["rows"]]
        self.assertIn("ppd_profile", keys)


if __name__ == "__main__":
    unittest.main()
