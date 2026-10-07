pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Item {
    id: root
    required property ShellContext context
    readonly property var style: context.style
    readonly property bool ready: width > 0 && height > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var mandatoryRegions: [{role:"title",x:32,y:10,width:width-64,height:44},{role:"body",x:width-21,y:80,width:10,height:height-112}]
    readonly property var family: { context.dataRevision; return Format.list(context.families).find(x => x.id === context.currentFamilyId) }
    visible: !context.uiStatus.urgent
    function settleMotion() { familyDots.settleMotion(); viewDots.settleMotion() }
    Rectangle { width:parent.width; height:64; color:root.style.background }
    OutlineIcon { x:32; y:17; opticalSize:28; symbol:Format.familyIcon(root.context.currentFamilyId); tint:root.style.semantic.accentTextOnCanvas }
    Label { x:72; y:9; width:300; height:46; themeStyle:root.style; size:24; font.weight:Font.DemiBold; text:root.family ? root.family.label : "SmartPC"; maximumLineCount:1 }
    NavigationDots {
        id:familyDots; objectName:"familyDots"
        x:(parent.width-width)/2; y:27; width:implicitWidth; height:implicitHeight
        count:root.context.navigation.familyCount; currentPosition:root.context.navigation.familyPosition
        themeStyle:root.style; motionPolicy:root.context.motionPolicy
    }
    NavigationDots {
        id:viewDots; objectName:"viewDots"
        x:parent.width-21; y:80+(parent.height-112-height)/2; width:implicitWidth; height:implicitHeight
        vertical:true; groupId:root.context.navigation.scopeId || root.context.currentFamilyId
        count:root.context.navigation.scopeCount || root.context.navigation.viewCount
        currentPosition:root.context.navigation.scopePosition || root.context.navigation.viewPosition
        themeStyle:root.style; motionPolicy:root.context.motionPolicy
    }
    Label { x:parent.width-164; y:9; width:132; height:46; themeStyle:root.style; size:16; secondary:true; horizontalAlignment:Text.AlignRight; text:[root.context.uiStatus.quiet ? "Quiete" : "",root.context.uiStatus.recovery ? "Ripristino tema" : ""].filter(Boolean).join(" · "); maximumLineCount:2 }
    Rectangle { x:32; y:63; width:parent.width-64; height:1; color:root.style.divider }
}
