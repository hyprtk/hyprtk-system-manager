// Page hero: a large glyph, an eyebrow, title, subtitle and chips.
import QtQuick
import "../theme"

Item {
    id: hero
    property string glyph: "\uf05a"
    property string eyebrow: ""
    property string title: ""
    property string subtitle: ""
    property var chips: []

    width: parent ? parent.width : 0
    implicitHeight: layout.implicitHeight + 8

    Row {
        id: layout
        width: parent.width
        spacing: 18

        Rectangle {
            width: 64; height: 64; radius: Theme.radiusMd
            color: Theme.alpha(Theme.accent, 0.14)
            border.width: 1
            border.color: Theme.alpha(Theme.accent, 0.35)
            Glyph {
                anchors.centerIn: parent
                glyph: hero.glyph
                pixelSize: Theme.size(6)
                color: Theme.accent
            }
        }

        Column {
            width: parent.width - 86
            spacing: 3

            Text {
                visible: hero.eyebrow.length > 0
                text: hero.eyebrow.toUpperCase()
                color: Theme.textFaint
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(0)
                font.letterSpacing: 1.1
                font.weight: Font.DemiBold
            }
            Text {
                width: parent.width
                text: hero.title
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(6)
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                visible: hero.subtitle.length > 0
                text: hero.subtitle
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(2)
                elide: Text.ElideRight
            }
            Row {
                spacing: 6
                topPadding: 4
                Repeater {
                    model: hero.chips
                    delegate: StatusPill {
                        required property var modelData
                        text: typeof modelData === "string" ? modelData : (modelData.label || "")
                        tone: "neutral"
                    }
                }
            }
        }
    }
}
