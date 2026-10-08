import QtQuick
import SmartPC.ThemeApi 2.1
Item {
    id: root
    required property CasaContext context
    readonly property bool ready: true
    readonly property bool contentReady: true
    property bool rowsLayout: false
    CasaHeader { context:root.context; width:parent.width; height:54 }
    Repeater {
        model:root.context.casa.favourites
        delegate: Rectangle {
            id: tile
            required property var item
            required property int index
            objectName:"casaTile"+index
            x:root.rowsLayout ? 0 : index%2*(width+16)
            y:62+(root.rowsLayout ? index*(height+10) : Math.floor(index/2)*(height+16))
            width:root.rowsLayout ? root.width : (root.width-16)/2
            height:root.rowsLayout ? (root.height-88)/4-10 : (root.height-100)/2
            radius:root.context.style.radiusCard
            color:root.context.selection.selectedId===item.id ? root.context.style.surfaceFocused : root.context.style.surface
            border.width:root.context.selection.selectedId===item.id ? root.context.style.focusWidth : root.context.style.borderWidth
            border.color:root.context.selection.selectedId===item.id ? root.context.style.accent : root.context.style.border
            CasaSymbol { x:16; y:15; iconId:tile.item.iconId; tint:root.context.style.textPrimary }
            CasaLabel { visualStyle:root.context.style; x:60; y:13; width:root.rowsLayout ? 300 : parent.width-76; text:tile.item.name; font.pixelSize:visualStyle.font25; font.weight:visualStyle.headingWeight }
            CasaLabel { visualStyle:root.context.style; x:root.rowsLayout ? 380 : 16; y:root.rowsLayout ? 10 : 50; width:root.rowsLayout ? 260 : parent.width-32; text:tile.item.primaryText; font.pixelSize:root.rowsLayout ? visualStyle.font28 : visualStyle.font34; font.family:visualStyle.numbersFamily; elide:Text.ElideRight }
            CasaLabel { visualStyle:root.context.style; x:16; y:root.rowsLayout ? 45 : 98; width:root.rowsLayout ? 330 : parent.width-32; text:tile.item.availability+(tile.item.availabilityPrevious ? " · salvata" : ""); color:tile.item.previous ? visualStyle.semantic.warningOnCard : visualStyle.textSecondary; font.pixelSize:visualStyle.font21 }
            CasaLabel { visualStyle:root.context.style; x:root.rowsLayout ? 380 : 16; y:root.rowsLayout ? 46 : 133; width:root.rowsLayout ? 330 : parent.width-32; text:tile.item.previous ? "Dato precedente"+(tile.item.secondaryText ? " · "+tile.item.secondaryText : "") : tile.item.secondaryText || "Ultimo stato riportato"; color:visualStyle.textSecondary; font.pixelSize:visualStyle.font18 }
            MouseArea { anchors.fill:parent; enabled:root.context.lifecycle.interactive; onClicked:root.context.requestAction("details.open",tile.item.id,{}) }
        }
    }
    CasaLabel { visualStyle:root.context.style; anchors.centerIn:parent; width:parent.width; horizontalAlignment:Text.AlignHCenter; visible:root.context.casa.favourites.count===0; text:"Scegli i dispositivi in Impostazioni → Casa" }
    CasaLabel { visualStyle:root.context.style; anchors.bottom:parent.bottom; width:parent.width; font.pixelSize:visualStyle.font18; color:visualStyle.textSecondary; text:"2/8 SELEZIONA · 5 DETTAGLIO · 2 DALLA PRIMA: 4/6 CAMBIA VISTA" }
}
