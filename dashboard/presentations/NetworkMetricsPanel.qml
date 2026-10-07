import QtQuick
Item {
    id:root
    required property var context
    property bool rowsLayout:false
    readonly property var view:context.metrics
    readonly property string route:context.contentId.split(".")[1]
    readonly property var tabs:route==="router" ? ["state","history"] : route==="wifi" ? ["radios","stations","detail"] : ["ports","hosts","history"]
    readonly property var tabLabels:route==="router" ? ["Stato","Storico"] : route==="wifi" ? ["Radio","Stazioni","Dettaglio"] : ["Porte","Host / Dati","Storico"]
    readonly property int pageSize:rowsLayout ? 6 : 5
    readonly property int start:Math.floor(Math.max(0,context.selection.index)/pageSize)*pageSize
    Rectangle { anchors.fill:parent;color:root.context.style.backgroundOverlay }
    CasaLabel { visualStyle:root.context.style;x:44;y:24;width:704;font.pixelSize:visualStyle.font37;font.weight:visualStyle.headingWeight;text:root.view.title+(root.view.busy ? " · lettura" : "") }
    Rectangle { x:770;y:27;width:146;height:38;radius:6;color:root.context.style.surface
        CasaLabel { visualStyle:root.context.style;anchors.centerIn:parent;font.pixelSize:visualStyle.font18;text:"AGGIORNA" }
        MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive && !root.view.busy;onClicked:root.context.requestAction("network.metrics.refresh",root.context.contentId,{}) }
    }
    CasaLabel { visualStyle:root.context.style;x:44;y:77;width:872;font.pixelSize:visualStyle.font18;color:visualStyle.textSecondary;text:root.view.sourceText }
    Repeater {
        model:root.tabs
        delegate:Rectangle {
            required property string modelData
            required property int index
            x:44+index*230;y:108;width:214;height:40;radius:6
            color:root.context.selection.tabId===modelData ? root.context.style.surfaceFocused : root.context.style.surface
            border.color:root.context.selection.anchorId==="metrics.tabs" && root.context.selection.tabId===modelData ? root.context.style.accent : root.context.style.border;border.width:root.context.style.borderWidth
            CasaLabel { visualStyle:root.context.style;anchors.centerIn:parent;font.pixelSize:visualStyle.font20;text:root.tabLabels[parent.index] }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("network.metrics.section",parent.modelData,{}) }
        }
    }
    CasaLabel { visualStyle:root.context.style;x:44;y:155;width:872;font.pixelSize:visualStyle.font18;color:visualStyle.textSecondary;text:root.view.selectedLabel+" · "+root.view.summary;visible:root.view.section!=="history" }
    Repeater {
        model:root.view.section==="history" ? 0 : Math.max(0,Math.min(root.pageSize,root.view.rows.count-root.start))
        delegate:Rectangle {
            required property int index
            readonly property var row:root.view.rows.get(root.start+index)
            x:44;y:183+index*(root.rowsLayout ? 58 : 69);width:872;height:root.rowsLayout ? 53 : 63;radius:root.context.style.radiusRow
            color:root.context.selection.index===root.start+index && root.context.selection.anchorId!=="metrics.tabs" ? root.context.style.surfaceFocused : root.context.style.surface
            border.color:root.context.selection.index===root.start+index && root.context.selection.anchorId!=="metrics.tabs" ? root.context.style.accent : root.context.style.border;border.width:root.context.style.borderWidth
            CasaLabel { visualStyle:root.context.style;x:14;y:7;width:490;font.pixelSize:visualStyle.font22;text:parent.row ? parent.row.title : "" }
            CasaLabel { visualStyle:root.context.style;x:516;y:7;width:340;horizontalAlignment:Text.AlignRight;font.pixelSize:visualStyle.font22;text:parent.row ? parent.row.value : "";color:parent.row && parent.row.previous ? visualStyle.semantic.warningOnOverlay : visualStyle.textPrimary }
            CasaLabel { visualStyle:root.context.style;x:14;y:34;width:840;font.pixelSize:visualStyle.font18;color:visualStyle.textSecondary;text:parent.row ? parent.row.detail+(parent.row.previous ? " · PRECEDENTE" : "") : "" }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive && !!parent.row && !!parent.row.targetId;onClicked:root.context.requestAction(parent.row.id==="metrics.refresh" ? "network.metrics.refresh" : "details.open",parent.row.id==="metrics.refresh" ? root.context.contentId : parent.row.id,{}) }
        }
    }
    NetworkHistoryChart { x:44;y:164;width:872;height:365;chart:root.view.chart;visualStyle:root.context.style;visible:root.view.section==="history" && root.view.hasChart }
    CasaLabel { visualStyle:root.context.style;x:44;y:245;width:872;font.pixelSize:visualStyle.font25;visible:root.view.section==="history" && !root.view.hasChart;text:"Storico non disponibile per questa selezione" }
    CasaLabel { visualStyle:root.context.style;x:44;y:545;width:872;font.pixelSize:visualStyle.font18;color:visualStyle.textSecondary;text:"Metriche router · nessuna modifica · traffico WAN, porta e stazione distinti" }
    CasaLabel { visualStyle:root.context.style;x:44;y:576;width:872;font.pixelSize:visualStyle.font20;color:visualStyle.textSecondary;text:root.view.section==="history" ? "4/6 SCHEDE · 2/8 FINESTRA 1h/24h · 5 METRICA · 7 INDIETRO" : "4/6 SCHEDE · 2/8 SELEZIONA · 5 APRI · 7 INDIETRO" }
}
