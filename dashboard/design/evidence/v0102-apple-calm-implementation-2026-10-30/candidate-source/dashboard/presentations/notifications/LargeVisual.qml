import QtQuick
import "../../themes"
import "../../components"

Rectangle {
    id: root
    required property var context
    readonly property NotificationStyle style: context.visualStyle
    readonly property var occupiedRegions: [Qt.rect(-style.insetX,-16,960,height+16)]
    color: style.surfaceColor; radius: style.noticeRadius
    border.color: style.noticeAccent; border.width: style.noticeBorderWidth
    Rectangle { z: -1; x: -root.style.insetX; y: -16; width: 960; height: root.height+16; color: root.context.style.background }
    NotificationText { id: label; style: root.style; role: "guide"; x: root.style.padding; y: root.style.padding; text: root.context.preview ? "ANTEPRIMA AVVISO" : "AVVISO" }
    AppIcon { style: root.context.style; visible: root.style.showIcon; anchors.right: parent.right; anchors.rightMargin: root.style.padding; y: root.style.padding; opticalSize: 40; iconId: root.context.iconId; tint: root.style.noticeAccent }
    NotificationText {
        id: title; objectName: "notificationTitle"; style: root.style; role: "title"
        x: root.style.padding; y: label.y+label.height+root.style.gap
        width: root.width-2*x; maximumLineCount: root.style.titleLines; elide: Text.ElideRight
        height: Math.min(implicitHeight,Math.max(0,(source.visible ? source.y : guide.y)-root.style.gap-y-root.style.bodySize*1.5-root.style.gap))
        clip: true
        text: root.context.event.title || ""
    }
    NotificationText {
        objectName: "notificationBody"; style: root.style
        x: root.style.padding; y: title.y+title.height+root.style.gap; width: root.width-2*x
        height: Math.max(0,(source.visible ? source.y : guide.y)-root.style.gap-y)
        maximumLineCount: root.style.bodyLines; elide: Text.ElideRight; text: root.context.event.detail || ""
    }
    NotificationText { id: source; objectName: "notificationSource"; style: root.style; role: "source"; visible: root.style.showSource; x: root.style.padding; y: guide.y-root.style.gap-height; width: root.width-2*x; text: root.context.sourceText; maximumLineCount: 1; elide: Text.ElideRight }
    NotificationText { id: guide; objectName: "notificationGuide"; style: root.style; role: "guide"; x: root.style.padding; y: root.height-root.style.padding-height; width: root.width-2*x; text: root.context.guideText; maximumLineCount: 1; elide: Text.ElideRight }
    MouseArea { anchors.fill: parent; onClicked: root.context.requestAction("openInbox") }
}
