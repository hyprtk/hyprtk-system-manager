import unittest
from unittest import mock

from system_manager import form, priv, util
from system_manager.panels import privacy
from system_manager.util import RunResult

UFW_ACTIVE = """\
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere
"""

UFW_INACTIVE = "Status: inactive\n"


class UfwParseTests(unittest.TestCase):
    def test_active_with_rules(self):
        parsed = privacy.parse_ufw_status(UFW_ACTIVE)
        self.assertTrue(parsed["active"])
        self.assertEqual(parsed["rules"], ["22/tcp                     ALLOW IN    Anywhere"])

    def test_inactive(self):
        self.assertFalse(privacy.parse_ufw_status(UFW_INACTIVE)["active"])

    def test_headers_and_separators_are_skipped(self):
        parsed = privacy.parse_ufw_status(UFW_ACTIVE)
        self.assertFalse(any("Action" in rule for rule in parsed["rules"]))


class FlatpakParseTests(unittest.TestCase):
    def test_rows_are_parsed(self):
        text = ("Table        Object    App          Permissions\n"
                "devices      dri       org.example  all\n"
                "filesystems  host      org.example  read-only\n")
        rows = privacy.parse_flatpak_permissions(text)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["app"], "org.example")
        self.assertEqual(rows[0]["permissions"], "all")

    def test_header_line_is_skipped(self):
        rows = privacy.parse_flatpak_permissions("Table Object App Permissions\n")
        self.assertEqual(rows, [])


class CaptureParseTests(unittest.TestCase):
    def test_application_names_are_unique(self):
        text = ('Source Output #1\n\tapplication.name = "Firefox"\n'
                'Source Output #2\n\tapplication.name = "Firefox"\n'
                'Source Output #3\n\tapplication.name = "OBS"\n')
        self.assertEqual(privacy.parse_source_outputs(text), ["Firefox", "OBS"])

    def test_no_outputs(self):
        self.assertEqual(privacy.parse_source_outputs(""), [])


class FirewallActionTests(unittest.TestCase):
    def test_enable_when_inactive(self):
        with mock.patch.object(util, "which", return_value="/usr/bin/ufw"), \
             mock.patch.object(util, "run", return_value=RunResult(0, UFW_INACTIVE, "")), \
             mock.patch.object(priv, "run_priv", return_value=RunResult(0, "", "")) as run:
            result = privacy.action("privacy.firewall_toggle", {})
        self.assertTrue(result["ok"])
        run.assert_called_with(["ufw", "--force", "enable"], timeout=60,
                               action="privacy")

    def test_disable_when_active(self):
        with mock.patch.object(util, "which", return_value="/usr/bin/ufw"), \
             mock.patch.object(util, "run", return_value=RunResult(0, UFW_ACTIVE, "")), \
             mock.patch.object(priv, "run_priv", return_value=RunResult(0, "", "")) as run:
            privacy.action("privacy.firewall_toggle", {})
        run.assert_called_with(["ufw", "disable"], timeout=60, action="privacy")

    def test_denied_escalation_is_reported(self):
        with mock.patch.object(util, "which", return_value="/usr/bin/ufw"), \
             mock.patch.object(util, "run", return_value=RunResult(0, UFW_INACTIVE, "")), \
             mock.patch.object(priv, "run_priv",
                               return_value=RunResult(1, "", "denied")):
            result = privacy.action("privacy.firewall_toggle", {})
        self.assertFalse(result["ok"])
        self.assertEqual(result["requires"], "root")

    def test_flatpak_reset_rejects_a_path(self):
        self.assertFalse(privacy.action("privacy.flatpak_reset",
                                        {"app": "../etc/passwd"})["ok"])


class PrivacyPageTests(unittest.TestCase):
    def test_page_reports_firewall_state(self):
        with mock.patch.object(util, "which", side_effect=lambda name: "/usr/bin/" + name
                               if name in ("ufw", "pactl") else None), \
             mock.patch.object(util, "run", return_value=RunResult(0, UFW_ACTIVE, "")):
            model = privacy.probe()
        self.assertEqual(form.validate(model), [])
        labels = [row.get("label") for section in model["sections"]
                  for row in section["rows"]]
        self.assertIn("State", labels)
        self.assertEqual(model["status"], "full")


if __name__ == "__main__":
    unittest.main()
