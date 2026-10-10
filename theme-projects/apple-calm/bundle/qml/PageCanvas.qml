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
    readonly property real bodyTop:48
    readonly property real bodyHeight:Math.max(1,height-bodyTop)
    readonly property bool ready: !!ctx && width > 0 && height > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var mandatoryRegions: [{role:"title", x:0, y:0, width:width, height:42}, {role:"body", x:0, y:48, width:width, height:Math.max(1,height-48)}]
    function settleMotion() { }
    Rectangle { anchors.fill: parent; color: root.style ? root.style.background : "#F3F4F6" }
    Label { x:0; y:0; width:parent.width*0.45; height:42; themeStyle:root.style; size:32; font.weight:Font.DemiBold; text:root.title; maximumLineCount:1 }
    Label { x:parent.width*0.47; y:0; width:parent.width-x; height:42; themeStyle:root.style; size:20; secondary:true; text:[root.subtitle,root.source ? Format.source(root.source) : ""].filter(Boolean).join(" · ");horizontalAlignment:Text.AlignRight; maximumLineCount:1 }
    Label { x:0; y:parent.height-35; width:parent.width; height:35; themeStyle:root.style; size:18; secondary:true; text:"";visible:false; maximumLineCount:1 }
}
