pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format

PageCanvas {
    id: root
    title: "Previsioni"
    subtitle: ctx && ctx.weather ? ctx.weather.location : "Dati non disponibili"
    source: ctx && ctx.weather ? ctx.weather.source : null
    readonly property var forecast: { if (!ctx) return []; ctx.dataRevision; return ctx.weather ? Format.list(ctx.weather.forecast).slice(0,3) : [] }
    Row {
        y:root.bodyTop; spacing:16
        Repeater {
            model:root.forecast
            delegate: Card {
                id: forecastCard
                required property var modelData
                width:(root.width-32)/3; height:root.bodyHeight; style:root.style
                Label { x:20; y:14; width:parent.width-40; height:40; themeStyle:root.style; size:26; font.weight:Font.DemiBold; text:Format.forecastDay(forecastCard.modelData.date,root.ctx.clock.epoch,forecastCard.modelData.dayText); maximumLineCount:1 }
                OutlineIcon { x:20; y:71; symbol:Format.weather(forecastCard.modelData.code); opticalSize:56; tint:root.style.semantic.accentTextOnCard }
                Label { x:90; y:64; width:parent.width-110; height:70; themeStyle:root.style; size:39; font.weight:Font.DemiBold; text:Format.number(forecastCard.modelData.high); maximumLineCount:1 }
                Label { x:20; y:141; width:parent.width-40; height:32; themeStyle:root.style; secondary:true; size:22; text:"Min " + Format.number(forecastCard.modelData.low); maximumLineCount:1 }
                Label { x:20; y:parent.height*0.51; width:parent.width-40; height:76; themeStyle:root.style; size:22; text:forecastCard.modelData.description; maximumLineCount:2 }
                Label { x:20; y:parent.height-48; width:parent.width-40; height:35; themeStyle:root.style; secondary:true; size:20; text:"Pioggia " + Format.number(forecastCard.modelData.rainProbability); maximumLineCount:1 }
            }
        }
    }
    Label { y:root.bodyTop; width:parent.width; height:root.bodyHeight; themeStyle:root.style; size:26; secondary:true; text:"Previsioni non disponibili"; visible:root.forecast.length===0; horizontalAlignment:Text.AlignHCenter }
}
