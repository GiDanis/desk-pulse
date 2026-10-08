pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.5
import "Format.js" as Format
Panel {
    required property SportHubContext context
    ctx:context
    pageMode:true
    fillRows:true
    title:"Sport"
    subtitle:context.description
    rows:{ context.dataRevision; return Format.list(context.rows).map(row=>({id:row.id,title:row.title,detail:row.detail,icon:({sport:"football",f1:"race-car",motogp:"motorcycle"})[row.id],actionId:"details.open",targetId:row.id})) }
    rowAction:"details.open"
}
