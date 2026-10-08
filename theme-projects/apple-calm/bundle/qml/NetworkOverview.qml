pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.3
import "Format.js" as Format
Item {
    id:root
    required property NetworkContext context
    readonly property bool ready:true
    readonly property bool contentReady:true
    readonly property bool toolsMode:context.overviewSection==="tools"
    readonly property int selectedIndex:toolsMode ? context.tools.indexOf(context.selection.selectedId) : context.deviceRows.indexOf(context.selection.selectedId)
    NetworkHeader { context:root.context;width:parent.width;height:55 }
    Row {
        y:60;spacing:8
        Repeater {
            model:[{id:"tools",label:"Metriche"},{id:"summary",label:"Dispositivi"}]
            delegate:Rectangle {
                required property var modelData
                width:(root.width-8)/2;height:38;radius:12
                color:root.context.overviewSection===modelData.id ? root.context.style.surfaceFocused : root.context.style.surface
                border.width:root.context.selection.anchorId==="network.tabs" && root.context.overviewSection===modelData.id ? 2 : 1
                border.color:root.context.selection.anchorId==="network.tabs" && root.context.overviewSection===modelData.id ? root.context.style.accent : root.context.style.border
                Label { anchors.fill:parent;themeStyle:root.context.style;size:26;text:parent.modelData.label;horizontalAlignment:Text.AlignHCenter }
                MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("network.metrics.section",parent.modelData.id,{}) }
            }
        }
    }
    ListView {
        id:feed
        objectName:"networkDashboardRows"
        y:108;width:parent.width;height:parent.height-y;clip:true;spacing:8;boundsBehavior:Flickable.StopAtBounds
        model:root.toolsMode ? root.context.tools : root.context.deviceRows
        function revealSelection() { if (root.selectedIndex>=0 && root.selectedIndex<count) positionViewAtIndex(root.selectedIndex,ListView.Contain) }
        Component.onCompleted:Qt.callLater(revealSelection)
        onModelChanged:Qt.callLater(revealSelection)
        Connections { target:root;function onSelectedIndexChanged() { Qt.callLater(feed.revealSelection) } }
        delegate:Rectangle {
            required property var item
            required property int index
            readonly property bool metric:root.toolsMode
            readonly property bool primary:metric && index===0
            width:feed.width-(feed.contentHeight>feed.height ? 10 : 0)
            height:(primary ? 194 : 118)*root.context.style.textScale-8;radius:root.context.style.radiusRow
            color:root.selectedIndex===index && root.context.selection.anchorId!=="network.tabs" ? root.context.style.surfaceFocused : root.context.style.surface
            border.width:root.selectedIndex===index && root.context.selection.anchorId!=="network.tabs" ? 3 : 1
            border.color:root.selectedIndex===index && root.context.selection.anchorId!=="network.tabs" ? root.context.style.semantic.focusIndicator : root.context.style.border
            OutlineIcon { x:14;y:14;opticalSize:32;symbol:parent.metric ? Format.settingIcon(parent.item.id) : "network";tint:root.context.style.semantic.accentTextOnCard }
            Label { x:60;y:8;width:parent.width-78;height:44;themeStyle:root.context.style;size:34;text:parent.metric ? parent.item.title : parent.item.name;maximumLineCount:1 }
            Label { x:60;y:parent.primary ? 57 : 56;width:parent.width-78;height:parent.primary ? 50 : 44;themeStyle:root.context.style;size:parent.primary ? 32 : 26;text:parent.metric ? parent.primary ? parent.item.value : parent.item.detail : parent.item.primaryAddress+" · "+parent.item.statusText;maximumLineCount:1;color:parent.item.previous ? root.context.style.semantic.warningOnCard : root.context.style.textSecondary }
            Label { visible:parent.primary;x:60;y:110;width:parent.width-78;height:parent.height-y-10;themeStyle:root.context.style;size:24;text:parent.metric ? parent.item.detail : "";maximumLineCount:2;color:parent.item.previous ? root.context.style.semantic.warningOnCard : root.context.style.textSecondary }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("details.open",parent.metric ? parent.item.targetId : parent.item.id,{}) }
        }
    }
    Label { x:0;y:120;width:parent.width;themeStyle:context.style;size:28;visible:feed.count===0;text:"Nessun dispositivo disponibile" }
    Rectangle { anchors.right:parent.right;y:feed.y+feed.visibleArea.yPosition*feed.height;width:4;height:Math.max(18,feed.visibleArea.heightRatio*feed.height);radius:2;color:root.context.style.accent;opacity:0.65;visible:feed.contentHeight>feed.height }
}
