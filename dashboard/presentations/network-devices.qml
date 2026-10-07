import QtQuick
import SmartPC.ThemeApi 2.3
Item {
    id:root
    required property NetworkContext context
    readonly property bool ready:true
    readonly property bool contentReady:true
    readonly property int selected:Math.max(0,context.deviceRows.indexOf(context.selection.selectedId))
    readonly property int start:Math.floor(selected/4)*4
    NetworkHeader { context:root.context;width:parent.width;height:55 }
    CasaLabel { visualStyle:root.context.style;y:65;width:parent.width;font.pixelSize:visualStyle.font20;text:"Filtro: "+root.context.description+" · "+root.context.deviceRows.count+" identità · seleziona le schede con 2, poi 5 per il filtro" }
    MouseArea { x:0;y:62;width:parent.width;height:32;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("network.filter.step","network",{direction:1}) }
    Repeater {
        model:Math.max(0,Math.min(4,root.context.deviceRows.count-root.start))
        delegate:Rectangle {
            required property int index
            readonly property var device:root.context.deviceRows.get(root.start+index)
            x:0;y:104+index*77;width:root.width;height:68;radius:root.context.style.radiusRow
            color:device && device.id===root.context.selection.selectedId ? root.context.style.surfaceFocused : root.context.style.surface
            border.color:device && device.id===root.context.selection.selectedId ? root.context.style.accent : root.context.style.border
            border.width:root.context.style.borderWidth
            CasaLabel { visualStyle:root.context.style;x:16;y:6;width:480;font.pixelSize:visualStyle.font25;text:parent.device ? parent.device.name+(parent.device.favourite ? " · ★" : "") : "" }
            CasaLabel { visualStyle:root.context.style;x:16;y:40;width:parent.width-32;font.pixelSize:visualStyle.font18;color:visualStyle.textSecondary;text:parent.device ? parent.device.primaryAddress+" · "+parent.device.connectionText : "" }
            CasaLabel { visualStyle:root.context.style;x:510;y:11;width:parent.width-526;horizontalAlignment:Text.AlignRight;font.pixelSize:visualStyle.font18;color:parent.device && parent.device.previous ? visualStyle.semantic.warningOnCard : visualStyle.textSecondary;text:parent.device ? parent.device.statusText : "" }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("details.open",parent.device.id,{}) }
        }
    }
    CasaLabel { visualStyle:root.context.style;y:145;width:parent.width;visible:root.context.deviceRows.count===0;font.pixelSize:visualStyle.font25;text:"Nessuna identità in questo filtro" }
    CasaLabel { visualStyle:root.context.style;anchors.bottom:parent.bottom;width:parent.width;font.pixelSize:visualStyle.font18;color:visualStyle.textSecondary;text:(root.context.deviceRows.count ? (root.selected+1)+"/"+root.context.deviceRows.count+" · " : "")+"2/8 SELEZIONA · 5 DETTAGLIO · dati del router" }
}
