pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format
PageCanvas {
    id:root
    title:"Previsioni"
    subtitle:ctx && ctx.weather ? ctx.weather.location : "Dati non disponibili"
    source:ctx && ctx.weather ? ctx.weather.source : null
    readonly property var forecast:{if(!ctx)return [];ctx.dataRevision;return ctx.weather ? Format.list(ctx.weather.forecast).slice(0,3) : []}
    readonly property int headerHeight:32
    readonly property int rowHeight:Math.max(1,Math.min(86,Math.floor((bodyHeight-headerHeight)/3)))
    readonly property real conditionX:Math.round(width*0.19)
    readonly property real highX:Math.round(width*0.59)
    readonly property real lowX:Math.round(width*0.73)
    readonly property real rainX:Math.round(width*0.87)
    readonly property real valueWidth:Math.floor(width*0.13)
    sourceY: forecast.length ? Math.min(height-35,bodyTop+headerHeight+rowHeight*forecast.length+12) : height-35

    Item {
        width:parent.width;y:root.bodyTop;height:root.headerHeight;visible:root.forecast.length>0
        Label { x:root.highX;width:root.valueWidth;height:parent.height;themeStyle:root.style;size:22;secondary:true;text:"Max";horizontalAlignment:Text.AlignHCenter }
        Label { x:root.lowX;width:root.valueWidth;height:parent.height;themeStyle:root.style;size:22;secondary:true;text:"Min";horizontalAlignment:Text.AlignHCenter }
        Label { x:root.rainX;width:root.valueWidth;height:parent.height;themeStyle:root.style;size:22;secondary:true;text:"Pioggia";horizontalAlignment:Text.AlignHCenter }
    }
    Column {
        y:root.bodyTop+root.headerHeight;width:parent.width
        Repeater {
            model:root.forecast
            delegate:Item {
                id:dayRow
                required property var modelData
                readonly property bool compact:height<64
                width:root.width;height:root.rowHeight
                Rectangle { width:parent.width;height:1;color:root.style.divider }
                Label { objectName:"forecastDayLabel";x:12;width:root.conditionX-24;height:parent.height;themeStyle:root.style;size:25;font.weight:Font.DemiBold;text:Format.forecastDay(dayRow.modelData.date,root.ctx.clock.epoch,dayRow.modelData.dayText);maximumLineCount:1 }
                OutlineIcon { x:root.conditionX;y:(parent.height-height)/2;symbol:Format.weather(dayRow.modelData.code);opticalSize:dayRow.compact ? 32 : 40;tint:root.style.semantic.accentTextOnCanvas }
                Label {
                    objectName:"forecastCondition";x:root.conditionX+(dayRow.compact ? 40 : 52);width:root.highX-x-12;height:parent.height
                    themeStyle:root.style;size:23;maximumLineCount:dayRow.compact ? 1 : 2
                    text:dayRow.compact ? Format.compactForecastCondition(dayRow.modelData.code,dayRow.modelData.description) : dayRow.modelData.description
                }
                Repeater {
                    model:[{name:"forecastHigh",x:root.highX,value:dayRow.modelData.high},
                           {name:"forecastLow",x:root.lowX,value:dayRow.modelData.low},
                           {name:"forecastRain",x:root.rainX,value:dayRow.modelData.rainProbability}]
                    delegate:Label {
                        required property var modelData
                        objectName:modelData.name;x:modelData.x;width:root.valueWidth;height:dayRow.height
                        themeStyle:root.style;size:dayRow.compact ? 27 : 32
                        font.family:root.style.numbersFamily;font.features: ({tnum: 1})
                        text:Format.number(modelData.value);maximumLineCount:1
                        horizontalAlignment:Text.AlignHCenter
                    }
                }
            }
        }
        Rectangle { width:parent.width;height:1;color:root.style ? root.style.divider : "#CDD2DA";visible:root.forecast.length>0 }
    }
    Label { y:root.bodyTop;width:parent.width;height:root.bodyHeight;themeStyle:root.style;size:26;secondary:true;text:"Previsioni non disponibili";visible:root.forecast.length===0;horizontalAlignment:Text.AlignHCenter }
}
