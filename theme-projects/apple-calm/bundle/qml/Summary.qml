pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Item {
    id: root
    required property SummaryContext context
    readonly property bool ready: summary.ready
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var mandatoryRegions: [{role:"title",x:32,y:20,width:896,height:48},{role:"body",x:32,y:94,width:896,height:514}]
    function settleMotion() { summary.settleMotion() }
    Rectangle { anchors.fill:parent; color:root.context.style.backgroundOverlay }
    Label { x:32; y:20; width:896; height:48; themeStyle:root.context.style; size:34; font.weight:Font.DemiBold; text:"Riepilogo" }
    ClockPage { id:summary; x:32; y:94; width:896; height:514; ctx:root.context }
}
