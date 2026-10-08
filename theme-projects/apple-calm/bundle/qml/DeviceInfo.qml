pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Panel {
    id: root
    required property InfoContext context
    ctx: context
    title: "Informazioni dispositivo"
    tabs: context.tabs
    rows: { context.dataRevision; return Format.info(context.rows) }
    footer: Format.stamp(context.updatedAt) ? "Rilevato " + Format.stamp(context.updatedAt) : "Informazioni non disponibili"
}
