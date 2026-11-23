import unittest

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
        )
        self.assertEqual([s["id"] for s in parsed["sinks"]], [34, 61])
        self.assertTrue(parsed["sinks"][0]["default"])
        self.assertEqual(parsed["sinks"][1]["volume"], "0.40")
        self.assertEqual(parsed["sources"][0]["name"], "Realtek USB MIC Mono")

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
