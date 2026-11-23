pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Panel {
    id: root
    required property PageContext context
    ctx: context
    pageMode: true
    title: context.team ? context.team.identity.name || "La tua squadra" : "La tua squadra"
    subtitle: context.team ? context.team.recordText : "Scegli una squadra nelle impostazioni"
    source: context.team ? context.team.source : null
    rows: { context.dataRevision; return context.team ? Format.matches(context.team.fixtures) : [] }
    emptyText: "Dati della squadra non disponibili"
    rowAction: "details.open"
}
