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
    Rectangle { x: 0; y: 239; width: 872; height: 2; color: visualRoot.style.divider }
    InfoCard { style: visualRoot.style;
        x: 0; y: 263; width: dashboard.hasEvent ? 520 : 872; height: 157
        night: dashboard.night
        heading: "METEO · ANGRI"
        value: dashboard.weatherData.temperature || "Meteo non disponibile"
        detail: dashboard.weatherData.temperature ? (dashboard.weatherData.description || "") + "  ·  " + dashboard.weatherStatus() : dashboard.weatherStatus()
        compact: dashboard.hasEvent || !dashboard.weatherData.temperature
    }
    InfoCard { style: visualRoot.style;
        visible: dashboard.hasEvent
        x: 538; y: 263; width: 334; height: 157
        night: dashboard.night
        heading: "PROSSIMO EVENTO"; value: dashboard.nextEvent.title || ""
        detail: dashboard.nextEvent.when || dashboard.eventWhen(dashboard.nextEvent)
        compact: true
    }
}
