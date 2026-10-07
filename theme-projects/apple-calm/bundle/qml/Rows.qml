pragma ComponentBehavior: Bound
import QtQuick

Item {
    id: root
    property var context: null
    property var rows: []
    property string emptyText: "Nessun dato disponibile"
    property bool compact: false
    property bool offsetMode: false
    property string actionId: ""
    readonly property var style: context ? context.style : null
    readonly property int rowHeight: Math.round((compact ? 65 : 84) * (style ? style.textScale : 1))
    readonly property int capacity: Math.max(1, Math.floor((height - 26) / rowHeight))
    readonly property int selectedIndex: {
        if (!context || !context.selection) return -1
        const selected = rows.findIndex(row => row.id === context.selection.selectedId)
        return selected >= 0 ? selected : context.selection.index
    }
    readonly property int pageStart: Math.max(0, Math.min(Math.max(0, rows.length - capacity), offsetMode ? Math.max(0, selectedIndex) : selectedIndex < 0 ? 0 : Math.floor(selectedIndex / capacity) * capacity))
    readonly property var visibleRows: rows.slice(pageStart, pageStart + capacity)
    Label { anchors.centerIn: parent; width: parent.width; themeStyle: root.style; secondary: true; size: 24; text: root.emptyText; visible: root.rows.length === 0; horizontalAlignment: Text.AlignHCenter }
    Repeater {
        // Keep delegate identities when selection/data changes the visible rows.
        model: Math.min(root.capacity,root.rows.length)
        delegate: Rectangle {
            id: row
            readonly property var modelData: root.visibleRows[index] || ({})
            required property int index
            readonly property bool selected: root.selectedIndex === root.pageStart + index
            x: 0; y: index * root.rowHeight
            width: root.width; height: root.rowHeight - 8
            radius: root.style ? root.style.radiusRow : 14
            color: root.style ? selected ? root.style.surfaceFocused : root.style.surface : "#FFFFFF"
            border.width: selected ? 3 : 1
            border.color: root.style ? selected ? root.style.semantic.focusIndicator : root.style.border : "#CDD2DA"
            OutlineIcon { id: icon; x: 14; anchors.verticalCenter: parent.verticalCenter; visible: !!row.modelData.icon; symbol: row.modelData.icon || "unknown"; opticalSize: 32; tint: root.style ? root.style.semantic.accentTextOnCard : "#0066CC" }
            Label { id: title; x: icon.visible ? 60 : 18; y: row.modelData.detail ? 6 : 0; width: Math.max(0, parent.width - x - (value.visible ? value.width + 30 : 20)); height: row.modelData.detail ? parent.height * 0.49 : parent.height; themeStyle: root.style; size: root.compact ? 21 : 24; font.weight: Font.Medium; text: row.modelData.title || ""; maximumLineCount: 1 }
            Label { x: title.x; y: parent.height * 0.51; width: title.width; height: parent.height * 0.40; themeStyle: root.style; secondary: true; size: 18; text: row.modelData.detail || ""; visible: !!text; maximumLineCount: 1 }
            Label { id: value; anchors.right: parent.right; anchors.rightMargin: 18; anchors.verticalCenter: parent.verticalCenter; width: Math.min(260, root.width * 0.33); height: parent.height - 8; themeStyle: root.style; size: root.compact ? 21 : 24; horizontalAlignment: Text.AlignRight; maximumLineCount: 2; text: row.modelData.value === undefined ? "" : String(row.modelData.value); visible: text.length > 0; color: root.style ? root.style.textPrimary : "#1D1D1F" }
            MouseArea {
                anchors.fill: parent
                enabled: !!root.context && row.modelData.enabled !== false && !!(row.modelData.actionId || root.actionId)
                onClicked: root.context.requestAction(row.modelData.actionId || root.actionId, row.modelData.targetId || row.modelData.id, {})
            }
        }
    }
    Label { anchors.right: parent.right; anchors.bottom: parent.bottom; themeStyle: root.style; size: 18; secondary: true; text: (root.pageStart + 1) + "–" + Math.min(root.rows.length, root.pageStart + root.capacity) + " / " + root.rows.length; visible: root.rows.length > root.capacity }
}
