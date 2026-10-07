pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Panel {
    id: root
    required property SettingsContext context
    ctx: context
    title: Format.settingTitle(context.sectionId)
    subtitle: context.description
    rows: { context.dataRevision; return Format.settings(context.rows) }
    footer: [context.feedback,context.operation.message,context.draft && context.draft.editing ? "Anteprima · " + context.draft.themeId : ""].filter(Boolean).join(" · ")
    rowAction: "settings.activate"
}
