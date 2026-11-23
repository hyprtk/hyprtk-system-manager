import QtQuick
import "../theme"

Rectangle {
    id: item
    property string glyph: ""
    property string label: ""
    property bool active: false
    property int count: -1
    signal clicked()

    width: parent ? parent.width : 0
    height: 34
    radius: Theme.radiusSm
    color: item.active ? Theme.alpha(Theme.accent, 0.22)
         : (hover.hovered ? Theme.alpha(Theme.foreground, 0.06) : "transparent")

    Rectangle {
        visible: item.active
        width: 3
        height: 16
        radius: 2
        color: Theme.accent
        anchors.left: parent.left
        anchors.leftMargin: 2
        anchors.verticalCenter: parent.verticalCenter
    }

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 14
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10

        Glyph {
            glyph: item.glyph
            pixelSize: Theme.size(2)
            color: item.active ? Theme.accent : Theme.textMuted
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            id: labelText
            width: parent.width - 42
            text: item.label
            color: item.active ? Theme.text : Theme.textMuted
            font.family: Theme.fontFamily
            font.pixelSize: Theme.size(2)
            font.weight: item.active ? Font.DemiBold : Font.Normal
            elide: Text.ElideRight
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    HoverHandler { id: hover }
    TapHandler { onTapped: item.clicked() }
}
