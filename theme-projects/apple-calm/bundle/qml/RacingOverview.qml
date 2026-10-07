pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Panel {
    id: root
    required property PageContext context
    ctx: context
    pageMode: true
    title: context.racing && context.racing.kind === "motogp" ? "MotoGP" : "Formula 1"
    subtitle: context.selection.tabId || "Calendario"
    source: context.racing ? context.racing.source : null
    rows: { context.dataRevision; if (!context.racing) return []; if (context.selection.tabId === "CLASSIFICA") return Format.standings(context.racing.standings); if (context.selection.tabId === "IN CORSO") return Format.timing(context.racing.live.rows); return Format.events(Format.list(context.racing.events).filter(x => context.selection.tabId === "RISULTATI" ? x.endsAt !== null && x.endsAt < context.clock.epoch : x.endsAt === null || x.endsAt >= context.clock.epoch)) }
    emptyText: "Nessun dato disponibile in questa vista"
    rowAction: "details.open"
}
