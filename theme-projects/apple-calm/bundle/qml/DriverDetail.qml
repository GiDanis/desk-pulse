pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Panel {
    id: root
    required property DriverContext context
    ctx: context
    title: context.driver ? context.driver.name || "Pilota" : "Pilota"
    tabs: context.tabs
    source: context.source
    rows: { context.dataRevision; return Format.driverRows(context) }
    footer: context.detailOperation.status === "pending" ? "Caricamento dettagli" : context.detailOperation.message
}
