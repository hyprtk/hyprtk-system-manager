import QtQuick
import "../theme"

Item {
    id: root
    property bool checked: false
    signal toggled(bool checked)

    implicitWidth: 44
    implicitHeight: 24
    opacity: enabled ? 1 : 0.42

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: root.checked ? Theme.accent : Theme.surface3
        border.width: 1
        border.color: root.checked ? Theme.accent : Theme.alpha(Theme.foreground, 0.18)
        Behavior on color { ColorAnimation { duration: 120 } }

        Rectangle {
            width: 18
            height: 18
            radius: 9
            y: 2
            x: root.checked ? parent.width - width - 3 : 3
            color: root.checked ? Theme.textOnAccent : Theme.foreground
            Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
        }
    }

    TapHandler { enabled: root.enabled; onTapped: root.toggled(!root.checked) }
}
