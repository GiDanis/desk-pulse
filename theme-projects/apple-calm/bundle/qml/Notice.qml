pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format

Item {
    id: root
    property var ctx: null
    property string mode: "small"
    readonly property var style: ctx ? ctx.style : null
    readonly property var visual: ctx ? ctx.visualStyle : null
    readonly property var event: ctx ? ctx.eventData : null
    readonly property bool full: mode === "urgent" || mode === "detail" || mode === "inbox"
    readonly property bool tiny: height < 150
    readonly property bool ready: !!ctx && width > 0 && height > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property real scrollMaximum: mode === "detail" ? Math.max(0,scroll.contentHeight-scroll.height) : 0
    readonly property var mandatoryRegions: mode === "badge" ? [{role:"body",x:10,y:0,width:width-20,height:height}] : [{role:"title",x:24,y:16,width:width-48,height:40},{role:"body",x:24,y:56,width:width-48,height:Math.max(1,height-64)}]
    readonly property var events: { if (!ctx) return []; ctx.appearanceRevision; return Format.list(ctx.itemModel) }
    readonly property int selected: ctx ? Math.max(0,events.findIndex(x => x.id === ctx.selectedEventId)) : 0
    readonly property int capacity: Math.max(1,Math.floor((height-125)/100))
    readonly property int first: Math.floor(selected/capacity)*capacity
    implicitWidth: mode === "badge" ? 180 : 896
    implicitHeight: mode === "badge" ? 44 : mode === "small" ? 124 : mode === "large" ? 340 : 560
    function settleMotion() { }
    Rectangle { anchors.fill:parent; radius:root.full ? 0 : root.visual ? root.visual.noticeRadius : 24; color:root.visual ? root.visual.surfaceColor : "#FFFFFF"; border.width:root.full ? 0 : 1; border.color:root.visual ? root.visual.noticeBorder : "#CDD2DA" }
    Rectangle { x:0; y:0; width:root.mode === "urgent" ? parent.width : 4; height:root.mode === "urgent" ? 6 : parent.height; radius:2; color:root.style ? root.event && (root.event.weatherSeverity === "rossa" || root.event.severity === "critical") ? root.style.semantic.criticalIndicator : root.mode === "urgent" ? root.style.semantic.warningIndicator : root.style.semantic.accentDecoration : "#0066CC"; visible:root.mode !== "badge" && root.mode !== "inbox" && root.mode !== "detail" }
    OutlineIcon { x:root.mode === "badge" ? 12 : 24; y:root.mode === "badge" ? (parent.height-26)/2 : 24; opticalSize:root.mode === "badge" ? 26 : 36; iconId:root.ctx ? root.ctx.iconId : "notification.default"; tint:root.visual ? root.visual.noticeAccent : "#0066CC"; visible:root.mode !== "inbox" && (!root.visual || root.visual.showIcon) }
    Label { x:48; y:0; width:parent.width-58; height:parent.height; themeStyle:root.style; size:18; text:root.ctx ? root.ctx.unreadCount + " avvisi" : "Avvisi"; color:root.visual ? root.visual.badgeTextColor : "#0066CC"; visible:root.mode === "badge"; maximumLineCount:1 }
    MouseArea { anchors.fill:parent; visible:root.mode === "badge"; enabled:root.ctx && root.ctx.interactive; onClicked:root.ctx.request("openInbox","",{}) }
    Label { id:title; objectName:"notificationTitle"; x:root.visual && root.visual.showIcon ? 80 : 24; y:root.full ? 20 : 13; width:parent.width-x-24; height:root.mode === "large" ? 76 : 42; themeStyle:root.style; size:root.full ? 30 : 26; font.weight:Font.DemiBold; text:root.mode === "inbox" ? "Avvisi" : root.mode === "detail" ? "Dettaglio avviso" : root.mode === "urgent" ? "Avviso prioritario" : root.event ? root.event.title : "Avviso"; color:root.visual ? root.visual.titleColor : "#1D1D1F"; visible:root.mode !== "badge"; maximumLineCount:root.mode === "large" ? 2 : 1 }
    Label { objectName:"notificationBody"; x:24; y:root.mode === "large" ? 106 : 59; width:parent.width-48; height:root.mode === "large" ? parent.height-140 : Math.max(1,parent.height-y-12); themeStyle:root.style; size:root.mode === "large" ? 24 : 20; text:root.event ? root.event.body : "Nessun contenuto disponibile"; color:root.visual ? root.visual.bodyColor : "#5D626C"; visible:!root.full && root.mode !== "badge"; maximumLineCount:root.mode === "large" ? 5 : 1 }
    Flickable {
        id:scroll; objectName:"notificationScroll"
        x:24; y:root.mode === "urgent" ? 92 : 82; width:parent.width-48; height:Math.max(1,parent.height-y-55)
        contentWidth:width; contentHeight:article.height; contentY:Math.max(0,Math.min(root.ctx ? root.ctx.scrollOffset : 0,root.scrollMaximum))
        clip:true; boundsBehavior:Flickable.StopAtBounds; interactive:root.ctx && root.ctx.interactive && root.mode === "detail"
        visible:root.full && root.mode !== "inbox" && !root.tiny
        onMovementEnded: if (root.ctx && root.mode === "detail") root.ctx.request("scrollDetails","",{delta:contentY-root.ctx.scrollOffset})
        Column {
            id:article; width:scroll.width; spacing:18
            Label { width:parent.width; height:implicitHeight; themeStyle:root.style; size:34; font.weight:Font.DemiBold; text:root.event ? root.event.title : "Avviso non disponibile"; color:root.visual ? root.visual.titleColor : "#1D1D1F"; maximumLineCount:100 }
            Label { width:parent.width; height:implicitHeight; themeStyle:root.style; size:24; text:root.event ? root.event.body : "Nessun contenuto disponibile"; color:root.visual ? root.visual.bodyColor : "#5D626C"; maximumLineCount:1000 }
            Label { objectName:"notificationSource"; width:parent.width; height:implicitHeight; themeStyle:root.style; size:18; secondary:true; text:root.ctx ? root.ctx.sourceText + "\n" + root.ctx.validityText + (root.ctx.sourceMetadata ? "\n" + Format.source(root.ctx.sourceMetadata) : "") : ""; visible:!root.visual || root.visual.showSource; maximumLineCount:100 }
        }
    }
    Repeater {
        model:root.mode === "inbox" && !root.tiny ? root.events.slice(root.first,root.first+root.capacity) : []
        delegate: Card {
                id: noticeCard
            required property var modelData
            required property int index
            readonly property bool focused: root.ctx && noticeCard.modelData.id === root.ctx.selectedEventId
            objectName:"alertRow"+(root.first+index)
            x:24; y:86+index*100; width:root.width-48; height:90; style:root.style
            color:focused ? root.visual.noticeFocusedSurface : root.visual.surfaceColor
            border.width:focused ? 3 : 1; border.color:focused ? root.style.semantic.focusIndicator : root.style.border
            Label { x:18; y:8; width:parent.width-36; height:36; themeStyle:root.style; size:24; font.weight:Font.DemiBold; text:(noticeCard.modelData.seen ? "" : "●  ")+noticeCard.modelData.title; maximumLineCount:1 }
            Label { x:18; y:46; width:parent.width-36; height:31; themeStyle:root.style; size:20; secondary:true; text:noticeCard.modelData.body; maximumLineCount:1 }
            MouseArea { anchors.fill:parent; enabled:root.ctx && root.ctx.interactive; onClicked:{ root.ctx.request("selectEvent",noticeCard.modelData.id,{}); root.ctx.request("openDetails",noticeCard.modelData.id,{}) } }
        }
    }
    Label { x:24; y:82; width:parent.width-48; height:Math.max(1,parent.height-140); themeStyle:root.style; size:26; secondary:true; text:"Nessun avviso attivo"; horizontalAlignment:Text.AlignHCenter; visible:root.mode === "inbox" && root.events.length === 0 && !root.tiny }
    Label { x:24; y:parent.height-43; width:parent.width-48; height:32; themeStyle:root.style; size:18; secondary:true; text:root.mode === "inbox" && root.ctx ? "Stato avvisi: " + root.ctx.sourceStatus + (root.events.length ? " · " + (root.selected+1) + " / " + root.events.length : "") : root.ctx ? root.ctx.sourceText : ""; visible:(root.mode === "large" || root.mode === "inbox") && !root.tiny && (!root.visual || root.visual.showSource); maximumLineCount:1 }
}
