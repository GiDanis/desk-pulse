pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format

Item {
    id: root
    property var ctx: null
    property string title: ""
    property string subtitle: ""
    property var source: null
    readonly property var style: ctx ? ctx.style : null
    readonly property bool ready: !!ctx && width > 0 && height > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var mandatoryRegions: [{role:"title", x:0, y:0, width:width, height:76}, {role:"body", x:0, y:90, width:width, height:Math.max(1,height-138)}]
    function settleMotion() { }
    Rectangle { anchors.fill: parent; color: root.style ? root.style.background : "#F3F4F6" }
    Label { x:0; y:0; width:parent.width; height:45; themeStyle:root.style; size:34; font.weight:Font.DemiBold; text:root.title; maximumLineCount:1 }
    Label { x:0; y:46; width:parent.width; height:30; themeStyle:root.style; size:20; secondary:true; text:root.subtitle; maximumLineCount:1 }
    Label { x:0; y:parent.height-35; width:parent.width; height:35; themeStyle:root.style; size:18; secondary:true; text:root.source ? Format.source(root.source) : ""; maximumLineCount:1 }
}
