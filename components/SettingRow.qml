// One settings row: label and help on the left, a value or control on the right.
import QtQuick
import "../theme"

Item {
    id: row

    property string label: ""
    property string help: ""
    property string value: ""
    property bool mono: false
    property bool copyValue: false
    property bool separator: true
    default property alias control: controlRow.data

    width: parent ? parent.width : 0
    implicitHeight: Math.max(leftColumn.implicitHeight, host.implicitHeight, 24) + 16

    Column {
        id: leftColumn
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: Math.max(60, parent.width - host.width - 18)
        spacing: 2

        Text {
            width: parent.width
            text: row.label
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.size(2)
            elide: Text.ElideRight
        }
        Text {
            width: parent.width
            visible: row.help.length > 0
            text: row.help
            color: Theme.textFaint
            font.family: Theme.fontFamily
            font.pixelSize: Theme.size(1)
            wrapMode: Text.WordWrap
            lineHeight: 1.2
        }
    }

    Row {
        id: host
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8

        Text {
            id: valueText
            visible: row.value.length > 0
            anchors.verticalCenter: parent.verticalCenter
            text: row.value
            color: Theme.textMuted
            font.family: row.mono ? Theme.monoFamily : Theme.fontFamily
            font.pixelSize: row.mono ? Theme.size(1) : Theme.size(2)
            elide: Text.ElideMiddle
            width: Math.min(implicitWidth, 320)
            horizontalAlignment: Text.AlignRight
        }
        Row { id: controlRow; spacing: 8; anchors.verticalCenter: parent.verticalCenter }

        Rectangle {
            visible: row.copyValue && row.value.length > 0
            width: 24
            height: 24
            radius: 6
            color: copyHover.hovered ? Theme.surface3 : "transparent"
            anchors.verticalCenter: parent.verticalCenter
            Glyph { anchors.centerIn: parent; glyph: "\uf0c5"; pixelSize: Theme.size(1); dim: true }
            HoverHandler { id: copyHover }
            TapHandler {
                onTapped: {
                    clipboard.text = row.value;
                    clipboard.selectAll();
                    clipboard.copy();
                }
            }
        }
    }

    TextInput {
        id: clipboard
        visible: false
        width: 1; height: 1
    }

    Rectangle {
        visible: row.separator
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Theme.alpha(Theme.foreground, 0.06)
    }
}
