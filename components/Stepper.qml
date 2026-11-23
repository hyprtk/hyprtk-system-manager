import QtQuick
import "../theme"

Row {
    id: root

    property real value: 0
    property real from: 0
    property real to: 100
    property real step: 1
    property int decimals: 0
    property string unit: ""
    signal moved(real value)

    spacing: 4

    function clamp(v) {
        let next = Math.max(root.from, Math.min(root.to, v));
        if (root.step > 0)
            next = Math.round(next / root.step) * root.step;
        return next;
    }
    function label(v) {
        const n = root.decimals > 0 ? Number(v).toFixed(root.decimals) : String(Math.round(v));
        return n + root.unit;
    }

    Rectangle {
        width: 28; height: 32; radius: Theme.radiusSm
        color: minusHover.hovered ? Theme.surface3 : Theme.surface2
        border.width: 1; border.color: Theme.border
        Text { anchors.centerIn: parent; text: "\u2212"; color: Theme.text; font.pixelSize: Theme.size(3) }
        HoverHandler { id: minusHover }
        TapHandler { onTapped: root.moved(root.clamp(root.value - root.step)) }
    }

    TTextField {
        id: field
        preferredWidth: 78
        text: root.label(root.value)
        onCommitted: (v) => {
            const parsed = parseFloat(String(v).replace(root.unit, ""));
            if (!isNaN(parsed))
                root.moved(root.clamp(parsed));
            else
                field.text = root.label(root.value);
        }
    }

    Rectangle {
        width: 28; height: 32; radius: Theme.radiusSm
        color: plusHover.hovered ? Theme.surface3 : Theme.surface2
        border.width: 1; border.color: Theme.border
        Text { anchors.centerIn: parent; text: "+"; color: Theme.text; font.pixelSize: Theme.size(3) }
        HoverHandler { id: plusHover }
        TapHandler { onTapped: root.moved(root.clamp(root.value + root.step)) }
    }
}
