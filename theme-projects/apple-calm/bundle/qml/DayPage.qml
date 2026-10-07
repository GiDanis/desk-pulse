pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format

PageCanvas {
    id: root
    title: "Oggi"
    subtitle: ctx ? ctx.clock.dateText : ""
    source: ctx && ctx.weather ? ctx.weather.source : null
    readonly property var forecast: { if (!ctx) return []; ctx.dataRevision; return ctx.weather ? Format.list(ctx.weather.forecast).slice(0,3) : [] }
    readonly property bool hasNext: ctx && ctx.nextEvent && !!ctx.nextEvent.id && !!ctx.nextEvent.title
    Row {
        x:0; y:94; spacing:16
        Repeater {
            model:root.forecast
            delegate: Card {
                id: forecastCard
                required property var modelData
                width:(root.width-32)/3; height:root.hasNext ? 185 : 312; style:root.style
                Label { x:20; y:14; width:parent.width-40; height:36; themeStyle:root.style; size:24; font.weight:Font.DemiBold; text:forecastCard.modelData.dayText; maximumLineCount:1 }
                OutlineIcon { x:20; y:61; opticalSize:48; symbol:Format.weather(forecastCard.modelData.code); tint:root.style.semantic.accentTextOnCard }
                Label { x:84; y:60; width:parent.width-104; height:53; themeStyle:root.style; size:30; text:Format.number(forecastCard.modelData.high); maximumLineCount:1 }
                Label { x:20; y:122; width:parent.width-40; height:35; themeStyle:root.style; secondary:true; size:20; text:"Min " + Format.number(forecastCard.modelData.low); maximumLineCount:1 }
                Label { x:20; y:174; width:parent.width-40; height:91; themeStyle:root.style; secondary:true; size:22; text:forecastCard.modelData.description; visible:!root.hasNext; maximumLineCount:3 }
            }
        }
    }
    Card {
        x:0; y:296; width:parent.width; height:110; style:root.style; visible:root.hasNext
        OutlineIcon { x:22; anchors.verticalCenter:parent.verticalCenter; symbol:"calendar"; opticalSize:40; tint:root.style.semantic.accentTextOnCard }
        Label { x:86; y:16; width:parent.width-320; height:40; themeStyle:root.style; size:26; font.weight:Font.DemiBold; text:root.hasNext ? root.ctx.nextEvent.title : ""; maximumLineCount:1 }
        Label { x:86; y:60; width:parent.width-320; height:32; themeStyle:root.style; size:20; secondary:true; text:"Prossimo evento" }
        Label { x:parent.width-230; y:20; width:210; height:75; themeStyle:root.style; size:22; text:root.hasNext ? root.ctx.nextEvent.whenText || Format.stamp(root.ctx.nextEvent.startsAt) : ""; horizontalAlignment:Text.AlignRight }
    }
    Label { x:0; y:100; width:parent.width; height:260; themeStyle:root.style; secondary:true; size:26; text:"Previsioni non disponibili"; visible:root.forecast.length===0; horizontalAlignment:Text.AlignHCenter }
}
