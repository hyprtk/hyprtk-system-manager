import argparse
import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from system_manager import bus, cli


class QueueTests(unittest.TestCase):
    def setUp(self):
        bus.poll()

    def test_poll_drains_the_queue(self):
        bus._queue({"panel": "power", "row": "Battery"})
        self.assertEqual(bus.poll(), [{"panel": "power", "row": "Battery"}])
        self.assertEqual(bus.poll(), [])


class SocketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sm-bus-"))
        self.saved = bus.SOCKET
        bus.SOCKET = self.tmp / "bus.sock"
        bus._STARTED["socket"] = False
        bus.poll()

    def tearDown(self):
        bus.SOCKET = self.saved
        bus._STARTED["socket"] = False

    def test_send_without_a_listener_returns_none(self):
        self.assertIsNone(bus.send({"panel": "power"}))

    def test_socket_delivers_and_queues(self):
        started = bus.start()
        self.assertTrue(started["started"])
        self.assertTrue(bus.SOCKET.exists())
        self.assertEqual(bus.send({"panel": "power", "row": "Charge limit"}),
                         {"ok": True})
        for _ in range(50):
            items = bus.poll()
            if items:
                break
            time.sleep(0.02)
        self.assertEqual(items, [{"panel": "power", "row": "Charge limit"}])

    def test_stale_socket_is_replaced(self):
        bus.SOCKET.write_text("")
        started = bus.start()
        self.assertTrue(started["started"])
        self.assertTrue(bus.send({"panel": "about"}))

    def test_permissions_are_private(self):
        bus.start()
        self.assertEqual(bus.SOCKET.stat().st_mode & 0o777, 0o600)


class CliTests(unittest.TestCase):
    def _args(self, **overrides):
        base = dict(page="power", row="Charge limit", overlay=False,
                    foreground=False, new_window=False)
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_open_deep_links_into_the_running_window(self):
        with mock.patch.object(bus, "send", return_value={"ok": True}) as send, \
             mock.patch.object(cli.subprocess, "Popen") as popen:
            code = cli.cmd_open(self._args())
        self.assertEqual(code, 0)
        send.assert_called_with({"panel": "power", "row": "Charge limit"})
        popen.assert_not_called()

    def test_open_starts_a_window_when_nobody_listens(self):
        with mock.patch.object(bus, "send", return_value=None), \
             mock.patch.object(cli.subprocess, "Popen") as popen:
            popen.return_value = mock.Mock()
            code = cli.cmd_open(self._args())
        self.assertEqual(code, 0)
        env = popen.call_args[1]["env"]
        self.assertEqual(env["HYPRTK_SM_PAGE"], "power")
        self.assertEqual(env["HYPRTK_SM_ROW"], "Charge limit")
        self.assertEqual(env["QS_APP_ID"], "hyprtk-system-manager")

    def test_new_window_skips_the_bus(self):
        with mock.patch.object(bus, "send") as send, \
             mock.patch.object(cli.subprocess, "Popen") as popen:
            popen.return_value = mock.Mock()
            cli.cmd_open(self._args(new_window=True))
        send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
