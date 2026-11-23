import QtQuick
import SmartPC.ThemeApi 2.3
Item {
    id:root
    required property NetworkContext context
    property bool rowsLayout:false
    readonly property bool ready:true
    readonly property bool contentReady:true
    readonly property var networkInfo:context.network
    readonly property var rows:context.deviceRows
    readonly property bool toolsMode:context.overviewSection==="tools"
    readonly property real bodyTop:116
    readonly property real bodyHeight:height-bodyTop
    NetworkHeader { context:root.context;width:parent.width;height:55 }
    Row {
        y:60;spacing:12
        Repeater {
            model:[{id:"tools",label:"Metriche"},{id:"summary",label:"Dispositivi"}]
            delegate:Rectangle {
                required property var modelData
                width:(root.width-12)/2;height:38;radius:root.context.style.radiusButton
                color:root.context.overviewSection===modelData.id ? root.context.style.surfaceFocused : root.context.style.surface
                border.width:root.context.selection.anchorId==="network.tabs" && root.context.overviewSection===modelData.id ? root.context.style.focusWidth : root.context.style.borderWidth
                border.color:root.context.selection.anchorId==="network.tabs" && root.context.overviewSection===modelData.id ? root.context.style.semantic.focusIndicator : root.context.style.border
                CasaLabel { visualStyle:root.context.style;anchors.fill:parent;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;font.pixelSize:visualStyle.font24;text:parent.modelData.label }
                MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("network.metrics.section",parent.modelData.id,{}) }
            }
        }
    }
    Repeater {
        model:root.toolsMode ? root.context.tools : []
        delegate:Rectangle {
            id:metric
            required property var item
            required property int index
            readonly property bool primary:index===0
            readonly property bool selectedState:root.context.selection.selectedId===item.id && root.context.selection.anchorId!=="network.tabs"
            objectName:"networkMetricTile"+index
            x:primary ? 0 : (index-1)*(width+16)
            y:root.bodyTop+(primary ? 0 : root.bodyHeight*0.55+16)
            width:primary ? root.width : (root.width-16)/2
            height:primary ? root.bodyHeight*0.55 : root.bodyHeight*0.45-16
            radius:root.context.style.radiusCard
            color:selectedState ? root.context.style.surfaceFocused : root.context.style.surface
            border.width:selectedState ? root.context.style.focusWidth : root.context.style.borderWidth
            border.color:selectedState ? root.context.style.semantic.focusIndicator : root.context.style.border
            CasaLabel { visualStyle:root.context.style;x:20;y:12;width:parent.width-40;height:40;font.pixelSize:visualStyle.font27;font.weight:visualStyle.headingWeight;text:metric.item.title }
            CasaLabel { visualStyle:root.context.style;x:20;y:58;width:parent.width-40;height:primary ? 65 : 44;font.pixelSize:primary ? visualStyle.font34 : visualStyle.font28;font.family:visualStyle.numbersFamily;color:metric.item.previous ? visualStyle.semantic.warningOnCard : visualStyle.textPrimary;text:metric.item.value;wrapMode:Text.WordWrap;maximumLineCount:2 }
            CasaLabel { visualStyle:root.context.style;x:20;y:primary ? parent.height-95 : 106;width:parent.width-40;height:primary ? 80 : parent.height-114;font.pixelSize:visualStyle.font21;color:metric.item.previous ? visualStyle.semantic.warningOnCard : visualStyle.textSecondary;text:metric.item.detail;wrapMode:Text.WordWrap;maximumLineCount:primary ? 3 : 2 }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("details.open",metric.item.targetId,{}) }
        }
    }
    Repeater {
        model:root.toolsMode ? 0 : Math.min(4,root.rows.count)
        delegate:Rectangle {
            required property int index
            readonly property var device:root.rows.get(index)
            x:root.rowsLayout ? 0 : index%2*(width+16)
            y:root.bodyTop+(root.rowsLayout ? index*(height+10) : Math.floor(index/2)*(height+16))
            width:root.rowsLayout ? root.width : (root.width-16)/2
            height:root.rowsLayout ? (root.bodyHeight-30)/4 : (root.bodyHeight-16)/2
            radius:root.context.style.radiusCard
            color:device && device.id===root.context.selection.selectedId && root.context.selection.anchorId!=="network.tabs" ? root.context.style.surfaceFocused : root.context.style.surface
            border.width:root.context.style.borderWidth
            border.color:device && device.id===root.context.selection.selectedId && root.context.selection.anchorId!=="network.tabs" ? root.context.style.semantic.focusIndicator : root.context.style.border
            CasaLabel { visualStyle:root.context.style;x:16;y:12;width:root.rowsLayout ? parent.width*0.55-32 : parent.width-32;height:root.rowsLayout ? 38 : 65;font.pixelSize:visualStyle.font25;text:parent.device ? parent.device.name+(parent.device.favourite ? " · ★" : "") : "";wrapMode:Text.WordWrap;maximumLineCount:root.rowsLayout ? 1 : 2 }
            CasaLabel { visualStyle:root.context.style;x:root.rowsLayout ? parent.width*0.55 : 16;y:root.rowsLayout ? 12 : 87;width:root.rowsLayout ? parent.width*0.45-16 : parent.width-32;font.pixelSize:visualStyle.font21;color:parent.device && parent.device.previous ? visualStyle.semantic.warningOnCard : visualStyle.textSecondary;text:parent.device ? parent.device.statusText : "" }
            CasaLabel { visualStyle:root.context.style;x:16;y:parent.height-42;width:parent.width-32;font.pixelSize:visualStyle.font22;color:visualStyle.textSecondary;text:parent.device ? parent.device.primaryAddress : "" }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("details.open",parent.device.id,{}) }
        }
    }
    CasaLabel { visualStyle:root.context.style;anchors.centerIn:parent;width:parent.width;font.pixelSize:visualStyle.font28;visible:!root.toolsMode && root.rows.count===0;text:"Nessun dispositivo disponibile";horizontalAlignment:Text.AlignHCenter }
}
