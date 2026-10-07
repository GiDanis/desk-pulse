pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Panel {
    id: root
    required property TeamContext context
    ctx: context
    title: context.team ? context.team.identity.name || "Squadra" : "Squadra"
    tabs: context.tabs
    source: context.team ? context.team.source : null
    rows: { context.dataRevision; return Format.teamRows(context) }
    footer: context.serieAOnly ? "Calendario Serie A" : "Calendario completo"
    rowAction: "details.open"
}
