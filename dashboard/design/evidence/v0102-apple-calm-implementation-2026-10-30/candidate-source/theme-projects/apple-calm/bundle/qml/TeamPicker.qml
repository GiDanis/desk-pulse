pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Panel {
    id: root
    required property TeamPickerContext context
    ctx: context
    title: "Scegli squadra"
    subtitle: "Scegli la squadra preferita"
    rows: { context.dataRevision; return Format.list(context.teams).map(x => Format.row(x.id,x.name,x.id === context.savedTeamId ? "Squadra preferita" : "", "", "football")) }
    rowAction: "details.open"
}
