import QtQuick
import "../../themes"
import "../../components"

Rectangle {
    id: root
    required property var context
    readonly property NotificationStyle style: context.visualStyle
    color: style.surfaceColor; radius: style.noticeRadius; border.color: style.noticeBorder; border.width: style.noticeBorderWidth
    implicitHeight: label.height+8
    NotificationText { id: label; objectName: "notificationBadgeText"; style: root.style; role: "title"; color: root.style.noticeAccent; anchors.centerIn: parent; width: root.width-2*root.style.padding; horizontalAlignment: Text.AlignHCenter; maximumLineCount: 1; elide: Text.ElideRight; text: root.context.unreadCount === 1 ? "3 · NUOVO AVVISO" : "3 · "+root.context.unreadCount+" NUOVI AVVISI" }
    MouseArea { anchors.fill: parent; onClicked: root.context.requestAction("openInbox") }
}
