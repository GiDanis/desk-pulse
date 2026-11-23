pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format

Item {
    id: root
    property var ctx: null
    readonly property var style: ctx ? ctx.style : null
    readonly property var weather: ctx ? ctx.weather : null
    readonly property bool hasNext: !!ctx && !!ctx.nextEvent && !!ctx.nextEvent.id && !!ctx.nextEvent.title
    readonly property bool ready: !!ctx && width > 0 && clockLabel.text.length > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var mandatoryRegions: [{role:"title",x:0,y:48,width:width,height:292},{role:"body",x:0,y:346,width:width,height:height-346}]
    function settleMotion() { }
    Rectangle { anchors.fill:parent; color:root.style ? root.style.background : "#F3F4F6" }
    Label { x:0; y:0; width:parent.width; height:48; themeStyle:root.style; size:26; secondary:true; text:root.ctx ? root.ctx.clock.dateText : ""; maximumLineCount:1; horizontalAlignment:Text.AlignHCenter }
    Label { id:clockLabel; objectName:"dominantClock"; x:0; y:48; width:parent.width; height:292; themeStyle:root.style; size:238; font.family:root.style ? root.style.numbersFamily : "Sans Serif"; text:root.ctx ? root.ctx.clock.timeText : "—"; maximumLineCount:1; horizontalAlignment:Text.AlignHCenter; fontSizeMode:Text.Fit; minimumPixelSize:140 }
    Row {
        anchors.horizontalCenter:parent.horizontalCenter; y:346; height:56; spacing:16
        OutlineIcon { y:8; symbol:root.weather && root.weather.source.hasData ? Format.weather(root.weather.code) : "unknown"; opticalSize:40; tint:root.style ? root.style.semantic.accentTextOnCanvas : "#0066CC" }
        Label { width:Math.min(root.width-100,implicitWidth); height:56; themeStyle:root.style; size:32; text:root.weather && root.weather.source.hasData ? [Format.number(root.weather.temperature),root.weather.description].filter(Boolean).join(" · ") : "Meteo non disponibile"; maximumLineCount:1 }
    }
    Label { x:0; y:407; width:parent.width; height:48; themeStyle:root.style; size:18; secondary:true; text:root.weather ? Format.source(root.weather.source) : "Dati meteo non disponibili"; maximumLineCount:2; horizontalAlignment:Text.AlignHCenter }
    Label { x:0; y:464; width:parent.width; height:60; themeStyle:root.style; size:22; secondary:true; visible:root.hasNext; text:root.hasNext ? root.ctx.nextEvent.title + " · " + (root.ctx.nextEvent.whenText || Format.stamp(root.ctx.nextEvent.startsAt)) : ""; maximumLineCount:2; horizontalAlignment:Text.AlignHCenter }
}
