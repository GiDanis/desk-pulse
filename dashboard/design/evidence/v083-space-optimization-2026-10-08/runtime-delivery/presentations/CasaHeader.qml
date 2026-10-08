import QtQuick
Item {
    id: root
    required property var context
    Rectangle { anchors.fill:parent; anchors.margins:-5; color:"transparent"; radius:6
        visible:root.context.selection.anchorId === "casa.tabs"; border.width:2; border.color:root.context.style.accent }
    function stamp(value) {
        if (!value) return "Nessuna lettura"
        const d=new Date(value*1000)
        function two(n) { return (n<10 ? "0" : "")+n }
        return two(d.getDate())+"/"+two(d.getMonth()+1)+" "+two(d.getHours())+":"+two(d.getMinutes())
    }
    CasaLabel { visualStyle: root.context.style; width:parent.width; font.pixelSize:visualStyle.font20;
        text:(root.context.source.status === "active" ? "Cloud letto " : root.context.source.status === "updating" ? "Aggiornamento in corso · lettura precedente " : "Dati salvati · cloud letto ")+root.stamp(root.context.source.updatedAt) }
    CasaLabel { visualStyle:root.context.style; y:27; width:parent.width; font.pixelSize:visualStyle.font18;
        color:root.context.source.status === "offline" || root.context.source.status === "error" ? visualStyle.semantic.warningOnCanvas : visualStyle.textSecondary;
        text:(root.context.selection.anchorId === "casa.tabs" ? "4/6 CAMBIA VISTA · 8 SELEZIONA · " : "")+(root.context.source.error || root.context.casa.modeText) }
}
