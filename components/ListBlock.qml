// A list of rows with badges and inline actions (users, services, suite apps).
import QtQuick
import "../theme"

Column {
    id: root

    property var items: []
    signal invoke(var action)

    width: parent ? parent.width : 0
    spacing: 6

    Repeater {
        model: root.items

        delegate: Rectangle {
            id: row
            required property var modelData

            width: root.width
            height: Math.max(52, textColumn.implicitHeight + 20)
            radius: Theme.radiusSm
            color: Theme.alpha(Theme.surface2, 0.55)
            border.width: 1
            border.color: Theme.border

            Column {
                id: textColumn
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.right: actions.left
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2

                Row {
                    spacing: 6
                    Text {
                        text: row.modelData.title || ""
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.size(2)
                        font.weight: Font.DemiBold
                    }
                    Repeater {
                        model: row.modelData.badges || []
                        delegate: StatusPill {
                            required property var modelData
                            text: String(modelData)
                            tone: String(modelData) === "running" ? "ok"
                                : String(modelData) === "disabled" ? "warn"
                                : String(modelData) === "danger" ? "danger"
                                : "neutral"
                        }
                    }
                }
                Text {
                    width: parent.width
                    visible: (row.modelData.subtitle || "").length > 0
                    text: row.modelData.subtitle || ""
                    color: Theme.textFaint
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.size(1)
                    elide: Text.ElideRight
                }
            }

            Row {
                id: actions
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                Repeater {
                    model: row.modelData.actions || []
                    delegate: TButton {
                        required property var modelData
                        text: modelData.label || "Run"
                        small: true
                        danger: modelData.variant === "danger"
                        primary: modelData.variant === "primary"
                        onClicked: root.invoke(modelData)
                    }
                }
            }
        }
    }

    Text {
        visible: root.items.length === 0
        text: "Nothing here."
        color: Theme.textFaint
        font.family: Theme.fontFamily
        font.pixelSize: Theme.size(2)
    }
}
