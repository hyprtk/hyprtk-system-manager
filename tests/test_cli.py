import unittest

from system_manager.cli import _action_name


class CliTests(unittest.TestCase):
    def test_short_action_names_are_prefixed(self):
        self.assertEqual(_action_name("users", "create"), "users.create")
        self.assertEqual(_action_name("users", "lock"), "users.lock")

    def test_qualified_actions_are_kept(self):
        self.assertEqual(_action_name("users", "users.create"), "users.create")
        self.assertEqual(_action_name("displays", "panel.refresh"), "panel.refresh")

    def test_empty_name(self):
        self.assertEqual(_action_name("users", ""), "")


if __name__ == "__main__":
    unittest.main()
