// Standalone settings window: a layer-shell panel, exactly like the bar's own
// Settings and Quick Settings dialogs. Layer surfaces are not decorated by the
// compositor — no border, shadow or rounding — so the only edge is the app's
// animated accent border. No anchors means wlr-layer-shell centres it.
import QtQuick
import Quickshell
import Quickshell.Wayland
import "../config"

PanelWindow {
    id: win

    visible: true
    color: "transparent"
    focusable: true
    exclusionMode: ExclusionMode.Ignore
    implicitWidth: Config.windowWidth
    implicitHeight: Config.windowHeight

    App {
        anchors.fill: parent
    }
}
