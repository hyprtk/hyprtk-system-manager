// Standalone settings window: a normal floating toplevel so SUPER+drag/resize
// work. The UI itself lives in App.qml.
import QtQuick
import Quickshell
import Quickshell.Hyprland
import "."
import "../config"

FloatingWindow {
    id: win

    visible: true
    color: "transparent"
    title: "System Settings"
    implicitWidth: Config.windowWidth
    implicitHeight: Config.windowHeight
    minimumSize: Qt.size(900, 620)

    onClosed: Qt.quit()

    property bool selfFloated: false

    function floatSelf() {
        if (selfFloated || !Hyprland.toplevels)
            return;
        const list = Hyprland.toplevels.values || [];
        for (const toplevel of list) {
            if (toplevel.title !== "System Settings")
                continue;
            let addr = String(toplevel.address || "");
            if (addr.length > 0 && addr.indexOf("0x") !== 0)
                addr = "0x" + addr;
            Hyprland.dispatch('hl.dsp.window.float({ window = "address:' + addr + '", action = "enable" })');
            Hyprland.dispatch('hl.dsp.window.center({ window = "address:' + addr + '" })');
            Hyprland.dispatch('hl.dsp.window.set_prop({ prop = "opacity", value = "1.0", window = "address:' + addr + '" })');
            Hyprland.dispatch('hl.dsp.window.set_prop({ prop = "opacity_inactive", value = "1.0", window = "address:' + addr + '" })');
            win.selfFloated = true;
            return;
        }
    }

    Connections {
        target: Hyprland.toplevels
        function onValuesChanged() { win.floatSelf(); }
    }

    Timer {
        interval: 400
        running: true
        repeat: false
        onTriggered: win.floatSelf()
    }

    App {
        anchors.fill: parent
    }
}
