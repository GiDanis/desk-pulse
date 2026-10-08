pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.2
import "Format.js" as Format

Panel {
    required property CasaContext context
    ctx:context; pageMode:true
    title:"Dispositivi"
    subtitle:context.selection.anchorId === "casa.tabs" ? "Scegli la vista" : "Casa · Smart Life"
    source:context.source
    rows: { context.dataRevision; return Format.casaDevices(context.casa.devices) }
    emptyText:"Nessun dispositivo disponibile"
    footer:context.feedback || context.casa.modeText
    rowAction:"details.open"
}
