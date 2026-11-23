// Navigation: grouped panel list, global search and the app's identity.
import QtQuick
import "../theme"
import "../components"

Rectangle {
    id: sidebar

    property var groups: []
    property var panels: []
    property var searchResults: []
    property string currentPage: ""
    property string hostname: ""
    property string version: ""
    property string privilege: ""
    property alias searchText: search.text

    signal select(string id)
    signal searchChanged(string text)
    signal submitted()

    function focusSearch() { search.forceActiveFocus(); }
    function clearSearch() {
        if (search.text.length > 0) {
            search.text = "";
            sidebar.searchChanged("");
        }
    }

    color: Theme.alpha(Theme.surface0, 0.9)
    border.width: 0

    function panelsIn(groupId) {
        return sidebar.panels.filter(p => p.group === groupId);
    }
    function matches(panel) {
        if (search.text.length === 0)
            return true;
        const hay = (panel.title + " " + panel.description + " " +
                     (panel.keywords || []).join(" ")).toLowerCase();
        return hay.indexOf(search.text.toLowerCase()) >= 0;
    }

    Column {
        anchors.fill: parent
        anchors.topMargin: 18
        spacing: 10

        // ── identity ───────────────────────────────────────────────
        Row {
            x: 18
            spacing: 10
            Rectangle {
                width: 34; height: 34; radius: 9
                color: Theme.alpha(Theme.accent, 0.18)
                border.width: 1
                border.color: Theme.alpha(Theme.accent, 0.4)
                Glyph {
                    anchors.centerIn: parent
                    glyph: "\uf1de"
                    pixelSize: Theme.size(4)
                    color: Theme.accent
                }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 1
                Text {
                    text: "System Settings"
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.size(3)
                    font.weight: Font.DemiBold
                }
                Text {
                    text: sidebar.hostname || "this device"
                    color: Theme.textFaint
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.size(1)
                }
            }
        }

        // ── search ─────────────────────────────────────────────────
        Rectangle {
            x: 14
            width: parent.width - 28
            height: 34
            radius: Theme.radiusSm
            color: Theme.surface2
            border.width: 1
            border.color: search.activeFocus ? Theme.accent : Theme.border

            Glyph {
                id: searchGlyph
                anchors.left: parent.left
                anchors.leftMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                glyph: "\uf002"
                pixelSize: Theme.size(1)
                dim: true
            }
            TextInput {
                id: search
                anchors.left: searchGlyph.right
                anchors.leftMargin: 8
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                color: Theme.text
                selectionColor: Theme.accent
                selectedTextColor: Theme.textOnAccent
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(2)
                clip: true
                onTextEdited: sidebar.searchChanged(text)
                onAccepted: sidebar.submitted()
                Keys.onEscapePressed: { text = ""; sidebar.searchChanged(""); }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: search.text.length === 0
                    text: "Search settings…"
                    color: Theme.textFaint
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.size(2)
                }
            }
        }

        // ── results / navigation ───────────────────────────────────
        Flickable {
            id: scroller
            width: parent.width
            height: parent.height - y - 46
            contentHeight: navColumn.implicitHeight + 16
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: navColumn
                width: scroller.width
                spacing: 2

                // search results
                Repeater {
                    model: sidebar.searchText.length > 0 ? sidebar.searchResults : []
                    delegate: Rectangle {
                        required property var modelData
                        width: navColumn.width - 20
                        x: 10
                        height: 46
                        radius: Theme.radiusSm
                        color: resultHover.hovered ? Theme.alpha(Theme.foreground, 0.06) : "transparent"

                        Row {
                            anchors.left: parent.left
                            anchors.leftMargin: 10
                            anchors.right: parent.right
                            anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 8
                            Glyph { glyph: modelData.icon || ""; pixelSize: Theme.size(2); dim: true; anchors.verticalCenter: parent.verticalCenter }
                            Column {
                                width: parent.width - 34
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 1
                                Text {
                                    text: modelData.title || ""
                                    color: Theme.text
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.size(2)
                                    elide: Text.ElideRight
                                    width: parent.width
                                }
                                Text {
                                    text: modelData.description || ""
                                    color: Theme.textFaint
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.size(1)
                                    elide: Text.ElideRight
                                    width: parent.width
                                }
                            }
                        }
                        HoverHandler { id: resultHover }
                        TapHandler { onTapped: sidebar.select(modelData.id) }
                    }
                }

                // grouped panels
                Repeater {
                    model: sidebar.searchText.length > 0 ? [] : sidebar.groups
                    delegate: Column {
                        required property var modelData
                        width: navColumn.width
                        spacing: 1
                        visible: sidebar.panelsIn(modelData.id).some(p => sidebar.matches(p))

                        Text {
                            x: 20
                            topPadding: 12
                            bottomPadding: 4
                            text: modelData.title.toUpperCase()
                            color: Theme.textFaint
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.size(0)
                            font.letterSpacing: 1.0
                            font.weight: Font.DemiBold
                        }

                        Repeater {
                            model: sidebar.panelsIn(modelData.id).filter(p => sidebar.matches(p))
                            delegate: NavItem {
                                required property var modelData
                                x: 10
                                width: navColumn.width - 20
                                glyph: modelData.icon
                                label: modelData.title
                                active: sidebar.currentPage === modelData.id
                                onClicked: sidebar.select(modelData.id)
                            }
                        }
                    }
                }

                Text {
                    visible: sidebar.searchText.length > 0 && sidebar.searchResults.length === 0
                    x: 20
                    topPadding: 14
                    text: "No matching settings."
                    color: Theme.textFaint
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.size(2)
                }
            }
        }

        // ── footer ─────────────────────────────────────────────────
        Row {
            x: 18
            width: parent.width - 36
            spacing: 6
            Text {
                text: "v" + (sidebar.version || "0.1.0")
                color: Theme.textFaint
                font.family: Theme.monoFamily
                font.pixelSize: Theme.size(0)
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: "·"
                color: Theme.textFaint
                font.pixelSize: Theme.size(0)
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: sidebar.privilege || "user"
                color: Theme.textFaint
                font.family: Theme.monoFamily
                font.pixelSize: Theme.size(0)
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
