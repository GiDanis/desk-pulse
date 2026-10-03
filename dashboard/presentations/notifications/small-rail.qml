import QtQuick
import "../../themes"
import "../../components"

Rectangle {
    id: root
    required property var context
    readonly property NotificationStyle style: context.visualStyle
    implicitHeight: title.height+body.height+style.gap+8
    color: style.surfaceColor; radius: style.noticeRadius; border.color: style.noticeBorder; border.width: style.noticeBorderWidth
    Rectangle { width: 6; height: parent.height; color: root.style.noticeAccent; radius: root.style.noticeRadius }
    AppIcon { style: root.context.style; x: root.style.padding; anchors.verticalCenter: parent.verticalCenter; iconId: root.context.iconId; tint: root.style.noticeAccent; opticalSize: 36 }
    NotificationText { id: title; objectName: "notificationTitle"; style: root.style; role: "title"; x: root.style.padding+36+root.style.gap; y: Math.max(4,(root.height-height-body.height-root.style.gap)/2); width: Math.max(0,root.width-x-root.style.padding); text: root.context.event.title || ""; maximumLineCount: 1; elide: Text.ElideRight }
    NotificationText { id: body; objectName: "notificationBody"; style: root.style; x: title.x; y: title.y+title.height+root.style.gap; width: Math.max(0,root.width-x-guide.width-root.style.padding-root.style.gap); text: root.context.event.detail || ""; maximumLineCount: 1; elide: Text.ElideRight }
    NotificationText { id: guide; objectName: "notificationGuide"; style: root.style; role: "guide"; anchors.right: parent.right; anchors.rightMargin: root.style.padding; y: body.y; text: root.context.guideText; wrapMode: Text.NoWrap }
    MouseArea { anchors.fill: parent; onClicked: root.context.requestAction("openInbox") }
}
