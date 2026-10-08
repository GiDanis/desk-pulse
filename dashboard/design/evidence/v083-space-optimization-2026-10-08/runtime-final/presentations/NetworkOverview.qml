import QtQuick
import SmartPC.ThemeApi 2.3
Item {
    id:root
    required property NetworkContext context
    property bool rowsLayout:false
    readonly property bool ready:true
    readonly property bool contentReady:true
    readonly property var networkInfo:context.network
    readonly property var rows:context.deviceRows
    NetworkHeader { context:root.context; width:parent.width;height:55 }
    CasaLabel { visualStyle:root.context.style;y:63;width:parent.width;font.pixelSize:visualStyle.font24;text:root.networkInfo.reachableText+" raggiungibili secondo box · "+root.networkInfo.knownCount+" identità note" }
    CasaLabel { visualStyle:root.context.style;y:98;width:parent.width;font.pixelSize:visualStyle.font18;color:visualStyle.textSecondary;text:root.networkInfo.wanText+" · "+root.networkInfo.localText }
    Repeater {
        model:root.context.overviewSection==="tools" ? 0 : Math.min(4,root.rows.count)
        delegate:Rectangle {
            required property int index
            readonly property var device:root.rows.get(index)
            x:root.rowsLayout ? 0 : index%2*(root.width/2+6)
            y:138+(root.rowsLayout ? index*65 : Math.floor(index/2)*136)
            width:root.rowsLayout ? root.width : root.width/2-6
            height:root.rowsLayout ? 57 : 124
            radius:root.context.style.radiusCard
            color:device && device.id===root.context.selection.selectedId && root.context.selection.anchorId!=="network.tabs" ? root.context.style.surfaceFocused : root.context.style.surface
            border.width:root.context.style.borderWidth
            border.color:device && device.id===root.context.selection.selectedId && root.context.selection.anchorId!=="network.tabs" ? root.context.style.accent : root.context.style.border
            CasaLabel { visualStyle:root.context.style;x:16;y:9;width:parent.width-32;font.pixelSize:visualStyle.font25;text:parent.device ? parent.device.name+(parent.device.favourite ? " · ★" : "") : "" }
            CasaLabel { visualStyle:root.context.style;x:16;y:root.rowsLayout ? 34 : 49;width:parent.width-32;font.pixelSize:visualStyle.font18;color:parent.device && parent.device.previous ? visualStyle.semantic.warningOnCard : visualStyle.textSecondary;text:parent.device ? parent.device.statusText : "" }
            CasaLabel { visible:!root.rowsLayout;visualStyle:root.context.style;x:16;y:82;width:parent.width-32;font.pixelSize:visualStyle.font20;color:visualStyle.textSecondary;text:parent.device ? parent.device.primaryAddress : "" }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("details.open",parent.device.id,{}) }
        }
    }
    Repeater {
        model:root.context.overviewSection==="tools" ? root.context.tools.count : 0
        delegate:Rectangle {
            required property int index
            readonly property var row:root.context.tools.get(index)
            y:138+index*86;width:parent.width;height:76;radius:root.context.style.radiusCard
            color:root.context.selection.selectedId===row.id && root.context.selection.anchorId!=="network.tabs" ? root.context.style.surfaceFocused : root.context.style.surface
            CasaLabel { visualStyle:root.context.style;x:18;y:8;width:parent.width-36;font.pixelSize:visualStyle.font25;text:parent.row.title }
            CasaLabel { visualStyle:root.context.style;x:18;y:44;width:parent.width-36;font.pixelSize:visualStyle.font18;color:visualStyle.textSecondary;text:parent.row.detail }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("details.open",parent.row.targetId,{}) }
        }
    }
    CasaLabel {
        visualStyle:root.context.style;anchors.bottom:parent.bottom;width:parent.width
        font.pixelSize:visualStyle.font18;color:visualStyle.textSecondary
        text:root.context.overviewSection==="tools" ? "RIEPILOGO · 5 APRI L’APPROFONDIMENTO SELEZIONATO" : root.context.selection.anchorId==="network.tabs" ? "5 APPROFONDIMENTI · 4/6 VISTA" : "APPROFONDIMENTI · seleziona l’intestazione e premi 5"
        MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("network.metrics.section",root.context.overviewSection==="tools" ? "summary" : "tools",{}) }
    }
}
