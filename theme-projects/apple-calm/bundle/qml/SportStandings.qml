pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Panel {
    id: root
    required property SportListContext context
    ctx: context
    title: "Classifica"
    subtitle: context.selectedRoundId ? "Giornata " + context.selectedRoundId : "Calcio"
    source: context.source
    rows: { context.dataRevision; return Format.standings(context.standings) }
    rowAction: "details.open"
}
