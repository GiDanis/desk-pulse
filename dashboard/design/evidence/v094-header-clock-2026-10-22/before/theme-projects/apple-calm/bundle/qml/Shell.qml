pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Item {
    id: root
    required property ShellContext context
    readonly property var style: context.style
    readonly property string overlayLabel: ({"device.info":"Informazioni","overlay.menu":"Menu","overlay.commands":"Comandi"})[context.navigation.overlayId] || (context.navigation.overlayId.indexOf("settings.")===0 ? "Impostazioni" : "")
    readonly property string headerIcon: context.navigation.overlayId==="device.info" ? "info" : context.navigation.overlayId.indexOf("settings.")===0 ? "settings" : Format.familyIcon(context.currentFamilyId)
    readonly property bool ready: width > 0 && height > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var mandatoryRegions: [{role:"title",x:24,y:6,width:width-48,height:44},{role:"body",x:width-21,y:72,width:10,height:height-88}]
    readonly property var family: { context.dataRevision; return Format.list(context.families).find(x => x.id === context.currentFamilyId) }
    visible: !context.uiStatus.urgent
    function settleMotion() { familyDots.settleMotion(); viewDots.settleMotion() }
    Rectangle { width:parent.width; height:56; color:root.style.background }
    OutlineIcon { x:24; y:13; opticalSize:28; symbol:root.headerIcon; tint:root.style.semantic.accentTextOnCanvas }
    Label { x:64; y:5; width:290; height:46; themeStyle:root.style; size:32; font.weight:Font.DemiBold; text:root.overlayLabel || (root.family ? root.family.label : "SmartPC"); maximumLineCount:1 }
    NavigationDots {
        id:familyDots; objectName:"familyDots"
        x:(parent.width-width)/2; y:23; width:implicitWidth; height:implicitHeight
        count:root.context.navigation.familyCount; currentPosition:root.context.navigation.familyPosition
        themeStyle:root.style; motionPolicy:root.context.motionPolicy
    }
    NavigationDots {
        id:viewDots; objectName:"viewDots"
        visible:root.context.navigation.overlayId!=="device.info" && root.context.navigation.overlayId.indexOf("settings.")!==0
        x:parent.width-21; y:72+(parent.height-88-height)/2; width:implicitWidth; height:implicitHeight
        vertical:true; groupId:root.context.navigation.scopeId || root.context.currentFamilyId
        count:root.context.navigation.scopeCount || root.context.navigation.viewCount
        currentPosition:root.context.navigation.scopePosition || root.context.navigation.viewPosition
        themeStyle:root.style; motionPolicy:root.context.motionPolicy
    }
    Label { x:parent.width-164; y:5; width:132; height:46; themeStyle:root.style; size:24; secondary:true; horizontalAlignment:Text.AlignRight; text:[root.context.uiStatus.quiet ? "Quiete" : "",root.context.uiStatus.recovery ? "Ripristino tema" : ""].filter(Boolean).join(" · "); maximumLineCount:2 }
    Label { x:560; y:5; width:220; height:46; themeStyle:root.style; size:26; secondary:true; text:({sport:"Calcio",f1:"Formula 1",motogp:"MotoGP"})[root.context.navigation.scopeId] || ""; maximumLineCount:1 }
    Rectangle { x:24; y:55; width:parent.width-48; height:1; color:root.style.divider }
}
