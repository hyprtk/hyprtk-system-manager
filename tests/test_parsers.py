import unittest
from unittest import mock

from system_manager.panels import (
    bluetooth, datetime, displays, input as input_panel, network, printers,
    shortcuts, sound, storage, updates, users,
)

MONITOR_FIXTURE = [{
    "name": "DP-1",
    "description": "Samsung Electric Company C49J89x HNTR300215",
    "width": 3840,
    "height": 1080,
    "refreshRate": 59.968,
    "x": 0,
    "y": 0,
    "scale": 1,
    "transform": 0,
    "vrr": 1,
    "mirrorOf": "DP-2",
    "currentFormat": "XRGB8888",
    "colorManagementPreset": "srgb",
    "disabled": False,
    "availableModes": ["3840x1080@59.97Hz", "1920x1080@60.00Hz", "1920x1080@60.00Hz"],
}]


class ParserTests(unittest.TestCase):
    def test_displays(self):
        monitors = displays.parse_monitors(MONITOR_FIXTURE)
        self.assertEqual(len(monitors), 1)
        mon = monitors[0]
        self.assertEqual(mon["name"], "DP-1")
        self.assertEqual(mon["currentMode"], "3840x1080@59.97")
        self.assertEqual(mon["modes"][0]["label"], "3840×1080 @ 59.97 Hz")
        self.assertEqual(mon["vrr"], 1)
        self.assertEqual(mon["mirror"], "DP-2")
        self.assertEqual(mon["format"], "XRGB8888")
        self.assertEqual(mon["currentCm"], "srgb")
        self.assertEqual(len(mon["modes"]), 2)  # duplicate mode removed
        self.assertEqual(displays.parse_monitors("nope"), [])

    def test_timedatectl(self):
        state = datetime.parse_timedatectl(
            "Timezone=Europe/London\nLocalRTC=no\nNTP=yes\nNTPSynchronized=yes\n"
        )
        self.assertEqual(state["Timezone"], "Europe/London")
        self.assertEqual(state["NTP"], "yes")

    def test_passwd(self):
        text = (
            "root:x:0:0:root:/root:/bin/bash\n"
            "hyprtk:x:1000:1000:Kori Tk,/home/hyprtk:/home/hyprtk:/usr/bin/zsh\n"
            "nobody:x:65534:65534:nobody:/:/usr/bin/nologin\n"
        )
        found = users.parse_passwd(text)
        self.assertEqual([u["name"] for u in found], ["root", "hyprtk"])
        self.assertEqual(found[1]["fullname"], "Kori Tk")
        self.assertEqual(found[1]["shell"], "/usr/bin/zsh")

    def test_groups(self):
        self.assertEqual(users.parse_groups("wheel, audio video"), ["wheel", "audio", "video"])
        self.assertEqual(users.parse_groups(""), [])

    def test_wpctl(self):
        parsed = sound.parse_wpctl(
            "Audio\n"
            " ├─ Sinks:\n"
            " │  *   34. Starship Analog Stereo [vol: 1.00]\n"
            " │      61. HDMI Digital Stereo [vol: 0.40]\n"
            " ├─ Sources:\n"
            " │      46. Realtek USB MIC Mono [vol: 1.00]\n"
            " └─ Streams:\n"
            "        75. cava\n"
            "             76. input_FL        < ALCS1200A Analog:monitor_FL\t[active]\n"
            "        96. Brave\n"
            "             97. output_FL       > ALCS1200A Analog:playback_FL\t[active]\n"
        )
        self.assertEqual([s["id"] for s in parsed["sinks"]], [34, 61])
        self.assertTrue(parsed["sinks"][0]["default"])
        self.assertEqual(parsed["sinks"][1]["volume"], "0.40")
        self.assertEqual(parsed["sources"][0]["name"], "Realtek USB MIC Mono")
        self.assertEqual([stream["id"] for stream in parsed["streams"]], [75, 96])
        self.assertEqual(parsed["streams"][1]["name"], "Brave")

    def test_vpn_plugin_detection(self):
        # WireGuard is built into NetworkManager; OpenVPN needs a plugin file.
        import tempfile
        from pathlib import Path
        self.assertEqual(network.vpn_plugin("wireguard"), "built-in")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(network, "VPN_PLUGIN_DIRS", (str(root / "VPN"),)), \
                 mock.patch.object(network, "PLUGIN_ROOT", root):
                self.assertEqual(network.vpn_plugin("openvpn"), "")
                (root / "VPN").mkdir()
                (root / "VPN" / "nm-openvpn-service.name").write_text("x")
                self.assertTrue(network.vpn_plugin("openvpn").endswith("nm-openvpn-service.name"))

    def test_pactl_cards(self):
        parsed = sound.parse_cards(
            "Card #49\n"
            "\tName: alsa_card.pci-0000_0d_00.1\n"
            "\tProperties:\n"
            "\t\tdevice.description = \"Navi 21/23 HDMI/DP Audio Controller\"\n"
            "\tProfiles:\n"
            "\t\toff: Off (sinks: 0, sources: 0, priority: 0, available: yes)\n"
            "\t\toutput:hdmi-stereo: Digital Stereo (HDMI) Output (sinks: 1, sources: 0, priority: 5900, available: yes)\n"
            "\t\toutput:hdmi-stereo-extra1: Digital Stereo (HDMI 2) Output (sinks: 1, sources: 0, priority: 0, available: no)\n"
            "\tActive Profile: output:hdmi-stereo\n"
            "\tPorts:\n"
        )
        self.assertEqual(len(parsed), 1)
        card = parsed[0]
        self.assertEqual(card["name"], "alsa_card.pci-0000_0d_00.1")
        self.assertEqual(card["description"], "Navi 21/23 HDMI/DP Audio Controller")
        self.assertEqual(card["active"], "output:hdmi-stereo")
        self.assertEqual([p["id"] for p in card["profiles"]],
                         ["off", "output:hdmi-stereo", "output:hdmi-stereo-extra1"])
        self.assertEqual(card["profiles"][1]["label"], "Digital Stereo (HDMI) Output")
        self.assertFalse(card["profiles"][2]["available"])

    def test_nmcli(self):
        devices = network.parse_devices(
            "enp7s0:ethernet:connected:Wired connection 1\n"
            "lo:loopback:connected (externally):lo\n"
            "wlp6s0:wifi:unavailable:\n"
        )
        self.assertEqual(devices[0]["connection"], "Wired connection 1")
        self.assertEqual(len(devices), 3)
        wifi = network.parse_wifi("*:HomeNet:82:WPA2\n :OtherNet:41:WPA2\n")
        self.assertTrue(wifi[0]["active"])
        self.assertEqual(wifi[0]["signal"], 82)
        self.assertEqual(wifi[0]["security"], "WPA2")
        connections = network.parse_connections(
            "HomeNet:wifi:wlp6s0\nCafe:wifi:\nWired:ethernet:enp7s0\n")
        self.assertEqual([c["name"] for c in connections], ["HomeNet", "Cafe"])
        self.assertTrue(connections[0]["active"])
        self.assertFalse(connections[1]["active"])
        self.assertEqual(connections[0]["type"], "wifi")
        vpn = network.parse_connections("Work:vpn:\nWG:wireguard:\nHome:wifi:\n",
                                        kinds=("vpn", "wireguard"))
        self.assertEqual([item["name"] for item in vpn], ["Work", "WG"])
        self.assertEqual(vpn[1]["type"], "wireguard")

    def test_lsblk(self):
        payload = {"blockdevices": [
            {"name": "sda", "type": "disk", "size": "2.7T", "children": [
                {"name": "sda1", "type": "part", "mountpoint": "/mnt/Docs", "fstype": "ntfs"},
            ]},
        ]}
        devices = storage.parse_lsblk(payload)
        self.assertEqual([d["name"] for d in devices], ["sda", "sda1"])
        self.assertEqual(devices[1]["depth"], 1)
        self.assertEqual(storage.parse_lsblk(None), [])

    def test_checkupdates(self):
        found = updates.parse_checkupdates(
            "linux 6.17.1-arch1-1 -> 6.17.2-arch1-1\n"
            "hyprland 0.57.2-1 -> 0.58.0-1\n"
            "garbage line\n"
        )
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]["name"], "linux")
        self.assertEqual(found[0]["new"], "6.17.2-arch1-1")
        self.assertEqual(found[1]["old"], "0.57.2-1")

    def test_keybindings(self):
        text = (
            'local mainMod = "SUPER"\n'
            'hl.bind(mainMod .. " + RETURN", hl.dsp.exec_cmd("sh -c \'p=$HOME/.local/bin/hyprtk-term; exec alacritty\'"))\n'
            'hl.bind(mainMod .. " + Q", hl.dsp.window.close())\n'
            'hl.bind(mainMod .. " + J", hl.dsp.layout("togglesplit"), { description = "Toggle split" })\n'
        )
        binds = shortcuts.parse_binds(text)
        self.assertEqual(len(binds), 3)
        self.assertEqual(binds[0]["keys"], "SUPER + RETURN")
        self.assertEqual(binds[0]["action"], "hyprtk-term")
        self.assertEqual(binds[2]["description"], "Toggle split")

    def test_hyprctl_getoption(self):
        self.assertEqual(input_panel.parse_option("str: gb\nset: true\n"), "gb")
        self.assertEqual(input_panel.parse_option("int: 25\nset: false\n"), "25")
        self.assertEqual(input_panel.parse_option("garbage"), "")

    def test_bluetooth(self):
        state = bluetooth.parse_show("Controller BC:54\n\tPowered: no\n\tDiscoverable: no\n")
        self.assertEqual(state["Powered"], "no")
        devices = bluetooth.parse_devices("Device AA:BB:CC Headset\nDevice DD:EE:FF Mouse\n")
        self.assertEqual(devices[1]["name"], "Mouse")

    def test_printers(self):
        parsed = printers.parse_lpstat(
            "printer Office disabled since Mon - \n"
            "system default destination: Office\n"
        )
        self.assertEqual(parsed["queues"][0]["name"], "Office")
        self.assertEqual(parsed["default"], "Office")


if __name__ == "__main__":
    unittest.main()
