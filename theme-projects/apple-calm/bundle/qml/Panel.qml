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
    property bool fillRows: false
    property bool offsetMode: false
    property bool gridRows: false
    property bool gridMetrics: false
    property bool compactHeading: false
    property string emptyText: "Nessun dato disponibile"
    property string rowAction: ""
    readonly property bool ready: !!ctx && heading.text.length > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var style: ctx ? ctx.style : null
    readonly property int inset: pageMode ? 0 : 24
    readonly property string footerText: [root.footer, root.source ? Format.source(root.source) : ""].filter(Boolean).join(" · ")
    readonly property int bottomInset: pageMode ? 0 : 16
    readonly property real bodyY: (pageMode ? 0 : 16) + (compactHeading ? 40 : 56) + (tabs || subtitle.length ? 40 : 0) + 8
    readonly property var mandatoryRegions: [{role: "title", x: heading.x, y: heading.y, width: heading.width, height: heading.height}, {role: "body", x: body.x, y: body.y, width: body.width, height: body.height}]
    function settleMotion() { }
    Rectangle { anchors.fill: parent; color: root.style ? root.pageMode ? root.style.background : root.style.backgroundOverlay : "#F3F4F6" }
    Label { id: heading; x: root.inset; y: root.pageMode ? 0 : 16; width: parent.width - 2*x; height: root.compactHeading ? 40 : 56; themeStyle: root.style; size: root.compactHeading ? 32 : 42; font.weight: Font.DemiBold; text: root.title; maximumLineCount: 1 }
    Label { x: root.inset; y: heading.y + heading.height; width: parent.width - 2*x; height: 40; themeStyle: root.style; secondary: true; size: 26; text: root.subtitle; maximumLineCount: 1; visible: !root.tabs }
    Tabs { x: root.inset; y: heading.y + heading.height + 4; width: parent.width - 2*x; context: root.ctx; tabs: root.tabs; visible: !!root.tabs }
    Item { id:body; x:root.inset; y:root.bodyY; width:parent.width-2*x; height:Math.max(0,parent.height-y-root.bottomInset-(root.footerText.length ? 40 : 0))
        Rows {anchors.fill:parent;visible:!root.gridRows;context:root.ctx;rows:visible ? root.rows : [];compact:root.compact;fillAvailable:root.fillRows;offsetMode:root.offsetMode;emptyText:root.emptyText;actionId:root.rowAction}
        DashboardCards {anchors.fill:parent;visible:root.gridRows;context:root.ctx;rows:visible ? root.rows : [];metrics:root.gridMetrics;actionId:root.rowAction}
    }
    Label { x: root.inset; y: parent.height - 34 - root.bottomInset; width: parent.width - 2*x; height: 34; themeStyle: root.style; secondary: true; size: 24; visible: root.footerText.length > 0; text: root.footerText; maximumLineCount: 1 }
}
