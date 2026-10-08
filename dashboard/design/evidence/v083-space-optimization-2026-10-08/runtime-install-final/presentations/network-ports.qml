import QtQuick
import SmartPC.ThemeApi 2.4
Item {
    required property NetworkPortsContext context
    readonly property bool ready:true
    readonly property bool contentReady:true
    NetworkMetricsPanel { anchors.fill:parent;context:parent.context;rowsLayout:false }
}
