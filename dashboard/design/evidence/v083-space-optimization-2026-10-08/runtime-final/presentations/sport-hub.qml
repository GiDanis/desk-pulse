import QtQuick
import SmartPC.ThemeApi 2.5
import "../icons"
Item {
    id: root
    required property SportHubContext context
    readonly property bool ready: true
    readonly property bool contentReady: true
    readonly property int selected: Math.max(0,context.rows.indexOf(context.selection.selectedId))
    readonly property int capacity: Math.max(1,Math.min(3,Math.floor((height-70)/(116*context.style.textScale))))
    readonly property int start: Math.floor(selected/capacity)*capacity
    readonly property real rowHeight: (height-70)/capacity
    CasaLabel { visualStyle:root.context.style; width:parent.width; text:"Scegli una disciplina"; font.pixelSize:visualStyle.font36; font.weight:visualStyle.headingWeight }
    Repeater {
        model:Math.min(root.capacity,root.context.rows.count-root.start)
        delegate:Rectangle {
            required property int index
            readonly property var row:root.context.rows.get(root.start+index)
            readonly property bool selectedState:row.id===root.context.selection.selectedId
            color:selectedState ? root.context.style.surfaceFocused : root.context.style.surface
            border.width:selectedState ? root.context.style.focusWidth : root.context.style.borderWidth
            border.color:selectedState ? root.context.style.semantic.focusIndicator : root.context.style.border
            radius:root.context.style.radiusRow
            x:0;y:52+index*root.rowHeight;width:root.width;height:root.rowHeight-10
            GeometryIcon { x:18;y:20;opticalSize:40;symbol:({sport:"football",f1:"race-car",motogp:"motorcycle"})[parent.row.id];tint:root.context.style.semantic.accentTextOnCard }
            CasaLabel { visualStyle:root.context.style;x:78;y:12;width:parent.width-104;height:52;font.pixelSize:visualStyle.font45;font.weight:visualStyle.headingWeight;text:parent.row.title }
            CasaLabel { visualStyle:root.context.style;x:78;y:69;width:parent.width-104;height:36;font.pixelSize:visualStyle.font25;color:visualStyle.textSecondary;text:parent.row.detail }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("details.open",parent.row.id,{}) }
        }
    }
    CasaLabel { visualStyle:root.context.style;anchors.bottom:parent.bottom;width:parent.width;text:root.context.rows.count ? (root.selected+1)+" / "+root.context.rows.count+" · 5 APRI · 7 INDIETRO" : "Nessuna disciplina abilitata";font.pixelSize:visualStyle.font22;color:visualStyle.textSecondary }
}
