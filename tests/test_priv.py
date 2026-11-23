import unittest
from unittest import mock

from system_manager import priv
from system_manager.util import RunResult


class PrivilegeTests(unittest.TestCase):
    def test_root_runs_directly(self):
        with mock.patch.object(priv, "euid", return_value=0), \
             mock.patch.object(priv, "run", return_value=RunResult(0, "ok")) as runner:
            result = priv.run_priv(["id"])
            runner.assert_called_once_with(["id"], input=None, timeout=120)
            self.assertTrue(result.ok)

    def test_sudo_is_preferred_when_passwordless(self):
        with mock.patch.object(priv, "euid", return_value=1000), \
             mock.patch.object(priv, "which", return_value="/usr/bin/sudo"), \
             mock.patch.object(priv, "run", return_value=RunResult(0, "")) as runner:
            priv.run_priv(["timedatectl", "set-timezone", "UTC"])
            runner.assert_called_with(["sudo", "-n", "timedatectl", "set-timezone", "UTC"],
                                      input=None, timeout=120)

    def test_pkexec_when_sudo_fails(self):
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv[:2] == ["sudo", "-n"]:
                return RunResult(1, "", "no")
            return RunResult(0, "")

        with mock.patch.object(priv, "euid", return_value=1000), \
             mock.patch.object(priv, "which", return_value="/usr/bin/pkexec"), \
             mock.patch.object(priv, "run", side_effect=fake_run):
            priv.run_priv(["timedatectl", "set-ntp", "true"])
        self.assertEqual(calls[0], ["sudo", "-n", "true"])
        self.assertEqual(calls[-1][0], "pkexec")

    def test_no_escalation_available(self):
        with mock.patch.object(priv, "euid", return_value=1000), \
             mock.patch.object(priv, "which", return_value=None):
            result = priv.run_priv(["id"])
        self.assertFalse(result.ok)
        self.assertIn("no privilege escalation", result.err)

    def test_command_for_labels(self):
        with mock.patch.object(priv, "euid", return_value=0):
            self.assertEqual(priv.command_for(["id"]), "id")
        with mock.patch.object(priv, "euid", return_value=1000), \
             mock.patch.object(priv, "which", return_value="/usr/bin/sudo"), \
             mock.patch.object(priv, "run", return_value=RunResult(0, "")):
            self.assertTrue(priv.command_for(["id"]).startswith("sudo "))
        with mock.patch.object(priv, "euid", return_value=1000), \
             mock.patch.object(priv, "which", return_value="/usr/bin/pkexec"), \
             mock.patch.object(priv, "run", return_value=RunResult(1, "")):
            self.assertTrue(priv.command_for(["id"]).startswith("pkexec "))


if __name__ == "__main__":
    unittest.main()
