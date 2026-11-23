pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format
PageCanvas {
    id:root
    title:"Previsioni"
    subtitle:ctx && ctx.weather ? ctx.weather.location : "Dati non disponibili"
    source:ctx && ctx.weather ? ctx.weather.source : null
    readonly property var forecast:{if(!ctx)return [];ctx.dataRevision;return ctx.weather ? Format.list(ctx.weather.forecast).slice(0,3) : []}
    Row {
        y:root.bodyTop;spacing:16
        Repeater {
            model:root.forecast
            delegate:Card {
                id:forecastCard
                required property var modelData
                readonly property bool compact:height<300
                width:(root.width-32)/3;height:root.bodyHeight;style:root.style
                Label { x:20;y:10;width:parent.width-40;height:38;themeStyle:root.style;size:26;font.weight:Font.DemiBold;text:Format.forecastDay(forecastCard.modelData.date,root.ctx.clock.epoch,forecastCard.modelData.dayText);maximumLineCount:1 }
                OutlineIcon { x:20;y:72;symbol:Format.weather(forecastCard.modelData.code);opticalSize:48;tint:root.style.semantic.accentTextOnCard;visible:!forecastCard.compact }
                Label { x:20;y:forecastCard.compact ? 53 : 139;width:parent.width-40;height:54;themeStyle:root.style;size:34;font.family:root.style.numbersFamily;text:Format.number(forecastCard.modelData.high)+" / "+Format.number(forecastCard.modelData.low);maximumLineCount:1 }
                Label { x:20;y:forecastCard.compact ? 109 : 195;width:parent.width-40;height:32;themeStyle:root.style;size:24;secondary:true;text:"Max · Min";maximumLineCount:1 }
                Label { x:20;y:245;width:parent.width-40;height:76;themeStyle:root.style;size:24;text:forecastCard.modelData.description;maximumLineCount:2;visible:height+245<parent.height-56 }
                Label { x:20;y:parent.height-44;width:parent.width-40;height:34;themeStyle:root.style;size:22;secondary:true;text:"Prob. max "+Format.number(forecastCard.modelData.rainProbability);maximumLineCount:1 }
            }
        }
    }
    Label { y:root.bodyTop;width:parent.width;height:root.bodyHeight;themeStyle:root.style;size:26;secondary:true;text:"Previsioni non disponibili";visible:root.forecast.length===0;horizontalAlignment:Text.AlignHCenter }
}
