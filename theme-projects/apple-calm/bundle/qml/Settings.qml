pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Panel {
    id: root
    required property SettingsContext context
    ctx: context
    gridRows:context.contentId==="settings.index"
    compactHeading:gridRows
    title: gridRows ? "Preferenze" : Format.settingTitle(context.sectionId)
    subtitle: gridRows ? "" : context.description
    rows: { context.dataRevision; return Format.settings(context.rows) }
    footer: gridRows ? "" : [context.feedback,context.operation.message].filter((value,index,values) => value && values.indexOf(value) === index).join(" · ")
    fillRows:true
    rowAction: "settings.activate"
}
