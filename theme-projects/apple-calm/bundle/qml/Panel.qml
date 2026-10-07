pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format

Item {
    id: root
    property var ctx: null
    property string title: ""
    property string subtitle: ""
    property string footer: ""
    property var source: null
    property var tabs: null
    property var rows: []
    property bool pageMode: false
    property bool compact: false
    property bool offsetMode: false
    property string emptyText: "Nessun dato disponibile"
    property string rowAction: ""
    readonly property bool ready: !!ctx && heading.text.length > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var style: ctx ? ctx.style : null
    readonly property int inset: pageMode ? 0 : 32
    readonly property real bodyY: pageMode ? 90 : 120
    readonly property var mandatoryRegions: [{role: "title", x: heading.x, y: heading.y, width: heading.width, height: heading.height}, {role: "body", x: body.x, y: body.y, width: body.width, height: body.height}]
    function settleMotion() { }
    Rectangle { anchors.fill: parent; color: root.style ? root.pageMode ? root.style.background : root.style.backgroundOverlay : "#F3F4F6" }
    Label { id: heading; x: root.inset; y: root.pageMode ? 0 : 24; width: parent.width - 2*x; height: 46; themeStyle: root.style; size: 34; font.weight: Font.DemiBold; text: root.title; maximumLineCount: 1 }
    Label { x: root.inset; y: heading.y + heading.height; width: parent.width - 2*x; height: 30; themeStyle: root.style; secondary: true; size: 20; text: root.subtitle; maximumLineCount: 1; visible: !root.tabs }
    Tabs { x: root.inset; y: heading.y + heading.height + 4; width: parent.width - 2*x; context: root.ctx; tabs: root.tabs; visible: !!root.tabs }
    Rows { id: body; x: root.inset; y: root.bodyY; width: parent.width - 2*x; height: Math.max(0, parent.height - y - (root.pageMode ? 45 : 55)); context: root.ctx; rows: root.rows; compact: root.compact; offsetMode: root.offsetMode; emptyText: root.emptyText; actionId: root.rowAction }
    Label { x: root.inset; y: parent.height - (root.pageMode ? 36 : 44); width: parent.width - 2*x; height: 34; themeStyle: root.style; secondary: true; size: 18; text: [root.footer, root.source ? Format.source(root.source) : ""].filter(Boolean).join(" · "); maximumLineCount: 1 }
}
