pragma ComponentBehavior: Bound
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
    CasaLabel { visualStyle:root.context.style;x:24;y:25;width:parent.width-48;font.pixelSize:visualStyle.font37;font.weight:visualStyle.headingWeight;text:root.device ? root.device.name : "Dispositivo non disponibile" }
    CasaLabel { visualStyle:root.context.style;x:24;y:79;width:parent.width-48;font.pixelSize:visualStyle.font24;color:root.device && root.device.previous ? visualStyle.semantic.warningOnOverlay : visualStyle.textSecondary;text:root.device ? root.device.statusText : "" }
    Repeater {
        model:["identity","addresses","link","observations"]
        delegate:Rectangle {
            required property string modelData
            required property int index
            x:24+index*((root.width-48)/4);y:117;width:(root.width-48)/4-12;height:40;radius:6;color:root.context.selection.tabId===modelData ? root.context.style.surfaceFocused : root.context.style.surface
            CasaLabel { visualStyle:root.context.style;anchors.centerIn:parent;font.pixelSize:visualStyle.font24;text:["Identità","Indirizzi","Collegamento","Riscontri"][parent.index] }
            MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("navigation.tab.select",parent.modelData,{}) }
        }
    }
    ListView {
        id:detailList
        objectName:"networkDetailRows"
        x:24;y:177;width:parent.width-48;height:Math.max(0,parent.height-y-56);clip:true;spacing:8;boundsBehavior:Flickable.StopAtBounds
        function revealSelection() { if (root.context.selection.index>=0 && root.context.selection.index<count) positionViewAtIndex(root.context.selection.index,ListView.Contain) }
        Component.onCompleted:Qt.callLater(revealSelection)
        onCountChanged:Qt.callLater(revealSelection)
        Connections { target:root.context.selection;function onIndexChanged() { Qt.callLater(detailList.revealSelection) } }
        model:root.context.detailRows
        delegate:Rectangle {
            required property int index
            required property var item
            readonly property var row:item
            width:detailList.width-(detailList.contentHeight>detailList.height ? 10 : 0);height:110*root.context.style.textScale;radius:root.context.style.radiusRow;color:root.context.style.surface
            CasaLabel { visualStyle:root.context.style;x:16;y:7;width:parent.width*0.31;font.pixelSize:visualStyle.font28;text:parent.row ? parent.row.title : "" }
            CasaLabel { visualStyle:root.context.style;x:parent.width*0.36;y:7;width:parent.width-x-16;horizontalAlignment:Text.AlignRight;font.pixelSize:visualStyle.font28;text:parent.row ? parent.row.value : "" }
            CasaLabel { visualStyle:root.context.style;x:16;y:parent.height-36;width:parent.width-32;font.pixelSize:visualStyle.font24;color:visualStyle.textSecondary;text:parent.row ? parent.row.detail : "" }
        }
    }
    CasaLabel { visualStyle:root.context.style;x:24;y:208;width:parent.width-48;visible:root.context.detailRows.count===0;text:"Dato non disponibile per questa identità";font.pixelSize:visualStyle.font32 }
    CasaLabel { visualStyle:root.context.style;x:24;y:root.height-48;width:parent.width-48;font.pixelSize:visualStyle.font24;color:visualStyle.textSecondary;text:"Presenza fisica non verificata · lettura iliadbox · nessun comando al dispositivo" }
    Rectangle { x:parent.width-28;y:detailList.y+detailList.visibleArea.yPosition*detailList.height;width:4;height:Math.max(18,detailList.visibleArea.heightRatio*detailList.height);radius:2;color:root.context.style.accent;opacity:0.65;visible:detailList.contentHeight>detailList.height }
}
