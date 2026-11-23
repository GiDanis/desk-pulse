import QtQuick
import SmartPC.ThemeApi 2.1
Item {
    id: root
    required property CasaContext context
    readonly property bool ready: true
    readonly property bool contentReady: true
    property bool rowsLayout: false
    readonly property var devices:context.contentId==="casa.devices" ? context.casa.devices : context.casa.favourites
    readonly property int selected:Math.max(0,devices.indexOf(context.selection.selectedId))
    readonly property int start:context.contentId==="casa.devices" ? Math.floor(selected/4)*4 : 0
    readonly property real bodyTop:82
    readonly property real tileHeight:rowsLayout ? (height-bodyTop-30)/4 : (height-bodyTop-16)/2
    CasaHeader { context:root.context;width:parent.width;height:70 }
    Repeater {
        model:Math.max(0,Math.min(4,root.devices.count-root.start))
        delegate:Rectangle {
            id:tile
            readonly property var item:root.devices.get(root.start+index)
            required property int index
            readonly property bool selectedState:root.context.selection.selectedId===item.id && root.context.selection.anchorId!=="casa.tabs"
            objectName:"casaTile"+index
            x:root.rowsLayout ? 0 : index%2*(width+16)
            y:root.bodyTop+(root.rowsLayout ? index*(height+10) : Math.floor(index/2)*(height+16))
            width:root.rowsLayout ? root.width : (root.width-16)/2
            height:root.tileHeight
            radius:root.context.style.radiusCard
            color:selectedState ? root.context.style.surfaceFocused : root.context.style.surface
            border.width:selectedState ? root.context.style.focusWidth : root.context.style.borderWidth
            border.color:selectedState ? root.context.style.semantic.focusIndicator : root.context.style.border
            CasaSymbol { x:16;y:16;iconId:tile.item.iconId;tint:root.context.style.semantic.accentTextOnCard }
            CasaLabel { visualStyle:root.context.style;x:60;y:12;width:root.rowsLayout ? parent.width*0.40-60 : parent.width-76;height:root.rowsLayout ? 38 : 62;text:tile.item.name;font.pixelSize:visualStyle.font25;font.weight:visualStyle.headingWeight;wrapMode:Text.WordWrap;maximumLineCount:root.rowsLayout ? 1 : 2 }
            CasaLabel { visualStyle:root.context.style;x:root.rowsLayout ? parent.width*0.42 : 16;y:root.rowsLayout ? 12 : 81;width:root.rowsLayout ? parent.width*0.28 : parent.width-32;height:44;text:tile.item.primaryText;font.pixelSize:root.rowsLayout ? visualStyle.font28 : visualStyle.font37;font.family:visualStyle.numbersFamily }
            CasaLabel { visualStyle:root.context.style;x:root.rowsLayout ? 60 : 16;y:root.rowsLayout ? parent.height-40 : parent.height-85;width:root.rowsLayout ? parent.width*0.36-60 : parent.width-32;height:32;text:tile.item.availability+(tile.item.availabilityPrevious ? " · salvata" : "");color:tile.item.previous ? visualStyle.semantic.warningOnCard : visualStyle.textSecondary;font.pixelSize:visualStyle.font21 }
            CasaLabel { visualStyle:root.context.style;x:root.rowsLayout ? parent.width*0.42 : 16;y:parent.height-48;width:root.rowsLayout ? parent.width*0.56-16 : parent.width-32;height:42;text:tile.item.previous ? "Dato precedente"+(tile.item.secondaryText ? " · "+tile.item.secondaryText : "") : tile.item.secondaryText || "Ultimo stato riportato";color:visualStyle.textSecondary;font.pixelSize:visualStyle.font20;wrapMode:Text.WordWrap;maximumLineCount:2 }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("details.open",tile.item.id,{}) }
        }
    }
    CasaLabel { visualStyle:root.context.style;anchors.centerIn:parent;width:parent.width;horizontalAlignment:Text.AlignHCenter;visible:root.devices.count===0;text:"Scegli i dispositivi in Impostazioni → Casa" }
}
