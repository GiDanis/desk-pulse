import QtQuick
import SmartPC.ThemeApi 2.3
Item {
    id:root
    required property NetworkContext context
    readonly property bool ready:true
    readonly property bool contentReady:true
    readonly property int selected:Math.max(0,context.deviceRows.indexOf(context.selection.selectedId))
    readonly property int start:Math.floor(selected/3)*3
    NetworkHeader { context:root.context;width:parent.width;height:55 }
    CasaLabel { visualStyle:root.context.style;y:65;width:parent.width;font.pixelSize:visualStyle.font24;text:"Filtro: "+root.context.description+" · "+root.context.deviceRows.count+" identità" }
    MouseArea { x:0;y:62;width:parent.width;height:32;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("network.filter.step","network",{direction:1}) }
    ListView {
        id:deviceList
        objectName:"networkDeviceRows"
        x:0;y:104;width:parent.width;height:parent.height-y;clip:true;spacing:8;boundsBehavior:Flickable.StopAtBounds
        function revealSelection() { if (root.selected>=0 && root.selected<count) positionViewAtIndex(root.selected,ListView.Contain) }
        Component.onCompleted:Qt.callLater(revealSelection)
        onCountChanged:Qt.callLater(revealSelection)
        Connections { target:root;function onSelectedChanged() { Qt.callLater(deviceList.revealSelection) } }
        model:root.context.deviceRows
        delegate:Rectangle {
            required property int index
            required property var item
            readonly property var device:item
            width:deviceList.width-(deviceList.contentHeight>deviceList.height ? 10 : 0);height:110*root.context.style.textScale;radius:root.context.style.radiusRow
            color:device && device.id===root.context.selection.selectedId ? root.context.style.surfaceFocused : root.context.style.surface
            border.color:device && device.id===root.context.selection.selectedId ? root.context.style.accent : root.context.style.border
            border.width:root.context.style.borderWidth
            CasaLabel { visualStyle:root.context.style;x:16;y:6;width:parent.width*0.54;font.pixelSize:visualStyle.font32;text:parent.device ? parent.device.name+(parent.device.favourite ? " · ★" : "") : "" }
            CasaLabel { visualStyle:root.context.style;x:16;y:parent.height-36;width:parent.width-32;font.pixelSize:visualStyle.font24;color:visualStyle.textSecondary;text:parent.device ? parent.device.primaryAddress+" · "+parent.device.connectionText : "" }
            CasaLabel { visualStyle:root.context.style;x:parent.width*0.58;y:11;width:parent.width-x-16;horizontalAlignment:Text.AlignRight;font.pixelSize:visualStyle.font24;color:parent.device && parent.device.previous ? visualStyle.semantic.warningOnCard : visualStyle.textSecondary;text:parent.device ? parent.device.statusText : "" }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("details.open",parent.device.id,{}) }
        }
    }
    CasaLabel { visualStyle:root.context.style;y:145;width:parent.width;visible:root.context.deviceRows.count===0;font.pixelSize:visualStyle.font32;text:"Nessuna identità in questo filtro" }
    Rectangle { anchors.right:parent.right;y:deviceList.y+deviceList.visibleArea.yPosition*deviceList.height;width:4;height:Math.max(18,deviceList.visibleArea.heightRatio*deviceList.height);radius:2;color:root.context.style.accent;opacity:0.65;visible:deviceList.contentHeight>deviceList.height }
}
