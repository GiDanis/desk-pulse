pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.2
import "Format.js" as Format

Panel {
    required property CasaContext context
    ctx:context; pageMode:true
    title:"Preferiti"
    subtitle:context.selection.anchorId === "casa.tabs" ? "Scegli la vista" : "Casa · Smart Life"
    source:context.source
    rows:Format.casaDevices(context.casa.favourites)
    emptyText:"Scegli i dispositivi in Impostazioni → Casa"
    footer:context.feedback || context.casa.modeText
    rowAction:"details.open"
}
