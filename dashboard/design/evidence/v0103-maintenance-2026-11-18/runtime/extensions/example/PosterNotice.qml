import QtQuick
import "../../themes"
import "../../components"

Rectangle {
    id: root
    required property var context
    readonly property NotificationStyle style: context.visualStyle
    color: style.surfaceColor; radius: style.noticeRadius; border.color: style.noticeAccent; border.width: style.noticeBorderWidth
    AppIcon { style: root.context.style; anchors.horizontalCenter: parent.horizontalCenter; y: root.style.padding; opticalSize: 48; iconId: root.context.iconId; tint: root.style.noticeAccent }
    NotificationText { id: title; objectName: "notificationTitle"; style: root.style; role: "title"; x: root.style.padding; y: root.style.padding+48+root.style.gap; width: root.width-2*x; horizontalAlignment: Text.AlignHCenter; text: root.context.event.title || ""; maximumLineCount: root.style.titleLines; elide: Text.ElideRight; height: Math.min(implicitHeight,Math.max(0,(source.visible ? source.y : guide.y)-root.style.gap-y-root.style.bodySize*1.5-root.style.gap)); clip: true }
    NotificationText { objectName: "notificationBody"; style: root.style; x: root.style.padding; y: title.y+title.height+root.style.gap; width: root.width-2*x; height: Math.max(0,(source.visible ? source.y : guide.y)-root.style.gap-y); horizontalAlignment: Text.AlignHCenter; text: root.context.event.detail || ""; maximumLineCount: root.style.bodyLines; elide: Text.ElideRight }
    NotificationText { id: source; objectName: "notificationSource"; style: root.style; role: "source"; x: root.style.padding; y: guide.y-root.style.gap-height; width: root.width-2*x; horizontalAlignment: Text.AlignHCenter; visible: root.style.showSource; text: root.context.sourceText; maximumLineCount: 1; elide: Text.ElideRight }
    NotificationText { id: guide; objectName: "notificationGuide"; style: root.style; role: "guide"; x: root.style.padding; y: root.height-root.style.padding-height; width: root.width-2*x; horizontalAlignment: Text.AlignHCenter; text: root.context.guideText; maximumLineCount: 1; elide: Text.ElideRight }
    MouseArea { anchors.fill: parent; onClicked: root.context.requestAction("openInbox") }
}
