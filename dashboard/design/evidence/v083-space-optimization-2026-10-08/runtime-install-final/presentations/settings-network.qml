import QtQuick
import SmartPC.ThemeApi 2.3
Item {
    id:root
    required property NetworkContext context
    readonly property bool ready:true
    readonly property bool contentReady:true
    readonly property int start:Math.floor(Math.max(0,context.selection.index)/3)*3
    Rectangle { anchors.fill:parent;color:root.context.style.backgroundOverlay }
    CasaLabel { visualStyle:root.context.style;x:44;y:30;width:872;font.pixelSize:visualStyle.font37;font.weight:visualStyle.headingWeight;text:"RETE LOCALE / ILIADBOX" }
    CasaLabel { visualStyle:root.context.style;x:44;y:84;width:872;font.pixelSize:visualStyle.font24;color:visualStyle.textSecondary;text:root.context.description }
    Repeater {
        model:Math.max(0,Math.min(3,root.context.rows.count-root.start))
        delegate:Rectangle {
            required property int index
            readonly property var row:root.context.rows.get(root.start+index)
            x:44;y:132+index*112;width:872;height:104;radius:root.context.style.radiusRow
            color:root.start+index===root.context.selection.index ? root.context.style.surfaceFocused : root.context.style.surface
            border.color:root.start+index===root.context.selection.index ? root.context.style.accent : root.context.style.border
            border.width:root.context.style.borderWidth
            CasaLabel { visualStyle:root.context.style;x:18;y:9;width:485;font.pixelSize:visualStyle.font32;color:parent.row && parent.row.enabled ? visualStyle.textPrimary : visualStyle.textSecondary;text:parent.row ? parent.row.title : "" }
            CasaLabel { visualStyle:root.context.style;x:18;y:parent.height-38;width:820;font.pixelSize:visualStyle.font24;color:visualStyle.textSecondary;text:parent.row ? parent.row.detail : "" }
            CasaLabel { visualStyle:root.context.style;x:515;y:12;width:337;horizontalAlignment:Text.AlignRight;font.pixelSize:visualStyle.font24;text:parent.row ? parent.row.value.displayText : "" }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive && !!parent.row && parent.row.enabled;onClicked:{ root.context.requestAction("selection.select",parent.row.id,{});root.context.requestAction(parent.row.actionId,parent.row.targetId,{}) } }
        }
    }
    CasaLabel { visualStyle:root.context.style;x:44;y:root.height-82;width:872;font.pixelSize:visualStyle.font24;color:visualStyle.textSecondary;text:root.context.feedback || root.context.network.modeText }

    CasaLabel { visualStyle:root.context.style;x:44;y:root.height-36;width:872;font.pixelSize:visualStyle.font24;color:visualStyle.textSecondary;text:"2/8 SELEZIONA · 5 CAMBIA · 4/6 ORDINE PREFERITI · 7 INDIETRO" }
}
