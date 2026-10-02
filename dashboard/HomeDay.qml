import QtQuick
import "themes"
import "components"

Item {
    id: visualRoot
    property StyleFacade style: Theme
    required property var dashboard
    width: 872; height: 455
    AppText { style: visualRoot.style; y: 3; text: dashboard.dateText(); color: visualRoot.style.textPrimary; font.pixelSize: visualRoot.style.font46 }
    AppText { style: visualRoot.style; y: 86; text: "IL TEMPO OGGI"; color: visualRoot.style.accent; font.pixelSize: visualRoot.style.font25; font.weight: (true ) ? visualRoot.style.headingWeight : visualRoot.style.bodyWeight}
    AppText { style: visualRoot.style; y: 127; width: 860; text: dashboard.weatherData.temperature ? dashboard.weatherData.temperature + "  " + dashboard.weatherData.description : "Meteo non disponibile"; color: visualRoot.style.textPrimary; font.pixelSize: visualRoot.style.font69; elide: Text.ElideRight }
    AppText { style: visualRoot.style; y: 246; text: dashboard.weatherStatus(); color: visualRoot.style.textSecondary; font.pixelSize: visualRoot.style.font27 }
    AppText { style: visualRoot.style; y: 309; text: dashboard.hasEvent ? "PROSSIMO · " + dashboard.nextEvent.title + " · " + (dashboard.nextEvent.when || dashboard.eventWhen(dashboard.nextEvent)) : ""; color: visualRoot.style.accent; font.pixelSize: visualRoot.style.font30 }
    AppText { style: visualRoot.style; y: 388; text: "6  METEO  →"; color: visualRoot.style.textSecondary; font.pixelSize: visualRoot.style.font26 }
}
