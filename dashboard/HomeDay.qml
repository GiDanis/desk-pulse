import QtQuick

Item {
    required property var dashboard
    width: 872; height: 455
    Text { y: 3; text: dashboard.dateText(); color: dashboard.ink; font.pixelSize: 46 }
    Text { y: 86; text: "IL TEMPO OGGI"; color: dashboard.accent; font.pixelSize: 25; font.bold: true }
    Text { y: 127; width: 860; text: dashboard.weatherData.temperature ? dashboard.weatherData.temperature + "  " + dashboard.weatherData.description : "Meteo non disponibile"; color: dashboard.ink; font.pixelSize: 69; elide: Text.ElideRight }
    Text { y: 246; text: dashboard.weatherStatus(); color: dashboard.muted; font.pixelSize: 27 }
    Text { y: 309; text: dashboard.hasEvent ? "PROSSIMO · " + dashboard.nextEvent.title + " · " + dashboard.nextEvent.when : ""; color: dashboard.accent; font.pixelSize: 30 }
    Text { y: 388; text: "6  METEO  →"; color: dashboard.muted; font.pixelSize: 26 }
}
