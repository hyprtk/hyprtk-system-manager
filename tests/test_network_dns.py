import unittest
from unittest import mock

from system_manager import form, util
from system_manager.panels import network
from system_manager.util import RunResult

ACTIVE = "Wired connection 1:802-3-ethernet:enp7s0\nlo:loopback:lo\n"


class DnsValidationTests(unittest.TestCase):
    def test_addresses(self):
        self.assertEqual(network.validate_dns("1.1.1.1, 9.9.9.9"), [])
        self.assertEqual(network.validate_dns("2606:4700:4700::1111"), [])
        self.assertTrue(network.validate_dns("1.1.1.1, nope"))
        self.assertEqual(network.validate_dns(""), [])

    def test_search_domains(self):
        self.assertEqual(network.validate_search("lan, example.com"), [])
        self.assertTrue(network.validate_search("bad domain"))
        self.assertTrue(network.validate_search("-leading.com"))


class DnsStateTests(unittest.TestCase):
    def test_fields_come_in_the_requested_order(self):
        parsed = network.parse_dns_state(["auto", "1.1.1.1 9.9.9.9", "lan", "yes"])
        self.assertEqual(parsed["method"], "auto")
        self.assertEqual(parsed["dns"], "1.1.1.1 9.9.9.9")
        self.assertEqual(parsed["search"], "lan")
        self.assertTrue(parsed["ignore_auto"])

    def test_short_output_is_padded(self):
        parsed = network.parse_dns_state(["auto"])
        self.assertEqual(parsed["dns"], "")
        self.assertFalse(parsed["ignore_auto"])


class DnsApplyTests(unittest.TestCase):
    def test_modify_carries_the_values(self):
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)
            if argv[:4] == ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE"] or \
                    argv[:3] == ["nmcli", "-t", "-f"]:
                return RunResult(0, ACTIVE, "")
            if argv[:3] == ["nmcli", "-g", "NAME"]:
                return RunResult(0, "Wired connection 1\n", "")
            return RunResult(0, "", "")

        with mock.patch.object(util, "run", side_effect=run):
            result = network.apply({"dns_connection": "Wired connection 1",
                                    "dns_servers": "1.1.1.1, 9.9.9.9",
                                    "dns_search": "lan",
                                    "ignore_auto_dns": True})
        self.assertTrue(result["ok"], result)
        modify = next(call for call in calls
                      if call[:3] == ["nmcli", "connection", "modify"])
        self.assertEqual(modify, ["nmcli", "connection", "modify",
                                  "Wired connection 1",
                                  "ipv4.dns", "1.1.1.1, 9.9.9.9",
                                  "ipv4.dns-search", "lan",
                                  "ipv4.ignore-auto-dns", "yes"])

    def test_invalid_values_never_reach_nmcli(self):
        with mock.patch.object(util, "run", return_value=RunResult(0, ACTIVE, "")) as run:
            result = network.apply({"dns_connection": "Wired connection 1",
                                    "dns_servers": "not-an-ip"})
        self.assertFalse(result["ok"])
        self.assertFalse(any("modify" in call[0] for call in run.call_args_list))

    def test_unknown_connection_is_refused(self):
        def run(argv, **kwargs):
            if argv[:3] == ["nmcli", "-t", "-f"]:
                return RunResult(0, ACTIVE, "")
            if argv[:3] == ["nmcli", "-g", "NAME"]:
                return RunResult(1, "", "no such connection")
            return RunResult(0, "", "")

        with mock.patch.object(util, "run", side_effect=run):
            result = network.apply({"dns_connection": "Nope", "dns_servers": "1.1.1.1"})
        self.assertFalse(result["ok"])

    def test_preview_is_not_offered(self):
        self.assertEqual(getattr(network, "PREVIEW", ""), "")


class DnsProbeTests(unittest.TestCase):
    def test_section_present_with_an_active_connection(self):
        def run(argv, **kwargs):
            if argv[:2] == ["nmcli", "-t"]:
                return RunResult(0, ACTIVE, "")
            if argv[:3] == ["nmcli", "-g", "ipv4.method"]:
                return RunResult(0, "auto\n1.1.1.1\nlan\nno\n", "")
            return RunResult(0, "", "")

        with mock.patch.object(util, "which", return_value="/usr/bin/nmcli"), \
             mock.patch.object(util, "run", side_effect=run):
            page = network.probe()
        titles = [section["title"] for section in page["sections"]]
        self.assertIn("DNS", titles)
        keys = [row.get("key") for section in page["sections"] for row in section["rows"]]
        self.assertIn("dns_servers", keys)
        self.assertEqual(form.validate(page), [])
        self.assertEqual(page["status"], "full")


if __name__ == "__main__":
    unittest.main()
