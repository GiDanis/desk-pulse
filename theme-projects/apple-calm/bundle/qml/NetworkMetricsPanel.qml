import QtQuick
Item {
    id:root
    required property var context
    property bool rowsLayout:false
    readonly property var view:context.metrics
    readonly property string route:context.contentId.split(".")[1]
    readonly property var tabs:route==="router" ? ["state","history"] : route==="wifi" ? ["radios","stations","detail"] : ["ports","hosts","history"]
    readonly property var tabLabels:route==="router" ? ["Stato","Storico"] : route==="wifi" ? ["Radio","Stazioni","Dettaglio"] : ["Porte","Host / Dati","Storico"]
    readonly property int pageSize:3
    readonly property real metricRowHeight: Math.max(74,(height-255)/pageSize)
    readonly property int start:Math.floor(Math.max(0,context.selection.index)/pageSize)*pageSize
    Rectangle { anchors.fill:parent;color:root.context.style.backgroundOverlay }
    CasaLabel { visualStyle:root.context.style;x:24;y:24;width:parent.width-220;font.pixelSize:visualStyle.font37;font.weight:visualStyle.headingWeight;text:root.view.title+(root.view.busy ? " · lettura" : "") }
    Rectangle { x:parent.width-170;y:27;width:146;height:38;radius:6;color:root.context.style.surface
        CasaLabel { visualStyle:root.context.style;anchors.centerIn:parent;font.pixelSize:visualStyle.font22;text:"AGGIORNA" }
        MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive && !root.view.busy;onClicked:root.context.requestAction("network.metrics.refresh",root.context.contentId,{}) }
    }
    CasaLabel { visualStyle:root.context.style;x:24;y:77;width:parent.width-48;font.pixelSize:visualStyle.font22;color:visualStyle.textSecondary;text:root.view.sourceText }
    Repeater {
        model:root.tabs
        delegate:Rectangle {
            required property string modelData
            required property int index
            x:24+index*((root.width-48)/root.tabs.length);y:108;width:(root.width-48)/root.tabs.length-16;height:40;radius:6
            color:root.context.selection.tabId===modelData ? root.context.style.surfaceFocused : root.context.style.surface
            border.color:root.context.selection.anchorId==="metrics.tabs" && root.context.selection.tabId===modelData ? root.context.style.accent : root.context.style.border;border.width:root.context.style.borderWidth
            CasaLabel { visualStyle:root.context.style;anchors.centerIn:parent;font.pixelSize:visualStyle.font26;text:root.tabLabels[parent.index] }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("network.metrics.section",parent.modelData,{}) }
        }
    }
    CasaLabel { visualStyle:root.context.style;x:24;y:155;width:parent.width-48;font.pixelSize:visualStyle.font22;color:visualStyle.textSecondary;text:[root.view.selectedLabel,root.view.summary].filter(Boolean).join(" · ");visible:root.view.section!=="history" }
    ListView {
        id: metricList
        objectName: "networkMetricRows"
        x:24;y:183;width:parent.width-48;height:Math.max(0,parent.height-y-16)
        clip:true;spacing:8;boundsBehavior:Flickable.StopAtBounds
        model:root.view.section==="history" ? null : root.view.rows
        function revealSelection() { if (root.context.selection.index>=0 && root.context.selection.index<count) positionViewAtIndex(root.context.selection.index,ListView.Contain) }
        Component.onCompleted:Qt.callLater(revealSelection)
        onCountChanged:Qt.callLater(revealSelection)
        Connections { target:root.context.selection; function onIndexChanged() { Qt.callLater(metricList.revealSelection) } }
        delegate:Rectangle {
            required property var item
            required property int index
            width:metricList.width-(metricList.contentHeight>metricList.height ? 10 : 0);height:118*root.context.style.textScale-8;radius:root.context.style.radiusRow
            color:root.context.selection.index===index && root.context.selection.anchorId!=="metrics.tabs" ? root.context.style.surfaceFocused : root.context.style.surface
            border.color:root.context.selection.index===index && root.context.selection.anchorId!=="metrics.tabs" ? root.context.style.accent : root.context.style.border;border.width:root.context.style.borderWidth
            CasaLabel { visualStyle:root.context.style;x:14;y:7;width:parent.width*0.56;font.pixelSize:visualStyle.font32;text:parent.item.title }
            CasaLabel { visualStyle:root.context.style;x:parent.width*0.60;y:7;width:parent.width-x-16;horizontalAlignment:Text.AlignRight;font.pixelSize:visualStyle.font32;text:parent.item.value;color:parent.item.previous ? visualStyle.semantic.warningOnOverlay : visualStyle.textPrimary }
            CasaLabel { visualStyle:root.context.style;x:14;y:parent.height-38;width:parent.width-28;font.pixelSize:visualStyle.font22;color:visualStyle.textSecondary;text:parent.item.detail+(parent.item.previous ? " · PRECEDENTE" : "") }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive && !!parent.item.targetId;onClicked:root.context.requestAction(parent.item.id==="metrics.refresh" ? "network.metrics.refresh" : "details.open",parent.item.id==="metrics.refresh" ? root.context.contentId : parent.item.id,{}) }
        }
    }
    Rectangle { x:parent.width-28;y:metricList.y+metricList.visibleArea.yPosition*metricList.height;width:4;height:Math.max(18,metricList.visibleArea.heightRatio*metricList.height);radius:2;color:root.context.style.accent;opacity:0.65;visible:root.view.section!=="history" && metricList.contentHeight>metricList.height }
    NetworkHistoryChart { x:24;y:164;width:parent.width-48;height:Math.max(120,root.height-180);chart:root.view.chart;visualStyle:root.context.style;visible:root.view.section==="history" && root.view.hasChart }
    CasaLabel { visualStyle:root.context.style;x:24;y:245;width:parent.width-48;font.pixelSize:visualStyle.font25;visible:root.view.section==="history" && !root.view.hasChart;text:"Storico non disponibile per questa selezione" }
}
