pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Panel {
    id: root
    required property RacingContext context
    ctx: context
    title: context.session ? context.session.name : "Sessione"
    tabs: context.tabs
    source: context.contentId === "racing.live" && context.racing ? context.racing.live.source : context.source
    rows: { context.dataRevision; return Format.racingRows(context) }
    footer: context.detailOperation.status === "pending" ? "Caricamento dettagli" : context.racing ? [context.racing.detailError,context.racing.partialError].filter(Boolean).join(" · ") : ""
    rowAction: "details.open"
}
