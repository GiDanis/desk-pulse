import QtQuick
import "themes"
import "components"

Item {
    id: visualRoot
    property StyleFacade style: Theme
    required property var dashboard
    width: 872; height: 455
    AppText { style: visualRoot.style; x: -8; y: 0; text: dashboard.timeText(); color: visualRoot.style.textPrimary; role: "display"; font.pixelSize: visualRoot.style.font152; font.weight: visualRoot.style.clockWeight }
    AppText { style: visualRoot.style; x: 4; y: 182; text: dashboard.dateText(); color: visualRoot.style.textSecondary; font.pixelSize: visualRoot.style.font31 }
    Rectangle { x: 0; y: 239; width: visualRoot.width; height: 2; color: visualRoot.style.divider }
    InfoCard { style: visualRoot.style;
        x: 0; y: 263; width: dashboard.hasEvent ? (visualRoot.width-16)*0.6 : visualRoot.width; height: visualRoot.height-263
        night: dashboard.night
        heading: "METEO · ANGRI"
        value: dashboard.weatherData.temperature || "Meteo non disponibile"
        detail: dashboard.weatherData.temperature ? (dashboard.weatherData.description || "") + "  ·  " + dashboard.weatherStatus() : dashboard.weatherStatus()
        compact: dashboard.hasEvent || !dashboard.weatherData.temperature
    }
    InfoCard { style: visualRoot.style;
        visible: dashboard.hasEvent
        x: (visualRoot.width-16)*0.6+16; y: 263; width: (visualRoot.width-16)*0.4; height: visualRoot.height-263
        night: dashboard.night
        heading: "PROSSIMO EVENTO"; value: dashboard.nextEvent.title || ""
        detail: dashboard.nextEvent.when || dashboard.eventWhen(dashboard.nextEvent)
        compact: true
    }
}
