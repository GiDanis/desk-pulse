pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format
Item {
    id:root
    property var ctx:null
    property string mode:"small"
    readonly property var style:ctx ? ctx.style : null
    readonly property var visual:ctx ? ctx.visualStyle : null
    readonly property var event:ctx ? ctx.eventData : null
    readonly property bool full:mode === "urgent" || mode === "detail" || mode === "inbox"
    readonly property bool tiny:height < 140
    readonly property bool ready:!!ctx && width > 0 && height > 0
    readonly property bool contentReady:ready
    readonly property string error:""
    readonly property real scrollMaximum:mode === "detail" ? Math.max(0,scroll.contentHeight-scroll.height) : 0
    readonly property var mandatoryRegions:mode === "badge" ? [{role:"body",x:12,y:0,width:Math.max(1,width-24),height:height}] : [{role:"title",x:24,y:12,width:width-48,height:76},{role:"body",x:24,y:92,width:width-48,height:Math.max(1,height-104)}]
    readonly property var events:{if(!ctx)return [];ctx.appearanceRevision;return Format.list(ctx.itemModel)}
    readonly property int selected:ctx ? Math.max(0,events.findIndex(x=>x.id === ctx.selectedEventId)) : 0
    readonly property int rowHeight:Math.round(144*(style ? style.textScale : 1))
    readonly property int capacity:Math.max(1,Math.floor((height-112)/rowHeight))
    readonly property int first:Math.floor(selected/capacity)*capacity
    readonly property color accent:style ? event && (event.severity === "critical" || event.weatherSeverity === "rossa") ? style.semantic.criticalIndicator : mode === "urgent" ? style.semantic.warningIndicator : style.semantic.accentDecoration : "#0066CC"
    implicitWidth:mode === "badge" ? 180 : 896
    implicitHeight:mode === "badge" ? 44 : mode === "small" ? 152 : mode === "large" ? 260 : 560
    function settleMotion() { }
    Rectangle { anchors.fill:parent;radius:root.full ? 0 : root.visual ? root.visual.noticeRadius : 24;color:root.visual ? root.visual.surfaceColor : "#FFFFFF";border.width:root.full ? 0 : 1;border.color:root.visual ? root.visual.noticeBorder : "#CDD2DA" }
    Rectangle { x:0;y:0;width:parent.width;height:root.mode === "urgent" ? 6 : 0;color:root.accent }
    OutlineIcon { x:12;y:(parent.height-26)/2;opticalSize:26;symbol:"bell";tint:root.accent;visible:root.mode === "badge" }
    Label { x:48;y:0;width:parent.width-58;height:parent.height;themeStyle:root.style;size:22;text:root.ctx ? root.ctx.unreadCount+" avvisi" : "Avvisi";visible:root.mode === "badge";maximumLineCount:1 }
    MouseArea { anchors.fill:parent;visible:root.mode === "badge";enabled:root.ctx && root.ctx.interactive;onClicked:root.ctx.request("openInbox","",{}) }
    NoticeHeading {
        x:24;y:12;width:parent.width-48;height:78;themeStyle:root.style;eventData:root.mode === "inbox" ? null : root.event
        heading:root.mode === "inbox" ? "Avvisi" : root.mode === "detail" ? "Dettaglio avviso" : root.mode === "urgent" ? "Avviso prioritario" : root.event ? root.event.title : "Avviso"
        compact:root.mode === "inbox";showIcon:!root.visual || root.visual.showIcon;accent:root.accent;visible:root.mode !== "badge"
    }
    Label { objectName:"notificationBody";x:80;y:94;width:parent.width-104;height:Math.max(1,parent.height-y-14);themeStyle:root.style;size:24;text:root.event ? root.event.body : "Nessun contenuto disponibile";visible:!root.full && root.mode !== "badge";maximumLineCount:root.mode === "large" ? 4 : 1 }
    Flickable {
        id:scroll;objectName:"notificationScroll";x:24;y:100;width:parent.width-48;height:Math.max(1,parent.height-y-48)
        contentWidth:width;contentHeight:article.height;contentY:Math.max(0,Math.min(root.ctx ? root.ctx.scrollOffset : 0,root.scrollMaximum))
        clip:true;boundsBehavior:Flickable.StopAtBounds;interactive:root.ctx && root.ctx.interactive && root.mode === "detail"
        visible:root.full && root.mode !== "inbox" && !root.tiny
        onMovementEnded:if(root.ctx && root.mode === "detail")root.ctx.request("scrollDetails","",{delta:contentY-root.ctx.scrollOffset})
        Column {
            id:article;width:scroll.width;spacing:16
            Label { width:parent.width;height:implicitHeight;themeStyle:root.style;size:32;font.weight:Font.DemiBold;text:root.event ? root.event.title : "Avviso non disponibile";maximumLineCount:100 }
            Label { width:parent.width;height:implicitHeight;themeStyle:root.style;size:26;text:root.event ? root.event.body : "Nessun contenuto disponibile";maximumLineCount:1000 }
            Label {
                objectName:"notificationSource";width:parent.width;height:implicitHeight;themeStyle:root.style;size:24;secondary:true
                text:root.event ? ["Fonte: "+(root.event.sourceLabel || "Non disponibile"),"Emesso "+(Format.stamp(root.event.issuedAt) || "Non disponibile"),"Validità: "+(Format.stamp(root.event.expiresAt) || "Non disponibile"),Format.noticeState(root.event),root.ctx && root.ctx.sourceMetadata ? Format.source(root.ctx.sourceMetadata) : ""].filter(Boolean).join("\n") : ""
                visible:!root.visual || root.visual.showSource;maximumLineCount:100
            }
        }
    }
    Repeater {
        model:root.mode === "inbox" && !root.tiny ? root.events.slice(root.first,root.first+root.capacity) : []
        delegate:NoticeRow { required property var modelData;required property int index;objectName:"alertRow"+(root.first+index);x:24;y:78+index*root.rowHeight;width:root.width-48;height:root.rowHeight-10;context:root.ctx;eventData:modelData;selected:root.ctx && modelData.id === root.ctx.selectedEventId }
    }
    Label { x:24;y:90;width:parent.width-48;height:Math.max(1,parent.height-150);themeStyle:root.style;size:26;secondary:true;text:"Nessun avviso attivo";horizontalAlignment:Text.AlignHCenter;visible:root.mode === "inbox" && root.events.length === 0 }
    Label { x:24;y:parent.height-38;width:parent.width-48;height:32;themeStyle:root.style;size:22;secondary:true;text:root.mode === "inbox" && root.ctx ? "Centro avvisi · "+root.ctx.sourceStatus+(root.events.length ? " · "+(root.selected+1)+" / "+root.events.length : "") : root.mode === "urgent" ? "5 Dettagli · 7 Chiudi" : "2/8 Scorri · 7 Indietro";visible:root.full && !root.tiny;maximumLineCount:1 }
}
