import QtQuick
import "../../themes"
import "../../components"

Rectangle {
    id: root
    required property var context
    readonly property NotificationStyle style: context.visualStyle
    readonly property var occupiedRegions: [Qt.rect(-style.insetX,-16,960,height+16)]
    readonly property real dividerX: width*.42
    color: style.surfaceColor; radius: style.noticeRadius; border.color: style.noticeBorder; border.width: style.noticeBorderWidth
    Rectangle { z: -1; x: -root.style.insetX; y: -16; width: 960; height: root.height+16; color: root.context.style.background }
    Rectangle { x: root.dividerX; y: root.style.padding; width: 2; height: guide.y-root.style.gap-y; color: root.style.noticeAccent }
    AppIcon { style: root.context.style; x: root.style.padding; y: root.style.padding; opticalSize: 42; iconId: root.context.iconId; tint: root.style.noticeAccent }
    NotificationText { objectName: "notificationTitle"; style: root.style; role: "title"; x: root.style.padding; y: root.style.padding+42+root.style.gap; width: Math.max(0,root.dividerX-2*x); height: Math.max(0,guide.y-root.style.gap-y); text: root.context.event.title || ""; maximumLineCount: Math.max(3,root.style.titleLines); elide: Text.ElideRight }
    NotificationText { objectName: "notificationBody"; style: root.style; x: root.dividerX+root.style.gap; y: root.style.padding; width: Math.max(0,root.width-x-root.style.padding); height: Math.max(0,(source.visible ? source.y : guide.y)-root.style.gap-y); text: root.context.event.detail || ""; maximumLineCount: Math.max(4,root.style.bodyLines); elide: Text.ElideRight }
    NotificationText { id: source; objectName: "notificationSource"; style: root.style; role: "source"; visible: root.style.showSource; x: root.dividerX+root.style.gap; y: guide.y-root.style.gap-height; width: Math.max(0,root.width-x-root.style.padding); text: root.context.sourceText; maximumLineCount: 2; elide: Text.ElideRight }
    NotificationText { id: guide; objectName: "notificationGuide"; style: root.style; role: "guide"; x: root.style.padding; y: root.height-root.style.padding-height; width: root.width-2*x; text: root.context.guideText; maximumLineCount: 1; elide: Text.ElideRight }
    MouseArea { anchors.fill: parent; onClicked: root.context.requestAction("openInbox") }
}
