import QtQuick
import SmartPC.ThemeApi 2.0

Rectangle {
    id: root
    required property NotificationContext context
    readonly property bool ready: root.context.eventData === null || title.text.length > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var mandatoryRegions: [{role: "title", x: title.x, y: title.y, width: title.width, height: title.height}, {role: "body", x: body.x, y: body.y, width: body.width, height: body.height}]
    function settleMotion() { }
    color: context.visualStyle.surfaceColor
    radius: context.visualStyle.noticeRadius
    border.width: 2; border.color: context.visualStyle.noticeAccent
    implicitHeight: 92
    Rectangle { x: 0; y: 0; width: 6; height: parent.height; color: root.context.visualStyle.noticeAccent }
    Text { id: title; x: 20; y: 9; width: parent.width - 40; text: root.context.eventData ? root.context.eventData.title : ""; color: root.context.visualStyle.titleColor; font.family: root.context.visualStyle.titleFamily; font.pixelSize: 23; font.bold: true; maximumLineCount: 1; elide: Text.ElideRight }
    Text { id: body; x: 20; y: 44; width: parent.width - 40; text: root.context.eventData ? root.context.eventData.body : ""; color: root.context.visualStyle.bodyColor; font.family: root.context.visualStyle.bodyFamily; font.pixelSize: 19; maximumLineCount: 1; elide: Text.ElideRight }
}
