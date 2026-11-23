pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.15
import "Format.js" as Format

Item {
    id: root
    required property ShellContext context
    readonly property var style: context.style
    readonly property string overlayLabel: ({"device.info":"Informazioni","overlay.menu":"Menu","overlay.commands":"Comandi"})[context.navigation.overlayId] || (context.navigation.overlayId.indexOf("settings.")===0 ? "Impostazioni" : "")
    readonly property string headerIcon: context.navigation.overlayId==="device.info" ? "info" : context.navigation.overlayId.indexOf("settings.")===0 ? "settings" : Format.familyIcon(context.currentFamilyId)
    readonly property string statusText: [context.uiStatus.recovery ? "Ripristino" : "",context.uiStatus.quiet ? "Quiete" : ""].filter(Boolean).join(" · ")
    readonly property bool pageShowsClock: !context.navigation.overlayId
        && (context.currentViewId === "home.now" || context.currentViewId === "home.clock")
    readonly property string scopeLabel: ({sport:"Calcio",f1:"Formula 1",motogp:"MotoGP"})[context.navigation.scopeId] || ""
    readonly property string homeLabel: context.currentViewId === "home.clock" ? "Orologio" : ""
    readonly property bool ready: width > 0 && height > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var mandatoryRegions: [{role:"title",x:24,y:6,width:760,height:44},{role:"body",x:width-24,y:72,width:10,height:height-88}]
        .concat(pageShowsClock ? [] : [{role:"clock",x:width-164,y:5,width:140,height:46}])
    readonly property var family: { context.dataRevision; return Format.list(context.families).find(x => x.id === context.currentFamilyId) }
    visible: !context.uiStatus.urgent
    function settleMotion() { familyDots.settleMotion(); viewDots.settleMotion() }
    Rectangle { width:parent.width; height:56; color:root.style.background }
    OutlineIcon { x:24; y:12; opticalSize:32; symbol:root.headerIcon; tint:root.style.semantic.accentTextOnCanvas }
    Label { x:64; y:5; width:root.statusText ? 410 : Math.max(0,familyDots.x-x-18); height:46; themeStyle:root.style; size:32; font.weight:Font.DemiBold; text:root.overlayLabel || root.homeLabel || (root.context.currentFamilyId === "account" ? "Account" : root.family ? root.family.label : "SmartPC"); maximumLineCount:1 }
    NavigationDots {
        id:familyDots; objectName:"familyDots"
        x:(parent.width-width)/2; y:23; width:implicitWidth; height:implicitHeight
        count:root.context.navigation.familyCount; currentPosition:root.context.navigation.familyPosition
        visible:!root.statusText
        themeStyle:root.style; motionPolicy:root.context.motionPolicy
    }
    NavigationDots {
        id:viewDots; objectName:"viewDots"
        visible:root.context.navigation.overlayId!=="device.info" && root.context.navigation.overlayId.indexOf("settings.")!==0
        x:parent.width-24; y:72+(parent.height-88-height)/2; width:implicitWidth; height:implicitHeight
        vertical:true; groupId:root.context.navigation.scopeId || root.context.currentFamilyId
        count:root.context.navigation.scopeCount || root.context.navigation.viewCount
        currentPosition:root.context.navigation.scopePosition || root.context.navigation.viewPosition
        themeStyle:root.style; motionPolicy:root.context.motionPolicy
    }
    Label { objectName:"headerClock"; x:parent.width-164; y:5; width:140; height:46; themeStyle:root.style; size:28; font.family:root.style.numbersFamily; horizontalAlignment:Text.AlignRight; text:root.context.clock.timeText; maximumLineCount:1; visible:!root.pageShowsClock }
    Label { objectName:"headerStatus"; x:490; y:5; width:216; height:46; visible:!!root.statusText; themeStyle:root.style; size:22; secondary:true; horizontalAlignment:Text.AlignRight; text:root.statusText; maximumLineCount:2 }
    Label { objectName:"headerScope";x:familyDots.x+familyDots.width+18;y:5;width:Math.max(0,headerAlerts.x-x-16);height:46;visible:!root.statusText && !!root.scopeLabel;themeStyle:root.style;size:23;secondary:true;text:root.scopeLabel;maximumLineCount:1 }
    Item {
        id:headerAlerts
        objectName:"headerAlerts";x:714;y:6;width:92;height:44;visible:root.context.uiStatus.notificationsAvailable
        OutlineIcon { x:2;y:6;symbol:"bell";opticalSize:32;tint:root.context.uiStatus.unreadCount>0 ? root.style.semantic.accentTextOnCanvas : root.style.textSecondary }
        Label { x:38;width:54;height:44;themeStyle:root.style;size:24;visible:root.context.uiStatus.unreadCount>0;text:root.context.uiStatus.unreadCount>99 ? "99+" : String(root.context.uiStatus.unreadCount);maximumLineCount:1 }
        MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("navigation.inbox","",{}) }
    }
    Rectangle { x:24; y:55; width:parent.width-48; height:1; color:root.style.divider }
}
