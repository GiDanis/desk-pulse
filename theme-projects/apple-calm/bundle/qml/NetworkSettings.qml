pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.3
import "Format.js" as Format
Panel {
    required property NetworkContext context
    ctx:context
    title:"Rete locale / iliadbox"
    subtitle:context.description
    rows:{ context.dataRevision; return Format.list(context.rows).map(row=>({id:row.id,title:row.title,detail:row.detail,value:row.value.displayText,icon:Format.settingIcon(row.id),enabled:row.enabled,actionId:row.actionId,targetId:row.targetId})) }
    footer:context.feedback || context.network.modeText
}
