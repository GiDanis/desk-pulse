import QtQuick
import SmartPC.ThemeApi 2.0

Rectangle {
    id: root
    required property NotificationContext context
    readonly property bool ready: root.context.eventData === null || title.text.length > 0 && body.text.length > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var mandatoryRegions: [{role: "title", x: title.x, y: title.y, width: title.width, height: title.height}, {role: "body", x: body.x, y: body.y, width: body.width, height: body.height}, {role: "source", x: source.x, y: source.y, width: source.width, height: source.height}]
    function settleMotion() { }
    color: context.visualStyle.surfaceColor; radius: context.visualStyle.noticeRadius
    border.width: 2; border.color: context.visualStyle.noticeAccent
    implicitHeight: 340
    Rectangle { x: 20; y: 22; width: 55; height: 5; color: root.context.visualStyle.noticeAccent }
    Text { id: title; x: 22; y: 45; width: parent.width - 44; text: root.context.eventData ? root.context.eventData.title : ""; color: root.context.visualStyle.titleColor; font.family: root.context.visualStyle.titleFamily; font.pixelSize: 31; font.bold: true; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
    Text { id: body; x: 22; y: 135; width: parent.width - 44; text: root.context.eventData ? root.context.eventData.body : ""; color: root.context.visualStyle.bodyColor; font.family: root.context.visualStyle.bodyFamily; font.pixelSize: 23; wrapMode: Text.Wrap; maximumLineCount: 4; elide: Text.ElideRight }
    Text { id: source; x: 22; y: parent.height - 65; width: parent.width - 44; text: root.context.sourceText + " · " + root.context.validityText; color: root.context.visualStyle.sourceColor; font.pixelSize: 17; maximumLineCount: 1; elide: Text.ElideRight }
    Text { x: 22; y: parent.height - 32; width: parent.width - 44; text: root.context.guideText; color: root.context.visualStyle.guideColor; font.pixelSize: 17; maximumLineCount: 1; elide: Text.ElideRight }
}
