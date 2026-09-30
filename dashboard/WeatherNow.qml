import QtQuick

Item {
    required property var dashboard
    width: 872; height: 455
    Text { y: 0; text: dashboard.weatherData.location || "ANGRI · SALERNO"; color: dashboard.muted; font.pixelSize: 28 }
    Text { y: 36; text: dashboard.weatherData.temperature || "—"; color: dashboard.ink; font.pixelSize: 139; font.weight: Font.Light }
    Text { x: 360; y: 89; width: 500; text: dashboard.weatherData.description || "Meteo non disponibile"; color: dashboard.ink; font.pixelSize: 40; elide: Text.ElideRight }
    Rectangle { y: 231; width: 872; height: 2; color: "#31505b" }
    InfoCard { x: 0; y: 257; width: 425; height: 155; night: dashboard.night; heading: "PIOGGIA"; value: dashboard.weatherData.rain_probability || "—"; detail: "Probabilità attuale"; compact: true }
    InfoCard { x: 443; y: 257; width: 429; height: 155; night: dashboard.night; heading: "PERCEPITA"; value: dashboard.weatherData.feels_like || "—"; detail: dashboard.weatherStatus(); compact: true }
}
