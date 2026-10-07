pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Panel {
    id: root
    required property PageContext context
    ctx: context
    pageMode: true
    title: context.sport ? context.sport.competitionName || "Calcio" : "Calcio"
    subtitle: context.selection.tabId || "Partite"
    source: context.sport ? context.sport.source : null
    rows: { context.dataRevision; return context.sport ? context.selection.tabId === "CLASSIFICA" ? Format.standings(context.sport.standings) : Format.matches(context.sport.matches, context.selection.tabId) : [] }
    emptyText: "Nessuna partita disponibile in questa vista"
    rowAction: "details.open"
}
