import QtQuick
import SmartPC.ThemeApi 2.3
Item {
    id:root
    required property NetworkContext context
    readonly property bool ready:true
    readonly property bool contentReady:true
    readonly property var device:context.selectedDevice
    readonly property int start:Math.floor(Math.max(0,context.selection.index)/3)*3
    Rectangle { anchors.fill:parent;color:root.context.style.backgroundOverlay }
    CasaLabel { visualStyle:root.context.style;x:44;y:25;width:872;font.pixelSize:visualStyle.font37;font.weight:visualStyle.headingWeight;text:root.device ? root.device.name : "Dispositivo non disponibile" }
    CasaLabel { visualStyle:root.context.style;x:44;y:79;width:872;font.pixelSize:visualStyle.font24;color:root.device && root.device.previous ? visualStyle.semantic.warningOnOverlay : visualStyle.textSecondary;text:root.device ? root.device.statusText : "" }
    Repeater {
        model:["identity","addresses","link","observations"]
        delegate:Rectangle {
            required property string modelData
            required property int index
            x:44+index*222;y:117;width:206;height:40;radius:6;color:root.context.selection.tabId===modelData ? root.context.style.surfaceFocused : root.context.style.surface
            CasaLabel { visualStyle:root.context.style;anchors.centerIn:parent;font.pixelSize:visualStyle.font24;text:["Identità","Indirizzi","Collegamento","Riscontri"][parent.index] }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("navigation.tab.select",parent.modelData,{}) }
        }
    }
    Repeater {
        model:Math.max(0,Math.min(3,root.context.detailRows.count-root.start))
        delegate:Rectangle {
            required property int index
            readonly property var row:root.context.detailRows.get(root.start+index)
            x:44;y:177+index*105;width:872;height:97;radius:root.context.style.radiusRow;color:root.context.style.surface
            CasaLabel { visualStyle:root.context.style;x:16;y:7;width:282;font.pixelSize:visualStyle.font28;text:parent.row ? parent.row.title : "" }
            CasaLabel { visualStyle:root.context.style;x:310;y:7;width:546;horizontalAlignment:Text.AlignRight;font.pixelSize:visualStyle.font28;text:parent.row ? parent.row.value : "" }
            CasaLabel { visualStyle:root.context.style;x:16;y:parent.height-36;width:840;font.pixelSize:visualStyle.font24;color:visualStyle.textSecondary;text:parent.row ? parent.row.detail : "" }
        }
    }
    CasaLabel { visualStyle:root.context.style;x:44;y:208;width:872;visible:root.context.detailRows.count===0;text:"Dato non disponibile per questa identità";font.pixelSize:visualStyle.font32 }
    CasaLabel { visualStyle:root.context.style;x:44;y:root.height-72;width:872;font.pixelSize:visualStyle.font24;color:visualStyle.textSecondary;text:"Presenza fisica non verificata · lettura iliadbox · nessun comando al dispositivo" }
    CasaLabel { visualStyle:root.context.style;x:44;y:root.height-36;width:872;font.pixelSize:visualStyle.font24;color:visualStyle.textSecondary;text:"4/6 SCHEDE · 2/8 SCORRI · 5 "+(root.device && root.device.favourite ? "RIMUOVI PREFERITO" : root.context.network.favourites.count>=4 ? "PREFERITI 4/4" : "AGGIUNGI PREFERITO")+" · 7 INDIETRO" }
}
