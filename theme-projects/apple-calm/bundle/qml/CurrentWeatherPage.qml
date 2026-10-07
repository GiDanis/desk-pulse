pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format

PageCanvas {
    id: root
    readonly property var weather: ctx ? ctx.weather : null
    title: "Meteo"
    subtitle: weather ? weather.location : "Dati non disponibili"
    source: weather ? weather.source : null
    WeatherCard { x:0; y:94; width:root.width*0.39; height:312; style:root.style; weather:root.weather }
    Grid {
        x:root.width*0.39+16; y:94; columns:2; spacing:12
        Repeater {
            model: [{title:"Vento", value:root.weather ? Format.number(root.weather.windSpeed) : "—", detail:root.weather ? root.weather.windDirectionText : "", symbol:"wind"}, {title:"Raffiche", value:root.weather ? Format.number(root.weather.gusts) : "—", detail:"", symbol:"wind"}, {title:"Umidità", value:root.weather ? Format.number(root.weather.humidity) : "—", detail:"", symbol:"drop"}, {title:"Pioggia", value:root.weather ? Format.number(root.weather.precipitation) : "—", detail:"", symbol:"rain"}]
            delegate: Metric { required property var modelData; width:(root.width*0.61-28)/2; height:150; style:root.style; title:modelData.title; value:modelData.value; detail:modelData.detail; symbol:modelData.symbol; valueSize:30 }
        }
    }
}
