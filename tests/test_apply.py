import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from system_manager import jsonconf, paths, priv, util
from system_manager.panels import (
    appearance, datetime, displays, fonts,
    input as input_panel, network, notifications, sound,
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

    def test_appearance_theme_writes_both_representations(self):
        # The bar reads the flat `themeAccent` override first and the nested
        # `theme` block second; writing only one leaves them divergent.
        with mock.patch.object(util, "which", return_value=None):
            result = appearance.apply({"accent": "#ff0000", "source": "manual"})
        self.assertTrue(result["ok"])
        data = jsonconf.load()
        self.assertEqual(data["themeAccent"], "#ff0000")
        self.assertEqual(data["theme"]["accent"], "#ff0000")
        self.assertEqual(data["themeSource"], "manual")
        self.assertEqual(data["theme"]["source"], "manual")

    def test_appearance_pywal_clears_colour_overrides(self):
        with mock.patch.object(util, "which", return_value=None):
            appearance.apply({"accent": "#ff0000", "source": "manual"})
            appearance.apply({"source": "pywal"})
        data = jsonconf.load()
        self.assertEqual(data["themeSource"], "pywal")
        self.assertEqual(data["themeAccent"], "")
        self.assertEqual(data["themeBackground"], "")
        # The nested block keeps the last manual palette for a later switch back.
        self.assertEqual(data["theme"]["accent"], "#ff0000")

    def test_appearance_probe_prefers_the_flat_override(self):
        jsonconf.patch({"themeAccent": "#00ff00",
                        "theme": {"accent": "#ff0000", "source": "manual"}})
        with mock.patch.object(util, "which", return_value=None):
            page = appearance.probe()
        rows = {row.get("key"): row for section in page["sections"]
                for row in section["rows"]}
        self.assertEqual(rows["accent"]["value"], "#00ff00")

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

    def _live_monitor(self):
        return [{
            "name": "DP-1", "currentMode": "3840x1080@59.97", "scale": 1.0,
            "transform": 0, "x": 0, "y": 0, "vrr": 0, "mirror": "",
            "disabled": False, "width": 3840, "height": 1080, "refreshRate": 59.97,
        }]

    def test_displays_apply_writes_layout(self):
        target = self.tmp / "monitors.lua"
        target.write_text("-- base\n")
        with mock.patch.object(displays, "_live_monitors", return_value=self._live_monitor()), \
             mock.patch.object(paths, "monitors_file", return_value=target), \
             mock.patch.object(util, "run", return_value=RunResult(0, "", "")) as runner:
            result = displays.action("displays.apply", {
                "name": "DP-1", "mode": "1920x1080@60.00", "scale": 1,
                "transform": 0, "vrr": 1, "mirror": "DP-2",
                "bitdepth": "10", "cm": "hdr", "x": 0, "y": 0,
            })
        self.assertTrue(result["ok"])
        text = target.read_text()
        self.assertIn('mode = "1920x1080@60.00"', text)
        self.assertIn("vrr = 1", text)
        self.assertIn('mirror = "DP-2"', text)
        self.assertIn("bitdepth = 10", text)
        self.assertIn('cm = "hdr"', text)
        self.assertTrue(any(call[0][0][:2] == ["hyprctl", "reload"]
                            for call in runner.call_args_list))

    def test_displays_apply_refuses_disabling_last_monitor(self):
        target = self.tmp / "monitors.lua"
        target.write_text("-- base\n")
        with mock.patch.object(displays, "_live_monitors", return_value=self._live_monitor()), \
             mock.patch.object(paths, "monitors_file", return_value=target), \
             mock.patch.object(util, "run", return_value=RunResult(0, "", "")):
            result = displays.action("displays.apply", {"name": "DP-1", "disabled": True})
        self.assertFalse(result["ok"])
        self.assertEqual(target.read_text(), "-- base\n")

    def test_displays_persist_refuses_all_disabled(self):
        result = displays.action("displays.persist", {
            "monitors": [{"name": "DP-1", "disabled": True}],
        })
        self.assertFalse(result["ok"])

    def test_displays_reload_detects_unknown_request(self):
        with mock.patch.object(util, "run", return_value=RunResult(0, "unknown request", "")):
            result = displays.action("displays.reload", {})
        self.assertFalse(result["ok"])

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

    def test_sound_card_profile(self):
        calls = []

        def fake(argv, **kwargs):
            calls.append(argv)
            return RunResult(0, "", "")

        with mock.patch.object(util, "which", return_value="/usr/bin/wpctl"), \
             mock.patch.object(util, "run", side_effect=fake):
            result = sound.apply({
                "card::alsa_card.pci-0000_0d_00.1::profile": "off",
            })
        self.assertTrue(result["ok"])
        self.assertIn(["pactl", "set-card-profile", "alsa_card.pci-0000_0d_00.1", "off"], calls)

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

    def test_vpn_import_requires_the_plugin(self):
        path = self.tmp / "office.ovpn"
        path.write_text("client\n")
        with mock.patch.object(network, "vpn_plugin", return_value=""), \
             mock.patch.object(util, "run") as runner:
            result = network.action("network.vpn_import", {"path": str(path)})
        self.assertFalse(result["ok"])
        self.assertIn("OpenVPN", result["message"])
        runner.assert_not_called()

    def test_vpn_import_type_by_suffix(self):
        for suffix, kind in (("ovpn", "openvpn"), ("conf", "wireguard")):
            path = self.tmp / f"office.{suffix}"
            path.write_text("x")
            calls = []
            with mock.patch.object(util, "which", return_value="/usr/bin/nmcli"), \
                 mock.patch.object(network, "vpn_plugin", return_value="built-in"), \
                 mock.patch.object(util, "run",
                                   side_effect=lambda argv, **kw: calls.append(argv) or RunResult(0)):
                result = network.action("network.vpn_import", {"path": str(path)})
            self.assertTrue(result["ok"], suffix)
            self.assertIn(["nmcli", "connection", "import", "type", kind, "file", str(path)], calls)

    def test_vpn_actions(self):
        calls = []
        with mock.patch.object(util, "which", return_value="/usr/bin/nmcli"), \
             mock.patch.object(util, "run",
                               side_effect=lambda argv, **kw: calls.append(argv) or RunResult(0)):
            network.action("network.vpn_connect", {"name": "Work"})
            network.action("network.vpn_disconnect", {"name": "Work"})
            network.action("network.vpn_forget", {"name": "Work"})
        self.assertIn(["nmcli", "--wait", "30", "connection", "up", "id", "Work"], calls)
        self.assertIn(["nmcli", "connection", "down", "id", "Work"], calls)
        self.assertIn(["nmcli", "connection", "delete", "id", "Work"], calls)

    def test_forget_connection(self):
        calls = []
        with mock.patch.object(util, "which", return_value="/usr/bin/nmcli"), \
             mock.patch.object(util, "run", side_effect=lambda argv, **kw: calls.append(argv) or RunResult(0)):
            result = network.action("network.forget", {"name": "Cafe"})
        self.assertTrue(result["ok"])
        self.assertEqual(calls[0], ["nmcli", "connection", "delete", "id", "Cafe"])

    def test_input_persist_and_clear(self):
        target = self.tmp / "input.lua"
        target.write_text("-- base\nhl.config({ input = {} })\n")

        def fake(argv, **kwargs):
            if argv[:2] == ["hyprctl", "getoption"]:
                values = {
                    "input:kb_layout": "str: gb",
                    "input:kb_variant": "str: ",
                    "input:repeat_rate": "int: 25",
                    "input:repeat_delay": "int: 600",
                    "input:sensitivity": "float: 0.5",
                    "input:accel_profile": "str: flat",
                    "input:touchpad:natural_scroll": "bool: true",
                    "input:touchpad:tap-to-click": "bool: true",
                    "input:touchpad:disable_while_typing": "bool: false",
                }
                return RunResult(0, values.get(argv[2], ""), "")
            return RunResult(0, "", "")

        with mock.patch.object(paths, "input_file", return_value=target), \
             mock.patch.object(util, "run", side_effect=fake):
            result = input_panel.action("input.persist", {})
            self.assertTrue(result["ok"])
            text = target.read_text()
            self.assertIn(input_panel.START, text)
            self.assertIn('kb_layout = "gb"', text)
            self.assertIn("repeat_rate = 25", text)
            self.assertIn('accel_profile = "flat"', text)
            self.assertIn('natural_scroll = true', text)
            self.assertIn('["tap-to-click"] = true', text)
            self.assertIn('disable_while_typing = false', text)
            self.assertIn("-- base", text)

            cleared = input_panel.action("input.clear_persistent", {})
            self.assertTrue(cleared["ok"])
            self.assertNotIn(input_panel.START, target.read_text())
            self.assertIn("-- base", target.read_text())

    def test_input_apply_writes_the_block_and_reloads(self):
        target = self.tmp / "input.lua"
        original = "-- base\nhl.config({ input = {} })\n"
        target.write_text(original)
        calls = []

        def fake(argv, **kwargs):
            calls.append(argv)
            if argv[:2] == ["hyprctl", "getoption"]:
                values = {
                    "input:kb_layout": "str: gb",
                    "input:kb_variant": "str: ",
                    "input:repeat_rate": "int: 25",
                    "input:repeat_delay": "int: 600",
                    "input:sensitivity": "float: 0",
                    "input:accel_profile": "str: ",
                    "input:touchpad:natural_scroll": "bool: false",
                    "input:touchpad:tap-to-click": "bool: true",
                    "input:touchpad:disable_while_typing": "bool: true",
                }
                return RunResult(0, values.get(argv[2], ""), "")
            return RunResult(0, "ok", "")

        with mock.patch.object(paths, "input_file", return_value=target), \
             mock.patch.object(util, "run", side_effect=fake):
            result = input_panel.apply({"repeat_rate": 31, "kb_layout": "de"})

        self.assertTrue(result["ok"])
        text = target.read_text()
        self.assertIn(input_panel.START, text)
        self.assertIn("repeat_rate = 31", text)
        self.assertIn('kb_layout = "de"', text)
        self.assertIn("tap-to-click\"] = true", text)
        # No runtime keyword: the change must go through the file and a reload.
        self.assertFalse(any(argv[:2] == ["hyprctl", "keyword"] for argv in calls))
        self.assertIn(["hyprctl", "reload"], calls)

    def test_input_apply_clamps_and_restores_on_rejection(self):
        target = self.tmp / "input.lua"
        original = "-- base\nhl.config({ input = {} })\n"

        def fake(argv, **kwargs):
            if argv[:2] == ["hyprctl", "getoption"]:
                return RunResult(0, "int: 25", "")
            if argv[:2] == ["hyprctl", "reload"]:
                return RunResult(0, "unknown request", "")
            return RunResult(0, "", "")

        target.write_text(original)
        with mock.patch.object(paths, "input_file", return_value=target), \
             mock.patch.object(util, "run", side_effect=fake):
            result = input_panel.apply({"repeat_rate": 0})
        self.assertFalse(result["ok"])
        self.assertIn("unknown request", result["message"])
        self.assertEqual(target.read_text(), original)

    def test_input_persist_restores_on_reload_failure(self):
        target = self.tmp / "input.lua"
        original = "-- base\nhl.config({ input = {} })\n"
        target.write_text(original)

        def fake(argv, **kwargs):
            if argv[:2] == ["hyprctl", "getoption"]:
                values = {
                    "input:kb_layout": "str: gb",
                    "input:kb_variant": "str: ",
                    "input:repeat_rate": "int: 25",
                    "input:repeat_delay": "int: 600",
                    "input:sensitivity": "float: 0",
                    "input:accel_profile": "str: ",
                    "input:touchpad:natural_scroll": "bool: false",
                    "input:touchpad:tap-to-click": "bool: false",
                    "input:touchpad:disable_while_typing": "bool: true",
                }
                return RunResult(0, values.get(argv[2], ""), "")
            if argv[:2] == ["hyprctl", "reload"]:
                return RunResult(1, "", "bad config")
            return RunResult(0, "", "")

        with mock.patch.object(paths, "input_file", return_value=target), \
             mock.patch.object(util, "run", side_effect=fake):
            result = input_panel.action("input.persist", {})
        self.assertFalse(result["ok"])
        self.assertEqual(target.read_text(), original)

    def test_displays_persist_writes_managed_block(self):
        target = self.tmp / "monitors.lua"
        target.write_text('-- header\nhl.monitor({ output = "", mode = "preferred" })\n')
        with mock.patch.object(paths, "monitors_file", return_value=target), \
             mock.patch.object(util, "run", return_value=RunResult(0, "", "")):
            result = displays.action("displays.persist", {"monitors": [
                {"name": "DP-1", "mode": "1920x1080@60.00", "scale": 1,
                 "transform": 0, "vrr": 1, "mirror": "DP-2",
                 "bitdepth": "10", "cm": "hdr", "x": 0, "y": 0},
            ]})
        self.assertTrue(result["ok"])
        text = target.read_text()
        self.assertIn(displays.START, text)
        self.assertIn(displays.END, text)
        self.assertIn('output = "DP-1"', text)
        self.assertIn("vrr = 1", text)
        self.assertIn('mirror = "DP-2"', text)
        self.assertIn("bitdepth = 10", text)
        self.assertIn('cm = "hdr"', text)
        self.assertIn("hl.monitor({ output = \"\", mode = \"preferred\" })", text)

        with mock.patch.object(paths, "monitors_file", return_value=target), \
             mock.patch.object(util, "run", return_value=RunResult(0, "", "")):
            displays.action("displays.clear_persistent", {})
        self.assertNotIn(displays.START, target.read_text())


if __name__ == "__main__":
    unittest.main()
