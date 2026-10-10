pragma ComponentBehavior: Bound
import QtQuick
Item {
    id: root
    required property var context
    readonly property bool devicesView: context.contentId === "casa.devices"
    function stamp(value) { return value ? Qt.formatDateTime(new Date(value*1000),"dd/MM hh:mm") : "nessuna lettura" }
    Row {
        spacing:12
        Repeater {
            model:["Preferiti","Dispositivi"]
            delegate:Rectangle {
                required property string modelData
                required property int index
                width:(root.width-12)/2;height:34;radius:root.context.style.radiusButton
                color:(index===1)===root.devicesView ? root.context.style.surfaceFocused : root.context.style.surface
                border.width:root.context.selection.anchorId==="casa.tabs" && (index===1)===root.devicesView ? root.context.style.focusWidth : root.context.style.borderWidth
                border.color:root.context.selection.anchorId==="casa.tabs" && (index===1)===root.devicesView ? root.context.style.semantic.focusIndicator : root.context.style.border
                CasaLabel { visualStyle:root.context.style;anchors.fill:parent;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;font.pixelSize:visualStyle.font24;text:parent.modelData }
                MouseArea { anchors.fill:parent;enabled:root.context.lifecycle.interactive;onClicked:if ((parent.index===1)!==root.devicesView) root.context.requestAction("navigation.view.step","",{direction:parent.index===1 ? 1 : -1}) }
            }
        }
    }
    CasaLabel { visualStyle:root.context.style;y:43;width:parent.width;font.pixelSize:visualStyle.font20;
        color:root.context.source.status==="active" ? visualStyle.textSecondary : visualStyle.semantic.warningOnCanvas;
        text:(root.context.source.status==="active" ? "Cloud letto " : root.context.source.status==="updating" ? "Aggiornamento · ultima lettura " : "Dati salvati · cloud letto ")+root.stamp(root.context.source.updatedAt)+" · "+(root.context.source.error || root.context.casa.modeText) }
}
