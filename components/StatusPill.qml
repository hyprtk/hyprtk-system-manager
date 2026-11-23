import QtQuick
import "../theme"

Rectangle {
    id: pill
    property string text: ""
    property string tone: "neutral"

    readonly property var tones: ({
        neutral: Theme.textFaint,
        ok: Theme.ok,
        warn: Theme.warn,
        danger: Theme.danger,
        info: Theme.info,
        accent: Theme.accent,
    })
    readonly property color tint: tones[tone] || Theme.textFaint

    implicitWidth: label.implicitWidth + 16
    implicitHeight: 20
    radius: 10
    color: Theme.alpha(tint, 0.14)
    border.width: 1
    border.color: Theme.alpha(tint, 0.35)

    Text {
        id: label
        anchors.centerIn: parent
        text: pill.text.toUpperCase()
        color: pill.tint
        font.family: Theme.fontFamily
        font.pixelSize: Theme.size(0)
        font.letterSpacing: 0.6
        font.weight: Font.DemiBold
    }
}
