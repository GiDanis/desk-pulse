import QtQuick
import "../../themes"
import "../../components"

Rectangle {
    id: root
    required property var context
    readonly property NotificationStyle style: context.visualStyle
    color: style.surfaceColor; radius: style.noticeRadius
    border.color: style.noticeAccent; border.width: style.noticeBorderWidth
    implicitHeight: title.height+guide.height+style.gap+8
    NotificationText { id: title; objectName: "notificationTitle"; style: root.style; role: "title"; x: root.style.padding; y: 4; width: root.width-2*x; horizontalAlignment: Text.AlignHCenter; text: root.context.event.title || ""; maximumLineCount: 1; elide: Text.ElideRight }
    NotificationText { id: guide; objectName: "notificationGuide"; style: root.style; role: "guide"; x: root.style.padding; y: title.y+title.height+root.style.gap; width: root.width-2*x; horizontalAlignment: Text.AlignHCenter; text: root.context.guideText; maximumLineCount: 1; elide: Text.ElideRight }
    MouseArea { anchors.fill: parent; onClicked: root.context.requestAction("openInbox") }
}
