pragma ComponentBehavior: Bound
import QtQuick
Item {
    id:root
    property var context:null
    property var rows:[]
    property bool metrics:false
    property string actionId:""
    readonly property var style:context ? context.style : null
    readonly property int selectedIndex:context ? rows.findIndex(row=>row.id===context.selection.selectedId) : -1
    function revealSelection() {
        // Coalesced deferred callbacks may outlive a destroyed GridView.
        if (grid && grid.currentIndex >= 0 && grid.currentIndex < grid.count)
            grid.positionViewAtIndex(grid.currentIndex,GridView.Contain)
    }
    GridView {
        id:grid
        objectName:"dashboardCards"
        x:0;y:0;width:parent.width+12;height:parent.height;clip:true;boundsBehavior:Flickable.StopAtBounds
        model:root.rows;currentIndex:root.selectedIndex
        cellWidth:width/2
        cellHeight:Math.max(158*(root.style ? root.style.textScale : 1),(height+12)/3)
        onCurrentIndexChanged:Qt.callLater(root.revealSelection)
        onCountChanged:Qt.callLater(root.revealSelection)
        delegate:Rectangle {
            id:card
            required property var modelData
            required property int index
            readonly property bool selected:index===root.selectedIndex
            width:grid.cellWidth-12;height:grid.cellHeight-12
            radius:root.style ? root.style.radiusCard : 18
            color:root.style ? selected ? root.style.surfaceFocused : root.style.surface : "#FFFFFF"
            border.width:selected ? 3 : 1
            border.color:root.style ? selected ? root.style.semantic.focusIndicator : root.style.border : "#CDD2DA"
            OutlineIcon {x:18;y:18;visible:!root.metrics;symbol:card.modelData.icon || "settings";opticalSize:32;tint:root.style ? root.style.semantic.accentTextOnCard : "#0066CC"}
            Label {x:root.metrics ? 18 : 62;y:8;width:parent.width-x-18;height:38;themeStyle:root.style;size:root.metrics ? 25 : 30;font.weight:Font.Medium;text:card.modelData.title;maximumLineCount:1}
            Label {x:18;y:46;width:parent.width-36;height:60;themeStyle:root.style;size:root.context && root.context.selection.tabId==="RISORSE" ? 32 : 26;font.weight:Font.Medium;text:card.modelData.value || "";visible:root.metrics;maximumLineCount:2}
            Label {x:18;y:root.metrics ? parent.height-45 : 63;width:parent.width-36;height:root.metrics ? 40 : parent.height-72;themeStyle:root.style;size:root.metrics ? 19 : 23;secondary:true;text:card.modelData.detail || "";maximumLineCount:root.metrics ? 2 : 3}
            MouseArea {anchors.fill:parent;enabled:!!root.context && card.modelData.enabled!==false
                onClicked:root.context.requestAction(root.metrics ? "selection.select" : card.modelData.actionId || root.actionId,card.modelData.targetId || card.modelData.id,{})}
        }
    }
    Rectangle {anchors.right:parent.right;width:4;y:grid.visibleArea.yPosition*root.height;height:Math.max(18,grid.visibleArea.heightRatio*root.height);radius:2;color:root.style ? root.style.accent : "#0066CC";visible:grid.contentHeight>grid.height;opacity:0.65}
}
