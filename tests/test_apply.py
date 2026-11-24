import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from system_manager import jsonconf, paths, priv, util
from system_manager.panels import (
    appearance, datetime, displays, fonts, network, notifications, sound,
    suite, users,
)
from system_manager.util import RunResult


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sm-apply-"))
        self.saved = {
            "BAR_CONFIG": paths.BAR_CONFIG,
            "GTK3": paths.GTK3_SETTINGS,
            "GTK4": paths.GTK4_SETTINGS,
            "CONFIG_ROOT": paths.CONFIG_ROOT,
            "BACKUP_ROOT": paths.BACKUP_ROOT,
        }
        paths.BAR_CONFIG = self.tmp / "bar.json"
        paths.GTK3_SETTINGS = self.tmp / "gtk-3.0" / "settings.ini"
        paths.GTK4_SETTINGS = self.tmp / "gtk-4.0" / "settings.ini"
        paths.CONFIG_ROOT = self.tmp / "state"
        paths.BACKUP_ROOT = self.tmp / "state" / "backups"
        self.env = mock.patch.dict(os.environ, {"HOME": str(self.tmp)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        paths.BAR_CONFIG = self.saved["BAR_CONFIG"]
        paths.GTK3_SETTINGS = self.saved["GTK3"]
        paths.GTK4_SETTINGS = self.saved["GTK4"]
        paths.CONFIG_ROOT = self.saved["CONFIG_ROOT"]
        paths.BACKUP_ROOT = self.saved["BACKUP_ROOT"]

    def test_notifications_apply(self):
        result = notifications.apply({"max_stored": 75, "default_timeout": 4000})
        self.assertTrue(result["ok"])
        data = jsonconf.load()
        self.assertEqual(data["notifications"]["max_stored"], 75)
        self.assertEqual(data["notifications"]["default_timeout"], 4000)

    def test_suite_apply_writes_bar_keys(self):
        result = suite.apply({"bar_opacity": 0.8, "bar_border_width": 3,
                              "bar_font_size": 14, "bar_animations": "low"})
        self.assertTrue(result["ok"])
        data = jsonconf.load()
        self.assertEqual(data["opacity"], 0.8)
        self.assertEqual(data["border_width"], 3)
        self.assertEqual(data["font"]["size"], 14)
        self.assertEqual(data["animations"]["mode"], "low")

    def test_appearance_apply_writes_gtk(self):
        result = appearance.apply({
            "opacity": 0.9,
            "accent": "#ff0000",
            "icon_theme": "Papirus-Dark",
            "cursor_theme": "Adwaita",
            "cursor_size": 28,
        })
        self.assertTrue(result["ok"])
        data = jsonconf.load()
        self.assertEqual(data["opacity"], 0.9)
        self.assertEqual(data["theme"]["accent"], "#ff0000")
        gtk = paths.GTK3_SETTINGS.read_text()
        self.assertIn("gtk-icon-theme-name=Papirus-Dark", gtk)
        self.assertIn("gtk-cursor-theme-size=28", gtk)
        self.assertTrue((self.tmp / ".icons" / "default" / "index.theme").is_file())

    def test_appearance_clamps_opacity(self):
        appearance.apply({"opacity": 5})
        self.assertEqual(jsonconf.load()["opacity"], 1.0)
        appearance.apply({"opacity": -3})
        self.assertEqual(jsonconf.load()["opacity"], 0.4)

    def test_datetime_apply_uses_privilege(self):
        calls = []

        def fake(argv, **kwargs):
            calls.append(argv)
            return RunResult(0, "", "")

        with mock.patch.object(priv, "run_priv", side_effect=fake):
            result = datetime.apply({"timezone": "Europe/Paris", "ntp": True})
        self.assertTrue(result["ok"])
        self.assertIn(["timedatectl", "set-timezone", "Europe/Paris"], calls)
        self.assertIn(["timedatectl", "set-ntp", "true"], calls)

    def test_datetime_apply_reports_denied(self):
        with mock.patch.object(priv, "run_priv", return_value=RunResult(1, "", "denied")):
            result = datetime.apply({"timezone": "UTC"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["requires"], "root")

    def test_displays_apply_builds_monitor_spec(self):
        with mock.patch.object(util, "run", return_value=RunResult(0, "", "")) as runner:
            result = displays.action("displays.apply", {
                "name": "DP-1", "mode": "1920x1080@60.00", "scale": 1,
                "transform": 0, "x": 0, "y": 0,
            })
        self.assertTrue(result["ok"])
        argv = runner.call_args[0][0]
        self.assertEqual(argv[:3], ["hyprctl", "keyword", "monitor"])
        self.assertEqual(argv[3], "DP-1,1920x1080@60.00,0x0,1,0")

    def test_sound_apply_input_and_streams(self):
        calls = []

        def fake(argv, **kwargs):
            calls.append(argv)
            return RunResult(0, "", "")

        with mock.patch.object(util, "which", return_value="/usr/bin/wpctl"), \
             mock.patch.object(util, "run", side_effect=fake):
            result = sound.apply({
                "input_volume": 40, "input_muted": True,
                "stream.75.volume": 60, "stream.75.muted": True,
            })
        self.assertTrue(result["ok"])
        self.assertIn(["wpctl", "set-volume", "@DEFAULT_AUDIO_SOURCE@", "40%"], calls)
        self.assertIn(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "1"], calls)
        self.assertIn(["wpctl", "set-volume", "75", "60%"], calls)
        self.assertIn(["wpctl", "set-mute", "75", "1"], calls)

    def test_users_groups_and_shell_actions(self):
        calls = []

        def fake(argv, **kwargs):
            calls.append(argv)
            return RunResult(0, "", "")

        with mock.patch.object(priv, "run_priv", side_effect=fake), \
             mock.patch.object(users, "shells", return_value=["/bin/sh", "/bin/zsh"]):
            groups = users.action("users.groups", {"username": "kori", "groups": "wheel,audio"})
            shell = users.action("users.shell", {"username": "kori", "shell": "/bin/zsh"})
        self.assertTrue(groups["ok"])
        self.assertTrue(shell["ok"])
        self.assertIn(["usermod", "--groups", "wheel,audio", "kori"], calls)
        self.assertIn(["usermod", "--shell", "/bin/zsh", "kori"], calls)

    def test_fonts_install_copies_and_refreshes(self):
        with mock.patch.object(paths, "FONTS_DIR", self.tmp / "fonts"):
            source = self.tmp / "TestFont.ttf"
            source.write_bytes(b"not a real font")
            with mock.patch.object(util, "run", return_value=RunResult(0, "", "")) as runner:
                result = fonts.action("fonts.install", {"path": str(source)})
            self.assertTrue(result["ok"])
            self.assertTrue((self.tmp / "fonts" / "TestFont.ttf").is_file())
            runner.assert_called()

    def test_connect_open_network_has_no_password(self):
        calls = []

        def fake(argv, **kwargs):
            calls.append(argv)
            return RunResult(0, "", "")

        with mock.patch.object(util, "which", return_value="/usr/bin/nmcli"), \
             mock.patch.object(network, "_saved", return_value=[]), \
             mock.patch.object(util, "run", side_effect=fake):
            result = network.action("network.connect", {
                "ssid": "Cafe", "security": "", "device": "wlp6s0"})
        self.assertTrue(result["ok"])
        self.assertFalse(any("passwd-file" in argv for argv in calls))
        self.assertFalse(any("wifi-sec.key-mgmt" in argv for argv in calls))

    def test_connect_secured_uses_private_passwd_file(self):
        seen = {}
        calls = []

        def fake(argv, **kwargs):
            calls.append(argv)
            if "passwd-file" in argv:
                path = argv[argv.index("passwd-file") + 1]
                seen["content"] = Path(path).read_text()
                seen["mode"] = oct(Path(path).stat().st_mode & 0o777)
            return RunResult(0, "", "")

        with mock.patch.object(util, "which", return_value="/usr/bin/nmcli"), \
             mock.patch.object(network, "_saved", return_value=[]), \
             mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(self.tmp)}), \
             mock.patch.object(util, "run", side_effect=fake):
            result = network.action("network.connect", {
                "ssid": "Cafe", "security": "WPA2", "device": "wlp6s0",
                "password": "s3cret",
            })
        self.assertTrue(result["ok"])
        self.assertEqual(seen["content"], "802-11-wireless-security.psk:s3cret\n")
        self.assertEqual(seen["mode"], "0o600")
        for argv in calls:
            self.assertNotIn("s3cret", argv)
        self.assertEqual(list(self.tmp.glob("hyprtk-wifi-*")), [])

    def test_connect_failure_removes_new_profile(self):
        calls = []

        def fake(argv, **kwargs):
            calls.append(argv)
            if "delete" in argv:
                return RunResult(0, "", "")
            if "up" in argv:
                return RunResult(1, "", "denied")
            return RunResult(0, "", "")

        with mock.patch.object(util, "which", return_value="/usr/bin/nmcli"), \
             mock.patch.object(network, "_saved", return_value=[]), \
             mock.patch.object(util, "run", side_effect=fake):
            result = network.action("network.connect", {
                "ssid": "Cafe", "security": "", "device": "wlp6s0"})
        self.assertFalse(result["ok"])
        self.assertTrue(any(argv[:4] == ["nmcli", "connection", "delete", "id"] for argv in calls))

    def test_forget_connection(self):
        calls = []
        with mock.patch.object(util, "which", return_value="/usr/bin/nmcli"), \
             mock.patch.object(util, "run", side_effect=lambda argv, **kw: calls.append(argv) or RunResult(0)):
            result = network.action("network.forget", {"name": "Cafe"})
        self.assertTrue(result["ok"])
        self.assertEqual(calls[0], ["nmcli", "connection", "delete", "id", "Cafe"])

    def test_displays_persist_writes_managed_block(self):
        target = self.tmp / "monitors.lua"
        target.write_text('-- header\nhl.monitor({ output = "", mode = "preferred" })\n')
        with mock.patch.object(paths, "monitors_file", return_value=target), \
             mock.patch.object(util, "run", return_value=RunResult(0, "", "")):
            result = displays.action("displays.persist", {"monitors": [
                {"name": "DP-1", "mode": "1920x1080@60.00", "scale": 1,
                 "transform": 0, "x": 0, "y": 0},
            ]})
        self.assertTrue(result["ok"])
        text = target.read_text()
        self.assertIn(displays.START, text)
        self.assertIn(displays.END, text)
        self.assertIn('output = "DP-1"', text)
        self.assertIn("hl.monitor({ output = \"\", mode = \"preferred\" })", text)

        with mock.patch.object(paths, "monitors_file", return_value=target), \
             mock.patch.object(util, "run", return_value=RunResult(0, "", "")):
            displays.action("displays.clear_persistent", {})
        self.assertNotIn(displays.START, target.read_text())


if __name__ == "__main__":
    unittest.main()
