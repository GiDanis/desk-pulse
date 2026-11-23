import QtQuick
import SmartPC.ThemeApi 2.1
Item {
    id:root
    required property CasaContext context
    readonly property bool ready:true
    readonly property bool contentReady:true
    readonly property int start:Math.floor(Math.max(0,context.selection.index)/4)*4
    Rectangle { anchors.fill:parent;color:root.context.style.backgroundOverlay }
    CasaLabel { visualStyle:root.context.style;x:44;y:30;width:872;font.pixelSize:visualStyle.font37;font.weight:visualStyle.headingWeight;text:"CASA / SMART LIFE" }
    CasaLabel { visualStyle:root.context.style;x:44;y:84;width:872;font.pixelSize:visualStyle.font20;color:visualStyle.textSecondary;text:root.context.description }
    Repeater {
        model:Math.min(4,root.context.rows.count-root.start)
        delegate:Rectangle {
            required property int index
            readonly property var row:root.context.rows.get(root.start+index)
            x:44;y:132+index*87;width:872;height:77;radius:root.context.style.radiusRow
            color:root.start+index===root.context.selection.index ? root.context.style.surfaceFocused : root.context.style.surface
            border.color:root.start+index===root.context.selection.index ? root.context.style.accent : root.context.style.border
            border.width:root.context.style.borderWidth
            CasaLabel { visualStyle:root.context.style;x:18;y:9;width:485;font.pixelSize:visualStyle.font25;color:parent.row && parent.row.enabled ? visualStyle.textPrimary : visualStyle.textSecondary;text:parent.row ? parent.row.title : "" }
            CasaLabel { visualStyle:root.context.style;x:18;y:46;width:820;font.pixelSize:visualStyle.font18;color:visualStyle.textSecondary;text:parent.row ? parent.row.detail : "" }
            CasaLabel { visualStyle:root.context.style;x:515;y:12;width:337;horizontalAlignment:Text.AlignRight;font.pixelSize:visualStyle.font24;text:parent.row ? parent.row.value.displayText : "" }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive && !!parent.row && parent.row.enabled;onClicked:{ root.context.requestAction("selection.select",parent.row.id,{});root.context.requestAction(parent.row.actionId,parent.row.targetId,{}) } }
        }
    }
    CasaLabel { visualStyle:root.context.style;x:44;y:498;width:872;font.pixelSize:visualStyle.font19;color:visualStyle.textSecondary;text:root.context.feedback || root.context.casa.modeText }
    CasaLabel { visualStyle:root.context.style;x:44;y:534;width:872;font.pixelSize:visualStyle.font19;color:visualStyle.textSecondary;text:root.context.casa.quotaConfigured ? "Richieste conteggiate "+root.context.casa.requests+" · margine disponibile "+root.context.casa.remaining : "Quota continuativa da configurare · richieste conteggiate "+root.context.casa.requests }
    CasaLabel { visualStyle:root.context.style;x:44;y:574;width:872;font.pixelSize:visualStyle.font19;color:visualStyle.textSecondary;text:"2/8 SELEZIONA · 5 CAMBIA · 4/6 ORDINE PREFERITI · 7 INDIETRO" }
}
