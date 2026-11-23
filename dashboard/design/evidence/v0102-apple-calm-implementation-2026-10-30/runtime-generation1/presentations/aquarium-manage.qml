pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.14
Item {
    id:root
    required property AquariumManagementContext context
    readonly property var managementData:context.management
    readonly property bool ready:true
    readonly property bool contentReady:true
    readonly property string error:""
    Rectangle {anchors.fill:parent;color:root.context.style.background}
    Text {x:28;y:78;width:900;text:root.managementData.title;color:root.context.style.textPrimary;font.family:root.context.style.uiFamily;font.pixelSize:28;font.bold:true}
    Text {x:28;y:120;width:900;text:"PESCI   ·   CATALOGO   ·   ROTAZIONE   ·   STORICO     4/6 per cambiare";color:root.context.style.textSecondary;font.pixelSize:16}
    ListView {
        id:list;x:24;y:155;width:912;height:414;clip:true;spacing:6
        model:root.managementData.rows;currentIndex:root.managementData.selectedIndex
        onCurrentIndexChanged:positionViewAtIndex(currentIndex,ListView.Contain)
        delegate:Rectangle {
            id:row
            required property var modelData
            required property int index
            width:912;height:78;radius:14
            color:index===root.managementData.selectedIndex ? root.context.style.surfaceFocused:root.context.style.background
            border.width:index===root.managementData.selectedIndex ? 2:0;border.color:root.context.style.semantic.accentTextOnCanvas
            Text {x:16;y:9;width:540;text:row.modelData.title;color:root.context.style.textPrimary;font.family:root.context.style.uiFamily;font.pixelSize:21;elide:Text.ElideRight}
            Text {x:566;y:9;width:325;text:row.modelData.value;horizontalAlignment:Text.AlignRight;color:root.context.style.semantic.accentTextOnCanvas;font.pixelSize:20;elide:Text.ElideRight}
            Text {x:16;y:42;width:880;text:row.modelData.detail;color:root.context.style.textSecondary;font.family:root.context.style.uiFamily;font.pixelSize:17;elide:Text.ElideRight}
        }
    }
    Text {x:28;y:590;width:900;wrapMode:Text.WordWrap;text:root.managementData.busy ? "Salvataggio…":root.managementData.message || "2/8 seleziona · 5 apri · 7 torna alla vasca";color:root.context.style.textSecondary;font.pixelSize:18}
}
