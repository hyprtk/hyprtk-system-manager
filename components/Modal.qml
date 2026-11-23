// Shared modal card: scrim, title, message, arbitrary body, footer actions.
// Used for destructive confirmation, password entry and the file picker.
import QtQuick
import "../theme"

Item {
    id: modal

    property bool open: false
    property string title: ""
    property string message: ""
    property string confirmText: "Confirm"
    property string cancelText: "Cancel"
    property bool danger: false
    property bool busy: false
    property bool showCancel: true
    property bool confirmEnabled: true
    default property alias body: bodyColumn.data

    signal accepted()
    signal rejected()

    visible: open
    z: 900
    anchors.fill: parent

    Rectangle {
        anchors.fill: parent
        color: Theme.scrim
        TapHandler { enabled: !modal.busy; onTapped: modal.rejected() }
    }

    Rectangle {
        id: card
        anchors.centerIn: parent
        width: Math.min(460, parent.width - 80)
        implicitHeight: content.implicitHeight + 40
        radius: Theme.radiusLg
        color: Theme.surface1
        border.width: 1
        border.color: Theme.borderStrong

        Column {
            id: content
            width: parent.width - 40
            x: 20
            y: 20
            spacing: 10

            Text {
                width: parent.width
                text: modal.title
                visible: modal.title.length > 0
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(4)
                font.weight: Font.DemiBold
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                text: modal.message
                visible: modal.message.length > 0
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(2)
                wrapMode: Text.WordWrap
                lineHeight: 1.3
            }
            Column {
                id: bodyColumn
                width: parent.width
                spacing: 8
            }
            Row {
                width: parent.width
                spacing: 8
                Item { width: parent.width - buttons.width - 8; height: 1 }
                Row {
                    id: buttons
                    spacing: 8
                    TButton {
                        visible: modal.showCancel
                        text: modal.cancelText
                        enabled: !modal.busy
                        onClicked: modal.rejected()
                    }
                    TButton {
                        text: modal.confirmText
                        primary: !modal.danger
                        danger: modal.danger
                        enabled: modal.confirmEnabled && !modal.busy
                        onClicked: modal.accepted()
                    }
                }
            }
        }
    }
}
