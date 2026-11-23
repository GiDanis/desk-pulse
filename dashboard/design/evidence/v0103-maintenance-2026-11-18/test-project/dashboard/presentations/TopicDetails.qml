pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.7
Item {
    id:root
    required property SummaryContext context
    readonly property bool ready:true
    readonly property bool contentReady:true
    readonly property int selected:context.selection.index
    Text {x:24;y:16;width:parent.width-48;height:52;text:root.context.familyId==="account" ? "Utilizzo e reset" : "Condizioni e giornata";color:root.context.style.textPrimary;font.family:root.context.style.uiFamily;font.pixelSize:32*root.context.style.textScale}
    ListView {
        id:list;x:24;y:88;width:parent.width-48;height:parent.height-y-16;clip:true;spacing:12;model:root.context.rows;boundsBehavior:Flickable.StopAtBounds
        function reveal() {if (root.selected<count) positionViewAtIndex(root.selected,ListView.Contain)}
        Component.onCompleted:Qt.callLater(reveal)
        Connections {target:root;function onSelectedChanged() {Qt.callLater(list.reveal)}}
        delegate:Rectangle {
            required property int index
            required property var item
            width:list.width;height:142*root.context.style.textScale;radius:root.context.style.radiusCard
            color:index===root.selected ? root.context.style.surfaceFocused : root.context.style.surface
            border.width:index===root.selected ? root.context.style.focusWidth : root.context.style.borderWidth
            border.color:index===root.selected ? root.context.style.semantic.focusIndicator : root.context.style.border
            Text {x:20;y:10;width:parent.width*0.54;height:64;text:parent.item.title;font.pixelSize:28*root.context.style.textScale;font.family:root.context.style.uiFamily;color:root.context.style.textPrimary;wrapMode:Text.Wrap;maximumLineCount:2;elide:Text.ElideRight}
            Text {x:parent.width*0.58;y:10;width:parent.width-x-20;height:64;text:parent.item.value;font.pixelSize:30*root.context.style.textScale;font.family:root.context.style.numbersFamily;color:root.context.style.textPrimary;wrapMode:Text.Wrap;maximumLineCount:2;elide:Text.ElideRight}
            Text {x:20;y:parent.height-56;width:parent.width-40;height:44;text:parent.item.detail;font.pixelSize:23*root.context.style.textScale;font.family:root.context.style.uiFamily;color:root.context.style.textSecondary;wrapMode:Text.Wrap;maximumLineCount:2;elide:Text.ElideRight}
        }
    }
}
