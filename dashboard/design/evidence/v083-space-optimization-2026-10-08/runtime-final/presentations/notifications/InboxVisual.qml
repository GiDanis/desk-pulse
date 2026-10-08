import QtQuick
import "../../themes"
import "../../components"

Item {
    id: root
    required property var context
    readonly property NotificationStyle style: context.visualStyle
    readonly property int selectedIndex: Math.max(0,context.items.findIndex(row => row.id === context.selectedEventId))
    readonly property real listHeight: Math.max(0,status.y-style.gap-92)
    readonly property int effectiveRows: Math.max(1,Math.min(style.noticeRows,Math.floor(listHeight/(style.titleSize*1.4+style.bodySize*1.3+2*style.padding+10))))
    readonly property int pageStart: Math.floor(selectedIndex/effectiveRows)*effectiveRows
    function ensureSelectionVisible() { /* pageStart is derived from the selected event id */ }
    NotificationText { style: root.style; role: "guide"; font.pixelSize: root.context.style.font37; text: root.context.preview ? "ANTEPRIMA AVVISI" : "AVVISI" }
    NotificationText { style: root.style; visible: root.context.items.length === 0; y: 133; width: root.width; text: "Nessun avviso attivo" }
    Repeater {
        model: root.context.items.slice(root.pageStart,root.pageStart+root.effectiveRows)
        delegate: Rectangle {
            required property var modelData
            required property int index
            readonly property bool selected: modelData.id === root.context.selectedEventId
            objectName: "alertRow"+(root.pageStart+index)
            y: 92+index*(root.listHeight/root.effectiveRows); width: root.width; height: root.listHeight/root.effectiveRows-10
            color: selected ? root.style.noticeFocusedSurface : root.style.surfaceColor
            radius: root.style.noticeRadius; border.color: selected ? root.style.noticeAccent : root.style.noticeBorder; border.width: selected ? root.context.style.focusWidth : root.style.noticeBorderWidth
            NotificationText { id: title; focused: parent.selected; style: root.style; role: "title"; x: root.style.padding; y: 8; width: parent.width-2*x; text: (modelData.seen ? "" : "●  ")+modelData.title; maximumLineCount: 1; elide: Text.ElideRight }
            NotificationText { focused: parent.selected; style: root.style; x: root.style.padding; y: title.y+title.height+Math.min(10,root.style.gap); width: parent.width-2*x; height: Math.max(0,parent.height-y-8); text: modelData.detail; maximumLineCount: 1; elide: Text.ElideRight }
            MouseArea { anchors.fill: parent; onClicked: { root.context.requestAction("selectEvent",modelData.id); root.context.requestAction("openDetails",modelData.id) } }
        }
    }
    NotificationText { id: status; objectName: "notificationSource"; style: root.style; role: "source"; visible: root.style.showSource; y: guide.y-root.style.gap-height; width: root.width; text: (root.context.items.length ? "AVVISO "+(root.selectedIndex+1)+"/"+root.context.items.length+" · " : "")+"Stato avvisi: "+root.context.sourceStatus; maximumLineCount: 1; elide: Text.ElideRight }
    NotificationText { id: guide; objectName: "notificationGuide"; style: root.style; role: "guide"; y: root.height-height-root.style.padding; width: root.width; text: root.context.guideText; maximumLineCount: 1; elide: Text.ElideRight }
}
