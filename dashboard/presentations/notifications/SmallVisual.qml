import QtQuick
import "../../themes"
import "../../components"

Rectangle {
    id: root
    required property var context
    readonly property NotificationStyle style: context.visualStyle
    readonly property int contentLeft: style.padding + (style.showIcon ? 42+style.gap : 0)
    implicitHeight: title.height+body.height+style.gap+8
    color: style.surfaceColor; radius: style.noticeRadius
    border.color: style.noticeAccent; border.width: style.noticeBorderWidth
    AppIcon { style: root.context.style; visible: root.style.showIcon; x: root.style.padding; anchors.verticalCenter: parent.verticalCenter; opticalSize: 36; iconId: root.context.iconId; tint: root.style.noticeAccent }
    NotificationText {
        id: title; objectName: "notificationTitle"; style: root.style; role: "title"
        x: root.contentLeft; y: Math.max(4,(root.height-height-body.height-root.style.gap)/2)
        width: Math.max(0,root.width-x-guide.width-root.style.padding-root.style.gap)
        text: root.context.event.title || ""; maximumLineCount: 1; elide: Text.ElideRight
    }
    NotificationText {
        id: body; objectName: "notificationBody"; style: root.style
        x: root.contentLeft; y: title.y+title.height+root.style.gap
        width: Math.max(0,root.width-x-root.style.padding)
        text: root.style.showSource ? (root.context.event.detail || "")+" · "+root.context.sourceText : root.context.event.detail || ""
        maximumLineCount: 1; elide: Text.ElideRight
    }
    NotificationText { id: guide; objectName: "notificationGuide"; style: root.style; role: "guide"; anchors.right: parent.right; anchors.rightMargin: root.style.padding; anchors.verticalCenter: parent.verticalCenter; text: root.context.guideText; wrapMode: Text.NoWrap }
    MouseArea { anchors.fill: parent; onClicked: root.context.requestAction("openInbox") }
}
