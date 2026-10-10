pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format

Card {
    id: root
    property var weather: null
    readonly property real valueTop:Math.max(116,height*0.38)
    OutlineIcon { objectName:"weatherSymbol"; x:24; y:24; opticalSize:64; symbol:root.weather ? Format.weather(root.weather.code) : "unknown"; tint:root.style ? root.style.semantic.accentTextOnCard : "#0066CC" }
    Label { x:104; y:20; width:parent.width-128; height:44; themeStyle:root.style; size:26; font.weight:Font.DemiBold; text:root.weather ? root.weather.location : "Meteo"; maximumLineCount:1 }
    Label { x:104; y:65; width:parent.width-128; height:32; themeStyle:root.style; size:20; secondary:true; text:root.weather ? root.weather.description || "Meteo non disponibile" : "Meteo non disponibile"; maximumLineCount:1 }
    Label { x:24; y:root.valueTop; width:parent.width-48; height:95; themeStyle:root.style; size:69; font.family:root.style ? root.style.numbersFamily : "Sans Serif"; font.weight:Font.DemiBold; text:root.weather ? Format.number(root.weather.temperature) : "—"; maximumLineCount:1 }
    Label { x:24; y:root.valueTop+95; width:parent.width-48; height:35; themeStyle:root.style; size:20; secondary:true; text:"Percepita " + (root.weather ? Format.number(root.weather.feelsLike) : "—"); maximumLineCount:1 }
}
