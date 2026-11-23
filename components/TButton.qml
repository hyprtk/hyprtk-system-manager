// Flat button with the suite's three variants: default, primary, danger.
import QtQuick
import "../theme"

Rectangle {
    id: btn

    property string text: ""
    property string glyph: ""
    property bool primary: false
    property bool danger: false
    property bool ghost: false
    property bool small: false
    signal clicked()

    implicitWidth: Math.max(small ? 54 : 64, content.implicitWidth + (small ? 18 : 28))
    implicitHeight: small ? 28 : 34
    radius: Theme.radiusSm
    opacity: enabled ? 1 : 0.55

    color: !enabled ? Theme.surface1
         : danger ? (hover.hovered ? Qt.lighter(Theme.danger, 1.12) : Theme.danger)
         : primary ? (hover.hovered ? Qt.lighter(Theme.accent, 1.12) : Theme.accent)
         : ghost ? (hover.hovered ? Theme.alpha(Theme.foreground, 0.09) : "transparent")
         : (hover.hovered ? Theme.surface3 : Theme.surface2)
    border.width: (primary || danger || ghost) ? 0 : 1
    border.color: Theme.border

    Row {
        id: content
        anchors.centerIn: parent
        spacing: 6
        Glyph {
            visible: btn.glyph.length > 0
            glyph: btn.glyph
            pixelSize: btn.small ? Theme.size(1) : Theme.size(2)
            color: btn.primary ? Theme.textOnAccent
                 : btn.danger ? Theme.textOnDanger
                 : Theme.text
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: btn.text
            color: btn.primary ? Theme.textOnAccent
                 : btn.danger ? Theme.textOnDanger
                 : Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: btn.small ? Theme.size(1) : Theme.size(2)
            font.weight: btn.primary ? Font.DemiBold : Font.Medium
            visible: btn.text.length > 0
        }
    }

    HoverHandler { id: hover; enabled: btn.enabled }
    TapHandler { enabled: btn.enabled; onTapped: btn.clicked() }
}
