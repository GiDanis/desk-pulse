import QtQuick
import SmartPC.ThemeApi 2.0

Item {
    id: root
    required property PageContext context
    readonly property bool ready: clock.text.length > 0 && weather.text.length > 0
    readonly property string error: ""
    readonly property bool contentReady: ready
    readonly property var mandatoryRegions: [{role: "clock", x: clock.x, y: clock.y, width: clock.width, height: clock.height}, {role: "weather", x: weather.x, y: weather.y, width: weather.width, height: weather.height}]
    function settleMotion() { pulse.stop(); marker.opacity = 1 }
    Rectangle { anchors.fill: parent; color: root.context.style.background }
    Rectangle { x: 0; y: 0; width: 5; height: parent.height; color: root.context.style.accent }
    Text { id: date; x: 28; y: 18; width: parent.width - 56; text: root.context.clock.dateText; color: root.context.style.textSecondary; font.family: root.context.style.uiFamily; font.pixelSize: 24; elide: Text.ElideRight }
    Text { id: clock; x: 25; y: 70; width: parent.width - 50; text: root.context.clock.timeText; color: root.context.style.textPrimary; font.family: root.context.style.numbersFamily; font.pixelSize: Math.min(140, parent.height * 0.31); font.weight: Font.Light }
    Rectangle { id: marker; x: 30; y: 235; width: 50; height: 4; color: root.context.style.accent }
    Text { id: weather; x: 30; y: 265; width: root.context.nextEvent ? parent.width * 0.53 : parent.width - 60; text: root.context.weather ? root.context.weather.temperature.displayText + " · " + root.context.weather.description : "Meteo non disponibile"; color: root.context.style.textPrimary; font.family: root.context.style.uiFamily; font.pixelSize: 28; maximumLineCount: 2; wrapMode: Text.Wrap; elide: Text.ElideRight }
    Text { x: 30; y: 345; width: weather.width; text: root.context.weather ? root.context.weather.source.status : "unavailable"; color: root.context.style.textSecondary; font.pixelSize: 20 }
    Column { visible: root.context.nextEvent !== null; x: parent.width * 0.60; y: 265; width: parent.width * 0.36; spacing: 12
        Text { width: parent.width; text: "PROSSIMO EVENTO"; color: root.context.style.textSecondary; font.pixelSize: 18 }
        Text { width: parent.width; text: root.context.nextEvent ? root.context.nextEvent.title : ""; color: root.context.style.textPrimary; font.pixelSize: 26; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
        Text { width: parent.width; text: root.context.nextEvent ? root.context.nextEvent.whenText : ""; color: root.context.style.textSecondary; font.pixelSize: 20 }
    }
    SequentialAnimation { id: pulse; running: root.context.lifecycle.active && root.context.motionPolicy.mode === "normal"; loops: Animation.Infinite
        NumberAnimation { target: marker; property: "opacity"; from: 1; to: 0.45; duration: 1500 }
        NumberAnimation { target: marker; property: "opacity"; from: 0.45; to: 1; duration: 1500 }
    }
    Connections { target: root.context.motionPolicy; function onModeChanged() { if (root.context.motionPolicy.mode !== "normal") root.settleMotion() } }
    Connections { target: root.context.lifecycle; function onActiveChanged() { if (!root.context.lifecycle.active) root.settleMotion() } }
    Component.onDestruction: settleMotion()
}
