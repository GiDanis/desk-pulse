import QtQuick
import SmartPC.ThemeApi 2.1
Item {
    id:root
    required property CasaContext context
    readonly property bool ready:true
    readonly property bool contentReady:true
    readonly property var device:context.selectedDevice
    Rectangle { anchors.fill:parent;color:root.context.style.backgroundOverlay }
    CasaLabel { visualStyle:root.context.style;x:44;y:28;width:872;font.pixelSize:visualStyle.font37;font.weight:visualStyle.headingWeight;text:root.device ? root.device.name : "Dispositivo non disponibile" }
    CasaLabel { visualStyle:root.context.style;x:44;y:85;width:872;font.pixelSize:visualStyle.font25;color:root.device && root.device.previous ? visualStyle.semantic.warningOnOverlay : visualStyle.textSecondary;text:root.device ? root.device.availability+(root.device.availabilityPrevious ? " · ultima disponibilità salvata" : "") : "" }
    CasaHeader { context:root.context;x:44;y:126;width:872;height:54 }
    Repeater {
        model:root.device ? Math.min(4,root.device.metrics.count-Math.floor(root.context.selection.index/4)*4) : 0
        delegate:Rectangle {
            required property int index
            readonly property var metric:root.device.metrics.get(Math.floor(Math.max(0,root.context.selection.index)/4)*4+index)
            x:44;y:200+index*76;width:872;height:66;radius:root.context.style.radiusRow;color:root.context.style.surface
            CasaLabel { visualStyle:root.context.style;x:16;y:8;width:400;font.pixelSize:visualStyle.font24;text:parent.metric ? parent.metric.label : "" }
            CasaLabel { visualStyle:root.context.style;x:16;y:38;width:600;font.pixelSize:visualStyle.font18;color:visualStyle.textSecondary;text:parent.metric ? (parent.metric.previous ? "Dato precedente · " : "Ultimo stato riportato · ")+headerStamp.stamp(parent.metric.checkedAt) : "" }
            CasaLabel { visualStyle:root.context.style;x:430;y:12;width:425;horizontalAlignment:Text.AlignRight;font.pixelSize:visualStyle.font26;text:parent.metric ? parent.metric.displayText : "" }
        }
    }
    CasaHeader { id:headerStamp;context:root.context;visible:false }
    CasaLabel { visualStyle:root.context.style;x:44;y:210;width:872;visible:!root.device || root.device.metrics.count===0;text:"Stato non disponibile · scegli il dispositivo tra i preferiti e aggiorna Casa";wrapMode:Text.WordWrap }
    CasaLabel { visualStyle:root.context.style;x:44;y:545;width:872;font.pixelSize:visualStyle.font19;color:visualStyle.textSecondary;text:"Consultazione · 2/8 SCORRI · 7 INDIETRO · 1 HOME" }
}
