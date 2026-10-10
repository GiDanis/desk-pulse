pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format

PageCanvas {
    id: root
    readonly property var weather: ctx ? ctx.weather : null
    title: "Meteo"
    subtitle: weather ? weather.location : "Dati non disponibili"
    source: weather ? weather.source : null
    WeatherCard { x:0; y:root.bodyTop; width:root.width*400/912; height:root.bodyHeight; style:root.style; weather:root.weather }
    Grid {
        x:root.width*416/912; y:root.bodyTop; columns:2; spacing:16
        Repeater {
            model: [{title:"Vento",size:34,value:root.weather ? Format.number(root.weather.windSpeed) : "—",detail:root.weather ? root.weather.windDirectionText : "",symbol:"wind"}, {title:"Umidità",size:52,value:root.weather ? Format.number(root.weather.humidity) : "—",detail:"",symbol:"humidity"}, {title:"Raffiche",size:34,value:root.weather ? Format.number(root.weather.gusts) : "—",detail:"",symbol:"wind"}, {title:"Precipitazioni",size:38,value:root.weather ? Format.number(root.weather.precipitation) : "—",detail:"Intervallo del modello",symbol:"rain"}]
            delegate: Metric { required property var modelData; width:root.width*240/912; height:(root.bodyHeight-16)/2; style:root.style; title:modelData.title; value:modelData.value; detail:modelData.detail; symbol:modelData.symbol; valueSize:modelData.size }
        }
    }
}
