import argparse
import json
import os
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
        # Every runtime file, or a test would touch the live session's bus.
        self.saved = (bus.SOCKET, bus.HEARTBEAT, bus.PIDFILE)
        bus.SOCKET = self.tmp / "bus.sock"
        bus.HEARTBEAT = self.tmp / "bus.heartbeat"
        bus.PIDFILE = self.tmp / "bus.pid"
        bus._STARTED["socket"] = False
        bus.poll()

    def tearDown(self):
        bus.SOCKET, bus.HEARTBEAT, bus.PIDFILE = self.saved
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

    def test_a_backend_with_a_window_gets_the_request(self):
        bus.start()
        with mock.patch.object(bus, "_surface_pids", return_value={os.getpid()}):
            self.assertEqual(bus.send({"panel": "power"}), {"ok": True})

    def test_a_backend_without_a_surface_is_reaped(self):
        """A layer surface can be unmapped by a monitor reload while the backend
        keeps answering; the next launch must not be swallowed."""
        bus.start()
        old = time.time() - 30
        os.utime(bus.PIDFILE, (old, old))
        with mock.patch.object(bus, "_surface_pids", return_value=set()):
            self.assertIsNone(bus.send({"panel": "power"}))
        self.assertFalse(bus.SOCKET.exists(), "the stranded socket should be gone")

    def test_a_stale_heartbeat_is_reaped(self):
        bus.start()
        old = time.time() - 60
        os.utime(bus.HEARTBEAT, (old, old))
        self.assertIsNone(bus.send({"panel": "power"}))

    def test_ownership_matches_only_our_processes(self):
        self.assertTrue(bus.is_ours_argv(["qs", "-p", "/home/u/.local/share/hyprtk-system-manager"]))
        self.assertTrue(bus.is_ours_argv(["python3", "-m", "system_manager.cli", "serve"]))
        # A shell whose -c string merely mentions the project path is not ours.
        self.assertFalse(bus.is_ours_argv(
            ["/usr/bin/zsh", "-c", "cd ~/Projects/AI-Projects/hyprtk-system-manager && python3 -m unittest"]))
        self.assertFalse(bus.is_ours_argv(["/usr/bin/qs", "-p", "/home/u/.config/quickshell/hyprtk-bar-qt"]))
        self.assertFalse(bus.is_ours_argv([]))

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
