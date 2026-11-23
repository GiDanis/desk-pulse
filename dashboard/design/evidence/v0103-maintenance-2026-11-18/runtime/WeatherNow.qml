import QtQuick
import "themes"
import "components"
import "components/IconIds.js" as IconIds

Item {
    id: visualRoot
    property StyleFacade style: Theme
    required property var dashboard
    width: 872; height: 455
    AppText { style: visualRoot.style; y: 0; text: dashboard.weatherData.location || "ANGRI · SALERNO"; color: visualRoot.style.textSecondary; font.pixelSize: visualRoot.style.font28 }
    AppText { style: visualRoot.style; y: 36; text: dashboard.weatherData.temperature || "—"; color: visualRoot.style.textPrimary; role: "numbers"; font.pixelSize: visualRoot.style.font139; font.weight: visualRoot.style.clockWeight }
    AppText { style: visualRoot.style; x: 360; y: 89; width: 500; text: dashboard.weatherData.description || "Meteo non disponibile"; color: visualRoot.style.textPrimary; font.pixelSize: visualRoot.style.font40; elide: Text.ElideRight }
    Rectangle { y: 231; width: visualRoot.width; height: 2; color: visualRoot.style.divider }
    AppIcon { style: visualRoot.style; x: visualRoot.width-58; y: 15; iconId: IconIds.weather(dashboard.weatherData.code); opticalSize: 38 }
    InfoCard { style: visualRoot.style; x: 0; y: 257; width: (visualRoot.width-16)/2; height: visualRoot.height-257; night: dashboard.night; heading: "PIOGGIA"; value: dashboard.weatherData.rain_probability || "—"; detail: "Probabilità attuale"; compact: true }
    InfoCard { style: visualRoot.style; x: (visualRoot.width+16)/2; y: 257; width: (visualRoot.width-16)/2; height: visualRoot.height-257; night: dashboard.night; heading: "PERCEPITA"; value: dashboard.weatherData.feels_like || "—"; detail: dashboard.weatherStatus(); compact: true }
}
