pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.2
import "Format.js" as Format

Panel {
    required property CasaContext context
    ctx:context
    title:context.selectedDevice ? context.selectedDevice.name : "Dispositivo"
    subtitle:context.selectedDevice ? context.selectedDevice.availability + (context.selectedDevice.availabilityPrevious ? " · salvata" : "") : "Stato non disponibile"
    source:context.source
    rows:context.selectedDevice ? Format.list(context.selectedDevice.metrics).map(x => Format.row(x.code,x.label,(x.previous ? "Dato precedente" : "Ultimo stato riportato") + (x.checkedAt ? " · " + Format.stamp(x.checkedAt) : ""),x.displayText,Format.metricIcon(x.code))) : []
    footer:"Consultazione"
    emptyText:"Stato non disponibile dalla fonte"
}
