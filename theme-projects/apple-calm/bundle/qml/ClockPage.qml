pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format

Item {
    id: root
    property var ctx: null
    readonly property var style: ctx ? ctx.style : null
    readonly property var next: ctx ? ctx.nextEvent : null
    readonly property var weather: ctx ? ctx.weather : null
    readonly property bool hasWeather: !!weather && !!weather.source && weather.source.hasData
    readonly property bool eventFits: height >= 390
    readonly property bool showNext: eventFits && !!next && !!next.id && !!next.title
    readonly property int eventHeight: eventFits ? 104 : 0
    readonly property real heroHeight: Math.min(224, Math.max(1, height-eventHeight-16))
    readonly property real heroTop: Math.max(0, Math.floor((height-eventHeight-heroHeight)/2))
    readonly property real split: Math.floor(width*0.57)
    readonly property bool ready: !!ctx && clockLabel.text.length > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var mandatoryRegions: [{role:"title",x:24,y:heroTop,width:split-48,height:heroHeight},
        {role:"body",x:split+16,y:heroTop,width:width-split-40,height:heroHeight}]
    function settleMotion() { if (eventFade.running) eventFade.complete() }
    Rectangle { anchors.fill:parent; color:root.style ? root.style.background : "#F3F4F6" }
    Item {
        x:24; y:root.heroTop; width:root.split-48; height:root.heroHeight
        Label {
            id:dateLabel; objectName:"homeDate"
            width:parent.width; height:44
            themeStyle:root.style; size:28; secondary:true
            text:root.ctx ? Format.shortDate(root.ctx.clock) : ""; maximumLineCount:1
        }
        Label {
            id:clockLabel; objectName:"dominantClock"
            y:dateLabel.height; width:parent.width; height:Math.max(1,parent.height-y-16)
            themeStyle:root.style; size:Math.min(148, Math.floor(height*0.86))
            font.family:root.style ? root.style.displayFamily : "Sans Serif"
            font.weight:Font.DemiBold; font.kerning:false; font.features: ({tnum: 1})
            text:root.ctx ? root.ctx.clock.timeText : "—"; maximumLineCount:1
            fontSizeMode:Text.Fit; minimumPixelSize:36
        }
    }
    Item {
        x:root.split+16; y:root.heroTop; width:parent.width-x-24; height:root.heroHeight
        readonly property real valueTop: Math.min(dateLabel.height+7, Math.round(height*0.23))
        readonly property real valueHeight: Math.max(1, Math.min(106, height-valueTop-72))
        OutlineIcon {
            objectName:"weatherSymbol"; x:0; y:parent.valueTop+(parent.valueHeight-height)/2
            opticalSize:52; symbol:root.hasWeather ? Format.weather(root.weather.code) : "unknown"
            tint:root.style ? root.style.semantic.accentTextOnCanvas : "#0066CC"
        }
        Label {
            objectName:"weatherTemperature"
            x:68; y:parent.valueTop; width:parent.width-x; height:parent.valueHeight
            themeStyle:root.style; size:76; font.family:root.style ? root.style.numbersFamily : "Sans Serif"
            font.weight:Font.DemiBold; font.features: ({tnum: 1})
            text:root.hasWeather ? Format.number(root.weather.temperature) : "—"
            maximumLineCount:1; fontSizeMode:Text.Fit; minimumPixelSize:28
        }
        Label {
            objectName:"deskWeatherCondition"
            x:68; y:parent.valueTop+parent.valueHeight; width:parent.width-x; height:Math.max(1,parent.height-y)
            themeStyle:root.style; size:25; verticalAlignment:Text.AlignTop
            text:root.hasWeather ? root.weather.description : Format.deskWeatherStatus(root.weather ? root.weather.source : null)
            maximumLineCount:2
        }
        Label {
            objectName:"deskWeatherStatus"
            x:68; y:0; width:parent.width-x; height:44
            themeStyle:root.style; size:21; secondary:true; maximumLineCount:1
            text:root.hasWeather ? Format.deskWeatherStatus(root.weather.source) : ""
            visible:text.length>0
        }
    }
    Item {
        objectName:"deskNextEvent"
        x:24; y:parent.height-root.eventHeight; width:parent.width-48; height:Math.max(0,root.eventHeight-12)
        visible:root.showNext
        opacity:root.showNext ? 1 : 0
        Behavior on opacity {
            enabled:!!root.ctx && !!root.ctx.motionPolicy && !root.ctx.motionPolicy.suspended
                    && !root.ctx.motionPolicy.urgent && root.ctx.motionPolicy.mode !== "off"
            NumberAnimation { id:eventFade; duration:root.ctx && root.ctx.motionPolicy && root.ctx.motionPolicy.mode === "reduced" ? 65 : 110; easing.type:Easing.OutCubic }
        }
        Rectangle { width:parent.width; height:1; color:root.style ? root.style.divider : "#CDD2DA" }
        OutlineIcon { y:34; symbol:"calendar"; opticalSize:28; tint:root.style ? root.style.semantic.accentTextOnCanvas : "#0066CC" }
        Label { x:48; y:12; width:parent.width-x; height:32; themeStyle:root.style; size:22; secondary:true; text:root.showNext ? ["Prossimo evento",root.next.whenText || Format.stamp(root.next.startsAt)].filter(Boolean).join(" · ") : ""; maximumLineCount:1 }
        Label { x:48; y:44; width:parent.width-x; height:44; themeStyle:root.style; size:28; font.weight:Font.DemiBold; text:root.showNext ? root.next.title : ""; maximumLineCount:1 }
    }
}
