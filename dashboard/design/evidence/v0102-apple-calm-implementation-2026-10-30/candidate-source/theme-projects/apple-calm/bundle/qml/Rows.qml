pragma ComponentBehavior: Bound
import QtQuick

Item {
    id: root
    property var context: null
    property var rows: []
    property string emptyText: "Nessun dato disponibile"
    property bool compact: false
    property bool offsetMode: false
    property bool fillAvailable: false
    property string actionId: ""
    readonly property var style: context ? context.style : null
    readonly property int baseRowHeight: Math.round((compact ? 108 : 118) * (style ? style.textScale : 1))
    readonly property real rowHeight: fillAvailable && rows.length > 0 && rows.length <= 4 ? Math.max(baseRowHeight, (height + 8) / rows.length) : baseRowHeight
    readonly property int capacity: Math.max(1, Math.floor((height + 8) / rowHeight))
    readonly property int selectedIndex: {
        if (!context || !context.selection) return -1
        const selected = rows.findIndex(row => row.id === context.selection.selectedId)
        return selected >= 0 ? selected : context.selection.index
    }
    readonly property int pageStart: Math.max(0, Math.floor(list.contentY / rowHeight))
    function revealSelection() {
        if (selectedIndex >= 0 && selectedIndex < list.count)
            list.positionViewAtIndex(selectedIndex, ListView.Contain)
    }
    onSelectedIndexChanged: Qt.callLater(revealSelection)
    onRowsChanged: Qt.callLater(revealSelection)
    Component.onCompleted: Qt.callLater(revealSelection)
    Label { anchors.centerIn: parent; width: parent.width; themeStyle: root.style; secondary: true; size: 24; text: root.emptyText; visible: root.rows.length === 0; horizontalAlignment: Text.AlignHCenter }
    ListView {
        id: list
        objectName: "scrollingRows"
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: root.rows
        spacing: 8
        delegate: Rectangle {
            id: row
            required property var modelData
            required property int index
            readonly property bool selected: root.selectedIndex === index
            width: list.width - (list.contentHeight > list.height ? 10 : 0)
            height: root.rowHeight - 8
            radius: root.style ? root.style.radiusRow : 14
            color: root.style ? selected ? root.style.surfaceFocused : root.style.background : "#FFFFFF"
            border.width: selected ? 3 : 0
            border.color: root.style ? selected ? root.style.semantic.focusIndicator : root.style.border : "#CDD2DA"
            OutlineIcon { id: icon; x: 14; anchors.verticalCenter: parent.verticalCenter; visible: !!row.modelData.icon; symbol: row.modelData.icon || "unknown"; opticalSize: 32; tint: root.style ? root.style.semantic.accentTextOnCard : "#0066CC" }
            Label { id: title; x: icon.visible ? 60 : 18; y: row.modelData.detail ? 6 : 0; width: Math.max(0, parent.width - x - (value.visible ? value.width + 30 : 20)); height: row.modelData.detail ? parent.height * 0.49 : parent.height; themeStyle: root.style; size: root.compact ? 30 : 34; font.weight: Font.Medium; text: row.modelData.title || ""; maximumLineCount: 1 }
            Label { x: title.x; y: parent.height * 0.51; width: title.width; height: parent.height * 0.44; themeStyle: root.style; secondary: true; size: 26; text: row.modelData.detail || ""; visible: !!text; maximumLineCount: root.fillAvailable ? 2 : 1 }
            Rectangle { x:18;y:parent.height-1;width:parent.width-36;height:1;color:root.style ? root.style.divider : "#CDD2DA";visible:!row.selected }
            Label { id: value; anchors.right: parent.right; anchors.rightMargin: 18; y:row.modelData.valueDetail ? 10 : 4; width: Math.min(260, root.width * 0.33); height:row.modelData.valueDetail ? parent.height*0.5 : parent.height-8; themeStyle: root.style; size: root.compact ? 30 : 34; font.family:root.style ? root.style.numbersFamily : "Sans Serif";horizontalAlignment: Text.AlignRight; maximumLineCount: 2; text: row.modelData.value === undefined ? "" : String(row.modelData.value); visible: text.length > 0; color: root.style ? root.style.textPrimary : "#1D1D1F" }
            Label { anchors.right:parent.right;anchors.rightMargin:18;y:parent.height*0.58;width:value.width;height:parent.height*0.32;themeStyle:root.style;size:22;secondary:true;text:row.modelData.valueDetail || "";horizontalAlignment:Text.AlignRight;maximumLineCount:1;visible:!!row.modelData.valueDetail }
            MouseArea {
                anchors.fill: parent
                enabled: !!root.context && row.modelData.enabled !== false && !!(row.modelData.actionId || root.actionId)
                onClicked: root.context.requestAction(row.modelData.actionId || root.actionId, row.modelData.targetId || row.modelData.id, {})
            }
        }
    }
    Rectangle {
        anchors.right: parent.right
        width: 4
        y: list.visibleArea.yPosition * root.height
        height: Math.max(18, list.visibleArea.heightRatio * root.height)
        radius: 2
        color: root.style ? root.style.accent : "#0066CC"
        visible: list.contentHeight > list.height
        opacity: 0.65
    }
}
