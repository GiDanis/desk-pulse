pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Panel {
    id: root
    required property MenuContext context
    ctx: context
    title: "Menu"
    subtitle: "Scegli una funzione"
    rows: { context.dataRevision; return Format.list(context.rows).map(x => ({id:x.id,title:x.title,detail:x.detail,value:"",icon:Format.settingIcon(x.id),enabled:x.enabled,actionId:x.actionId || "menu.activate",targetId:x.targetId || x.id})) }
    rowAction: "menu.activate"
}
