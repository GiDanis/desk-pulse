pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format
Item {
    id:root
    required property InfoContext context
    readonly property var style:context.style
    readonly property bool ready:width>0 && height>0
    readonly property bool contentReady:ready
    readonly property string error:""
    readonly property var mandatoryRegions:[{role:"title",x:24,y:16,width:width-48,height:44},{role:"body",x:24,y:76,width:width-48,height:height-92}]
    function settleMotion() {}
    Rectangle {anchors.fill:parent;color:root.style.backgroundOverlay}
    Tabs {x:24;y:16;width:parent.width-48;height:44;context:root.context;tabs:root.context.tabs}
    DashboardCards {x:24;y:76;width:parent.width-48;height:parent.height-92;context:root.context;metrics:true;rows:{root.context.dataRevision;return Format.info(root.context.rows)}}
}
