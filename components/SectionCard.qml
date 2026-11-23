// A titled group of rows. The suite's settings language: surface card, a small
// uppercase title, optional explanation, then full-width rows.
import QtQuick
import "../theme"

Rectangle {
    id: card

    property string title: ""
    property string description: ""
    default property alias body: rows.data

    width: parent ? parent.width : 0
    implicitHeight: column.implicitHeight + 32
    radius: Theme.radiusMd
    color: Theme.alpha(Theme.surface1, 0.66)
    border.width: 1
    border.color: Theme.border

    Column {
        id: column
        width: parent.width - 32
        x: 16
        y: 16
        spacing: 8

        Text {
            visible: card.title.length > 0
            width: parent.width
            text: card.title
            color: Theme.accent
            font.family: Theme.fontFamily
            font.pixelSize: Theme.size(1)
            font.weight: Font.DemiBold
            font.letterSpacing: 0.8
            font.capitalization: Font.AllUppercase
        }
        Text {
            visible: card.description.length > 0
            width: parent.width
            text: card.description
            color: Theme.textMuted
            font.family: Theme.fontFamily
            font.pixelSize: Theme.size(1)
            wrapMode: Text.WordWrap
            lineHeight: 1.25
        }
        Column {
            id: rows
            width: parent.width
            spacing: 0
        }
    }
}
