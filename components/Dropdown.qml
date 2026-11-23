// Custom dropdown: a styled button and a plain QML popup, so nothing inherits
// the platform theme's palette (the trap that makes Controls menus go white).
import QtQuick
import QtQuick.Controls
import "../theme"

Rectangle {
    id: box

    property string value: ""
    property var choices: []
    property int preferredWidth: 200
    signal selected(string value)

    implicitWidth: preferredWidth
    implicitHeight: 32
    radius: Theme.radiusSm
    color: hover.hovered || popup.visible ? Theme.surface3 : Theme.surface2
    border.width: 1
    border.color: popup.visible ? Theme.accent : Theme.border

    function labelFor(v) {
        const list = box.choices || [];
        for (let i = 0; i < list.length; i++) {
            if (list[i] && String(list[i].value) === String(v))
                return list[i].label;
        }
        return String(v);
    }

    Text {
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.right: caret.left
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        text: box.labelFor(box.value)
        color: Theme.text
        font.family: Theme.fontFamily
        font.pixelSize: Theme.size(2)
        elide: Text.ElideRight
    }
    Glyph {
        id: caret
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        glyph: "\uf078"
        pixelSize: Theme.size(0)
        dim: true
    }

    HoverHandler { id: hover }
    TapHandler { onTapped: popup.visible ? popup.close() : popup.open() }

    Popup {
        id: popup
        parent: box
        x: 0
        y: box.height + 4
        width: box.width
        padding: 6
        modal: false
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: Theme.radiusSm
            color: Theme.surface2
            border.width: 1
            border.color: Theme.borderStrong
        }

        contentItem: ListView {
            id: list
            implicitHeight: Math.min(340, contentHeight)
            clip: true
            model: box.choices
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                required property var modelData
                width: list.width
                height: 30
                radius: 6
                color: hoverRow.hovered ? Theme.alpha(Theme.accent, 0.18) : "transparent"
                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.label
                    color: String(modelData.value) === String(box.value) ? Theme.accent : Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.size(2)
                    elide: Text.ElideRight
                }
                HoverHandler { id: hoverRow }
                TapHandler {
                    onTapped: {
                        box.selected(String(modelData.value));
                        popup.close();
                    }
                }
            }
        }
    }
}
