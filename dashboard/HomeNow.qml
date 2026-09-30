import QtQuick

Item {
    required property var dashboard
    width: 872; height: 455
    Text { x: -8; y: 0; text: dashboard.timeText(); color: dashboard.ink; font.pixelSize: 152; font.weight: Font.Light }
    Text { x: 4; y: 182; text: dashboard.dateText(); color: dashboard.muted; font.pixelSize: 31 }
    Rectangle { x: 0; y: 239; width: 872; height: 2; color: "#31505b" }
    InfoCard {
        x: 0; y: 263; width: dashboard.hasEvent ? 520 : 872; height: 157
        night: dashboard.night
        heading: "METEO · ANGRI"
        value: dashboard.weatherData.temperature || "Meteo non disponibile"
        detail: dashboard.weatherData.temperature ? (dashboard.weatherData.description || "") + "  ·  " + dashboard.weatherStatus() : dashboard.weatherStatus()
        compact: dashboard.hasEvent || !dashboard.weatherData.temperature
    }
    InfoCard {
        visible: dashboard.hasEvent
        x: 538; y: 263; width: 334; height: 157
        night: dashboard.night
        heading: "PROSSIMO EVENTO"; value: dashboard.nextEvent.title || ""
        detail: (dashboard.nextEvent.type || "").toUpperCase() + " · " + (dashboard.nextEvent.when || "")
        compact: true
    }
}
