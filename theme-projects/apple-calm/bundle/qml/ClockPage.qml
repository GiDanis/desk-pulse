pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format

Item {
    id: root
    property var ctx: null
    readonly property var style: ctx ? ctx.style : null
    readonly property var next: ctx ? ctx.nextEvent : null
    readonly property bool hasNext: !!next && !!next.id && !!next.title
    readonly property bool ready: !!ctx && clockLabel.text.length > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var mandatoryRegions: [{role:"title",x:0,y:20,width:width*0.57,height:185}, {role:"body",x:width*0.59,y:20,width:width*0.41,height:height-65}]
    function settleMotion() { }
    Rectangle { anchors.fill:parent; color:root.style ? root.style.background : "#F3F4F6" }
    Label { x:0; y:18; width:parent.width*0.56; height:40; themeStyle:root.style; size:24; secondary:true; text:root.ctx ? root.ctx.clock.dateText : ""; maximumLineCount:1 }
    Label { id:clockLabel; x:-5; y:68; width:parent.width*0.59; height:200; themeStyle:root.style; size:152; font.family:root.style ? root.style.displayFamily : "Sans Serif"; font.weight:Font.DemiBold; text:root.ctx ? root.ctx.clock.timeText : "—"; maximumLineCount:1; fontSizeMode:Text.Fit; minimumPixelSize:100 }
    Card {
        x:0; y:310; width:parent.width*0.56; height:170; style:root.style; visible:root.hasNext
        OutlineIcon { x:20; y:20; symbol:"calendar"; opticalSize:28; tint:root.style ? root.style.semantic.accentTextOnCard : "#0066CC" }
        Label { x:62; y:12; width:parent.width-82; height:40; themeStyle:root.style; size:20; secondary:true; text:"Prossimo evento"; maximumLineCount:1 }
        Label { x:20; y:54; width:parent.width-40; height:54; themeStyle:root.style; size:26; font.weight:Font.DemiBold; text:root.next ? root.next.title : ""; maximumLineCount:1 }
        Label { x:20; y:107; width:parent.width-40; height:31; themeStyle:root.style; size:20; secondary:true; text:root.next ? root.next.whenText || Format.stamp(root.next.startsAt) : ""; maximumLineCount:1 }
    }
    WeatherCard { x:parent.width*0.59; y:20; width:parent.width*0.41; height:parent.height-82; style:root.style; weather:root.ctx ? root.ctx.weather : null }
    Label { x:parent.width*0.59+24; y:parent.height-175; width:parent.width*0.41-48; height:98; themeStyle:root.style; size:18; secondary:true; text:root.ctx && root.ctx.weather ? Format.source(root.ctx.weather.source) : ""; maximumLineCount:3 }
}
