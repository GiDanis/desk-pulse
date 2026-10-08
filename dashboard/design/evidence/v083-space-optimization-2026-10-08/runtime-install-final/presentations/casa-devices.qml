import QtQuick
import SmartPC.ThemeApi 2.1
Item {
    id:root
    required property CasaContext context
    readonly property bool ready:true
    readonly property bool contentReady:true
    readonly property int selected:Math.max(0,context.casa.devices.indexOf(context.selection.selectedId))
    readonly property int start:Math.floor(selected/4)*4
    CasaHeader { context:root.context; width:parent.width; height:54 }
    Repeater {
        model:Math.min(4,root.context.casa.devices.count-root.start)
        delegate:Rectangle {
            required property int index
            readonly property var device:root.context.casa.devices.get(root.start+index)
            x:0; y:62+index*83; width:root.width; height:73; radius:root.context.style.radiusRow
            color:device && device.id===root.context.selection.selectedId ? root.context.style.surfaceFocused : root.context.style.surface
            border.color:device && device.id===root.context.selection.selectedId ? root.context.style.accent : root.context.style.border
            border.width:root.context.style.borderWidth
            CasaSymbol { x:14;y:18;iconId:parent.device ? parent.device.iconId : "";tint:root.context.style.textPrimary }
            CasaLabel { visualStyle:root.context.style; x:60;y:8;width:460;font.pixelSize:visualStyle.font25;text:parent.device ? parent.device.name : "" }
            CasaLabel { visualStyle:root.context.style; x:60;y:42;width:480;font.pixelSize:visualStyle.font18;color:visualStyle.textSecondary;text:parent.device ? parent.device.primaryText : "" }
            CasaLabel { visualStyle:root.context.style; x:550;y:17;width:parent.width-564;horizontalAlignment:Text.AlignRight;font.pixelSize:visualStyle.font20;color:parent.device && parent.device.previous ? visualStyle.semantic.warningOnCard : visualStyle.textSecondary;text:parent.device ? parent.device.availability+(parent.device.favourite ? " · ★" : "") : "" }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("details.open",parent.device.id,{}) }
        }
    }
    CasaLabel { visualStyle:root.context.style; anchors.bottom:parent.bottom;width:parent.width;color:visualStyle.textSecondary;font.pixelSize:visualStyle.font18;text:(root.selected+1)+"/"+root.context.casa.devices.count+" · 2/8 SELEZIONA · 5 DETTAGLIO" }
}
