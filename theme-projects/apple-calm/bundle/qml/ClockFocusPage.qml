pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format

Item {
    id: root
    property var ctx: null
    readonly property var style: ctx ? ctx.style : null
    readonly property var weather: ctx ? ctx.weather : null
    readonly property bool hasWeather: !!weather && !!weather.source && weather.source.hasData
    readonly property string weatherStatus: Format.deskWeatherStatus(weather ? weather.source : null)
    readonly property bool hasNext: !!ctx && !!ctx.nextEvent && !!ctx.nextEvent.id && !!ctx.nextEvent.title
    readonly property bool compact: height < 340
    readonly property bool eventFits: height >= 490
    readonly property bool showNext: eventFits && hasNext
    readonly property real clockTop: compact ? 44 : 56
    readonly property real weatherHeight: compact ? 48 : 56
    readonly property real clockHeight: Math.max(1,height-clockTop-weatherHeight-12
                                                   -(eventFits ? 58 : 0))
    readonly property bool ready: !!ctx && width > 0 && clockLabel.text.length > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var mandatoryRegions: [{role:"title",x:0,y:clockTop,width:width,height:clockHeight},{role:"body",x:0,y:weatherRow.y,width:width,height:weatherHeight}]
    function settleMotion() { if (eventFade.running) eventFade.complete() }
    Rectangle { anchors.fill:parent; color:root.style ? root.style.background : "#F3F4F6" }
    Label { objectName:"homeDate"; x:0; y:0; width:parent.width; height:root.clockTop; themeStyle:root.style; size:26; secondary:true; text:root.ctx ? Format.shortDate(root.ctx.clock) : ""; maximumLineCount:1; horizontalAlignment:Text.AlignHCenter }
    Label {
        id:clockLabel; objectName:"dominantClock"; x:0; y:root.clockTop; width:parent.width; height:root.clockHeight
        themeStyle:root.style; size:Math.min(238,Math.floor(height*0.73))
        font.family:root.style ? root.style.displayFamily : "Sans Serif"
        font.kerning:false; font.features: ({tnum: 1})
        text:root.ctx ? root.ctx.clock.timeText : "—"; maximumLineCount:1
        horizontalAlignment:Text.AlignHCenter; fontSizeMode:Text.Fit; minimumPixelSize:36
    }
    Row {
        id:weatherRow
        anchors.horizontalCenter:parent.horizontalCenter; y:clockLabel.y+clockLabel.height+4; height:root.weatherHeight; spacing:12
        OutlineIcon { y:(parent.height-height)/2; symbol:root.hasWeather ? Format.weather(root.weather.code) : "unknown"; opticalSize:root.compact ? 36 : 44; tint:root.style ? root.style.semantic.accentTextOnCanvas : "#0066CC" }
        Label {
            objectName:"clockWeather"; width:Math.min(root.width-88,implicitWidth); height:parent.height
            themeStyle:root.style; size:root.compact ? 28 : 32
            text:root.hasWeather ? [Format.number(root.weather.temperature),root.weatherStatus || root.weather.description].filter(Boolean).join(" · ") : root.weatherStatus
            maximumLineCount:1
        }
    }
    Label {
        x:0; y:weatherRow.y+weatherRow.height; width:parent.width; height:58
        themeStyle:root.style; size:22; secondary:true; visible:root.showNext; opacity:root.showNext ? 1 : 0
        text:root.showNext ? [root.ctx.nextEvent.title,root.ctx.nextEvent.whenText || Format.stamp(root.ctx.nextEvent.startsAt)].filter(Boolean).join(" · ") : ""
        maximumLineCount:2; horizontalAlignment:Text.AlignHCenter
        Behavior on opacity {
            enabled:!!root.ctx && !!root.ctx.motionPolicy && !root.ctx.motionPolicy.suspended
                    && !root.ctx.motionPolicy.urgent && root.ctx.motionPolicy.mode !== "off"
            NumberAnimation { id:eventFade; duration:root.ctx && root.ctx.motionPolicy && root.ctx.motionPolicy.mode === "reduced" ? 65 : 110; easing.type:Easing.OutCubic }
        }
    }
}
