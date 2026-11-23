// hyprtk-system-manager — Quickshell entry point.
// HYPRTK_SM_OVERLAY=1 opens the layer-shell overlay used by the bar; otherwise
// the standalone floating window is used. The source strings keep the
// layer-shell type out of the tree when it is not needed (off-screen QA runs
// have no Wayland backend, and PanelWindow cannot load there).
import QtQuick
import Quickshell
import "config"
import "surface"

ShellRoot {
    Loader {
        source: Config.overlayMode ? "surface/Overlay.qml" : "surface/MainWindow.qml"
    }
}
