import QtQuick
Item {
    id:root
    required property var context
    function stamp(value) { return value ? Qt.formatDateTime(new Date(value*1000),"dd/MM hh:mm") : "nessuna lettura" }
    Rectangle { anchors.fill:parent; color:"transparent"; radius:6; visible:root.context.selection.anchorId==="network.tabs"; border.width:2; border.color:root.context.style.accent }
    CasaLabel { visualStyle:root.context.style; width:parent.width; font.pixelSize:visualStyle.font24; text:(root.context.source.status==="active" ? "iliadbox letta " : root.context.source.status==="updating" ? "Lettura in corso · dati salvati " : "Dati salvati · iliadbox letta ")+root.stamp(root.context.source.updatedAt) }
    CasaLabel { visualStyle:root.context.style; y:28; width:parent.width; font.pixelSize:visualStyle.font22; color:root.context.source.status==="active" ? visualStyle.textSecondary : visualStyle.semantic.warningOnCanvas; text:root.context.source.error || root.context.network.coverage }
}
