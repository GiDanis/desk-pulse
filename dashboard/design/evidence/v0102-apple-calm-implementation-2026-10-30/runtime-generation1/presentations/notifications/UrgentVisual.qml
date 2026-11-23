import QtQuick
import "../../themes"
import "../../components"

Rectangle {
    id: root
    required property var context
    readonly property NotificationStyle style: context.visualStyle
    color: style.surfaceColor
    Rectangle { width: parent.width; height: 8; color: root.context.event.weatherSeverity === "rossa" ? root.style.criticalOnCard : root.style.warningOnCard }
    NotificationText { id: heading; style: root.style; role: "guide"; x: root.style.padding; y: root.style.padding+8; width: root.width-2*x; text: (root.context.preview ? "ANTEPRIMA · " : "")+"AVVISO PRIORITARIO"+(root.context.event.weatherSeverity ? " · "+root.context.event.weatherSeverity.toUpperCase() : ""); maximumLineCount: 1; elide: Text.ElideRight }
    AppIcon { style: root.context.style; visible: root.style.showIcon; anchors.right: parent.right; anchors.rightMargin: root.style.padding; y: heading.y+heading.height; opticalSize: 40; iconId: root.context.iconId; tint: root.style.noticeAccent }
    NotificationText { id: title; objectName: "notificationTitle"; style: root.style; role: "title"; x: root.style.padding; y: heading.y+heading.height+2*root.style.gap; width: root.width-2*x; text: root.context.event.title || ""; maximumLineCount: root.style.titleLines; elide: Text.ElideRight; height: Math.min(implicitHeight,Math.max(0,(source.visible ? source.y : divider.y)-root.style.gap-y-root.style.bodySize*1.5-root.style.gap)); clip: true }
    NotificationText { objectName: "notificationBody"; style: root.style; x: root.style.padding; y: title.y+title.height+root.style.gap; width: root.width-2*x; height: Math.max(0,(source.visible ? source.y : divider.y)-root.style.gap-y); text: root.context.event.detail || ""; maximumLineCount: root.style.bodyLines; elide: Text.ElideRight }
    NotificationText { id: source; objectName: "notificationSource"; style: root.style; role: "source"; visible: root.style.showSource; x: root.style.padding; y: divider.y-root.style.gap-height; width: root.width-2*x; text: root.context.sourceText; maximumLineCount: 2; elide: Text.ElideRight }
    Rectangle { id: divider; x: root.style.padding; y: guide.y-root.style.gap; width: root.width-2*x; height: 2; color: root.style.noticeBorder }
    NotificationText { id: guide; objectName: "notificationGuide"; style: root.style; role: "guide"; x: root.style.padding; y: root.height-root.style.padding-height; width: root.width-2*x; text: root.context.guideText; maximumLineCount: 1; elide: Text.ElideRight }
}
