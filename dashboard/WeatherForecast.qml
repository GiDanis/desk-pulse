import QtQuick

Item {
    required property var dashboard
    width: 872; height: 455
    Text { y: 3; text: "PROSSIMI TRE GIORNI"; color: dashboard.ink; font.pixelSize: 40 }
    Repeater {
        model: dashboard.weatherData.forecast || []
        delegate: Rectangle {
            required property var modelData
            required property int index
            x: 0; y: 69 + index * 105; width: 872; height: 91
            radius: 10; color: dashboard.panel; border.color: dashboard.edge
            Text { x: 22; y: 12; text: modelData.day; color: dashboard.accent; font.pixelSize: 24; font.bold: true }
            Text { x: 22; y: 48; width: 370; text: modelData.description; color: dashboard.ink; font.pixelSize: 25; elide: Text.ElideRight }
            Text { x: 515; y: 18; text: modelData.high + " / " + modelData.low; color: dashboard.ink; font.pixelSize: 32 }
            Text { x: 712; y: 55; text: "PIOGGIA " + modelData.rain; color: dashboard.muted; font.pixelSize: 20 }
        }
    }
    Text { visible: !(dashboard.weatherData.forecast && dashboard.weatherData.forecast.length); y: 120; text: "Previsioni non disponibili"; color: dashboard.muted; font.pixelSize: 31 }
    Text { y: 404; text: dashboard.weatherStatus() + "  ·  OPEN-METEO"; color: dashboard.muted; font.pixelSize: 22 }
}
