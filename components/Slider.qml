import QtQuick
import "../theme"

Item {
    id: root

    property real value: 0
    property real from: 0
    property real to: 100
    property real step: 1
    property bool mono: false
    signal moved(real value)

    implicitWidth: 220
    implicitHeight: 28

    readonly property real ratio:
        (root.to - root.from) !== 0
            ? Math.max(0, Math.min(1, (root.value - root.from) / (root.to - root.from)))
            : 0

    Rectangle {
        id: track
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width
        height: 4
        radius: 2
        color: Theme.surface3
    }
    Rectangle {
        anchors.verticalCenter: track.verticalCenter
        width: root.ratio * track.width
        height: 4
        radius: 2
        color: Theme.accent
    }
    Text {
        anchors.right: parent.right
        anchors.bottom: parent.top
        anchors.bottomMargin: -2
        text: root.mono ? root.value : Math.round(root.value) + "%"
        color: Theme.textFaint
        font.family: root.mono ? Theme.monoFamily : Theme.fontFamily
        font.pixelSize: Theme.size(0)
        visible: false
    }
    Rectangle {
        id: handle
        width: 16
        height: 16
        radius: 8
        color: Theme.accent
        border.width: 2
        border.color: Theme.background
        y: (root.height - height) / 2
        x: Math.max(0, Math.min(root.width - width, root.ratio * (root.width - width)))
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        function setFromX(px) {
            const span = root.width - handle.width;
            if (span <= 0)
                return;
            const ratio = Math.max(0, Math.min(1, (px - handle.width / 2) / span));
            let next = root.from + ratio * (root.to - root.from);
            if (root.step > 0)
                next = Math.round(next / root.step) * root.step;
            next = Math.max(root.from, Math.min(root.to, next));
            root.moved(next);
        }
        onPressed: (mouse) => setFromX(mouse.x)
        onPositionChanged: (mouse) => { if (pressed) setFromX(mouse.x); }
    }
}
