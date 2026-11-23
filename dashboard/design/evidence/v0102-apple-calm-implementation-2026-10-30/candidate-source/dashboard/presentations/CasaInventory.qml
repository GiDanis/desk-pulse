pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.7
Item {
    id:root
    required property CasaContext context
    readonly property bool ready:true
    readonly property bool contentReady:true
    readonly property var devices:context.casa.devices
    readonly property int selected:Math.max(0,devices.indexOf(context.selection.selectedId))
    Text { x:24;y:16;width:parent.width-48;height:48;text:"Dispositivi Smart Life";color:root.context.style.textPrimary;font.family:root.context.style.uiFamily;font.pixelSize:32*root.context.style.textScale }
    Text { x:24;y:66;width:parent.width-48;height:34;text:"Stati riportati dal cloud · sola consultazione";color:root.context.style.textSecondary;font.family:root.context.style.uiFamily;font.pixelSize:23*root.context.style.textScale }
    ListView {
        id:list;x:24;y:112;width:parent.width-48;height:parent.height-y-16;clip:true;spacing:12;boundsBehavior:Flickable.StopAtBounds
        model:root.devices
        function reveal() { if (root.selected<count) positionViewAtIndex(root.selected,ListView.Contain) }
        Component.onCompleted:Qt.callLater(reveal)
        Connections {target:root;function onSelectedChanged() { Qt.callLater(list.reveal) }}
        onCountChanged:Qt.callLater(reveal)
        delegate:Rectangle {
            required property var item
            required property int index
            width:list.width;height:132*root.context.style.textScale;radius:root.context.style.radiusCard
            color:item.id===root.context.selection.selectedId ? root.context.style.surfaceFocused : root.context.style.surface
            border.width:item.id===root.context.selection.selectedId ? root.context.style.focusWidth : root.context.style.borderWidth
            border.color:item.id===root.context.selection.selectedId ? root.context.style.semantic.focusIndicator : root.context.style.border
            Text {x:20;y:12;width:parent.width*0.52;height:64;text:parent.item.name;color:root.context.style.textPrimary;font.family:root.context.style.uiFamily;font.pixelSize:28*root.context.style.textScale;wrapMode:Text.Wrap;maximumLineCount:2;elide:Text.ElideRight}
            Text {x:parent.width*0.55;y:12;width:parent.width-x-20;height:64;text:parent.item.primaryText;color:root.context.style.textSecondary;font.family:root.context.style.uiFamily;font.pixelSize:25*root.context.style.textScale;wrapMode:Text.Wrap;maximumLineCount:2;elide:Text.ElideRight}
            Text {x:20;y:parent.height-43;width:parent.width-40;height:33;text:parent.item.availability+(parent.item.previous ? " · dato precedente" : "");color:root.context.style.textSecondary;font.family:root.context.style.uiFamily;font.pixelSize:22*root.context.style.textScale;elide:Text.ElideRight}
            MouseArea {anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:root.context.requestAction("details.open",parent.item.id,{})}
        }
    }
    Text {x:24;y:160;width:parent.width-48;text:"Nessun dispositivo disponibile";visible:root.devices.count===0;color:root.context.style.textSecondary;font.pixelSize:30}
}
