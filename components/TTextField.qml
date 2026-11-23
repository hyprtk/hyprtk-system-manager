// Styled single-line text input. `edited` fires per keystroke; `committed`
// fires on Enter and on focus loss, which is what a settings form should save.
import QtQuick
import "../theme"

Rectangle {
    id: field

    property alias text: input.text
    property alias input: input
    property alias echoMode: input.echoMode
    property string placeholder: ""
    property bool mono: false
    property int preferredWidth: 200
    property bool invalid: false
    signal edited(string value)
    signal committed(string value)
    signal accepted()

    implicitWidth: preferredWidth
    implicitHeight: 32
    radius: Theme.radiusSm
    color: Theme.surface2
    border.width: 1
    border.color: input.activeFocus ? Theme.accent
                : field.invalid ? Theme.danger
                : Theme.border

    TextInput {
        id: input
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        verticalAlignment: TextInput.AlignVCenter
        color: Theme.text
        selectionColor: Theme.accent
        selectedTextColor: Theme.textOnAccent
        font.family: field.mono ? Theme.monoFamily : Theme.fontFamily
        font.pixelSize: Theme.size(2)
        clip: true
        onTextEdited: field.edited(text)
        onEditingFinished: field.committed(text)
        onAccepted: field.accepted()
    }

    Text {
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        visible: input.text.length === 0
        text: field.placeholder
        color: Theme.textFaint
        font.family: Theme.fontFamily
        font.pixelSize: Theme.size(2)
    }
}
