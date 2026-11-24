import unittest
from unittest import mock

from system_manager import util
from system_manager.panels import printers
from system_manager.util import RunResult

LPSTAT = """printer Office is idle.  enabled since Tue 24 Nov 2026
printer PDF is idle.  enabled since Tue 24 Nov 2026
system default destination: Office
"""

LPINFO_V = """file cups-pdf:/
network beh
network socket
network ipp
network https
direct hp:/usb/Office_jet?serial=ABC
"""

LPINFO_M = """drv:///sample.drv/dymo.ppd DYMO Label Printer
CUPS-PDF_noopt.ppd Generic CUPS-PDF Printer (no options)
everywhere Everywhere
"""


class ParserTests(unittest.TestCase):
    def test_lpstat(self):
        parsed = printers.parse_lpstat(LPSTAT)
        self.assertEqual([q["name"] for q in parsed["queues"]], ["Office", "PDF"])
        self.assertEqual(parsed["default"], "Office")
        self.assertIn("idle", parsed["queues"][0]["state"])

    def test_lpinfo_devices_skip_bare_backends(self):
        devices = printers.parse_lpinfo_v(LPINFO_V)
        self.assertEqual([d["uri"] for d in devices],
                         ["cups-pdf:/", "hp:/usb/Office_jet?serial=ABC"])

    def test_lpinfo_models(self):
        models = printers.parse_lpinfo_m(LPINFO_M)
        self.assertEqual(models[0]["id"], "drv:///sample.drv/dymo.ppd")
        self.assertEqual(models[0]["label"], "DYMO Label Printer")


class ProbeTests(unittest.TestCase):
    def _probe(self, *, lpstat=LPSTAT):
        def fake_run(argv, **kwargs):
            if argv[:2] == ["lpstat", "-p"]:
                return RunResult(0, lpstat, "")
            if argv[:2] == ["lpinfo", "-v"]:
                return RunResult(0, LPINFO_V, "")
            if argv[:2] == ["lpinfo", "-m"]:
                return RunResult(0, LPINFO_M, "")
            if argv[:1] == ["systemctl"]:
                return RunResult(0, "active\n", "")
            return RunResult(0, "", "")

        with mock.patch.object(util, "which", return_value="/usr/bin/lpstat"), \
             mock.patch.object(util, "run", side_effect=fake_run):
            return printers.probe()

    def test_queues_offer_actions_and_skip_default_switch(self):
        page = self._probe()
        items = {row["items"][0]["title"]: row["items"][0]
                 for row in page["sections"][0]["rows"] if row["type"] == "list"}
        office = [row for section in page["sections"] for row in section["rows"]
                  if row["type"] == "list"][0]["items"]
        default = next(item for item in office if item["title"] == "Office")
        other = next(item for item in office if item["title"] == "PDF")
        self.assertEqual(default["badges"], ["default"])
        self.assertNotIn("printers.default", [a["action"] for a in default["actions"]])
        self.assertIn("printers.default", [a["action"] for a in other["actions"]])
        remove = [a for a in other["actions"] if a["action"] == "printers.remove"][0]
        self.assertTrue(remove["danger"])
        self.assertEqual(remove["confirm"], "PDF")
        self.assertEqual(page["status"], "partial")

    def test_add_form_defaults_to_driverless(self):
        rows = {row.get("key"): row for section in self._probe()["sections"]
                for row in section["rows"]}
        self.assertEqual(rows["new_model"]["value"], "everywhere")
        self.assertEqual(rows["new_device"]["value"], "cups-pdf:/")
        self.assertIn("new_uri", rows)


class ActionTests(unittest.TestCase):
    def test_add_builds_lpadmin(self):
        calls = []
        with mock.patch.object(printers.priv, "run_priv",
                               side_effect=lambda argv, **kw: calls.append(argv) or RunResult(0, "", "")):
            result = printers.apply({
                "new_name": "Office",
                "new_device": "cups-pdf:/",
                "new_model": "everywhere",
                "new_location": "Desk",
                "new_description": "Colour",
            })
        self.assertTrue(result["ok"])
        self.assertEqual(calls[0], ["lpadmin", "-p", "Office", "-E", "-v", "cups-pdf:/",
                                    "-m", "everywhere", "-D", "Colour", "-L", "Desk"])

    def test_add_prefers_typed_uri(self):
        calls = []
        with mock.patch.object(printers.priv, "run_priv",
                               side_effect=lambda argv, **kw: calls.append(argv) or RunResult(0, "", "")):
            printers.apply({"new_name": "Net", "new_device": "cups-pdf:/",
                            "new_uri": "ipp://10.0.0.5/ipp/print"})
        self.assertIn("ipp://10.0.0.5/ipp/print", calls[0])
        self.assertNotIn("cups-pdf:/", calls[0])

    def test_add_validates_name_and_uri(self):
        self.assertFalse(printers.apply({"new_name": ""})["ok"])
        self.assertFalse(printers.apply({"new_name": "My Printer", "new_device": "cups-pdf:/"})["ok"])
        self.assertFalse(printers.apply({"new_name": "Office", "new_device": ""})["ok"])

    def test_add_denied_reports_root(self):
        with mock.patch.object(printers.priv, "run_priv",
                               return_value=RunResult(1, "", "denied")):
            result = printers.apply({"new_name": "Office", "new_device": "cups-pdf:/"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["requires"], "root")

    def test_remove_and_default(self):
        calls = []
        with mock.patch.object(printers.priv, "run_priv",
                               side_effect=lambda argv, **kw: calls.append(argv) or RunResult(0, "", "")):
            self.assertTrue(printers.action("printers.remove", {"name": "PDF"})["ok"])
            self.assertTrue(printers.action("printers.default", {"name": "PDF"})["ok"])
        self.assertEqual(calls, [["lpadmin", "-x", "PDF"], ["lpadmin", "-d", "PDF"]])

    def test_test_page_uses_lp(self):
        calls = []
        with mock.patch.object(util, "run",
                               side_effect=lambda argv, **kw: calls.append(argv) or RunResult(0, "", "")):
            result = printers.action("printers.test", {"name": "Office"})
        self.assertTrue(result["ok"])
        self.assertEqual(calls[0][:3], ["lp", "-d", "Office"])
        self.assertTrue(calls[0][3].endswith("default-testpage.pdf"))

    def test_open_cups_interface(self):
        with mock.patch.object(util, "spawn", return_value=True) as spawn:
            result = printers.action("printers.open_cups", {})
        self.assertTrue(result["ok"])
        self.assertEqual(spawn.call_args.args[0], ["xdg-open", "http://localhost:631"])


if __name__ == "__main__":
    unittest.main()
