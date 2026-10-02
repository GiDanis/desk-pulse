import QtQuick
import "themes"
import "components"
import "components/IconIds.js" as IconIds

Item {
    id: visualRoot
    property StyleFacade style: Theme
    required property var dashboard
    width: 872; height: 455
    AppText { style: visualRoot.style; y: 3; text: "PROSSIMI TRE GIORNI"; color: visualRoot.style.textPrimary; font.pixelSize: visualRoot.style.font40 }
    Repeater {
        model: dashboard.weatherData.forecast || []
        delegate: Rectangle {
            required property var modelData
            required property int index
            x: 0; y: 69 + index * 105; width: 872; height: 91
            radius: visualRoot.style.radiusPanel; color: visualRoot.style.surface; border.color: visualRoot.style.border
            AppText { style: visualRoot.style; x: 22; y: 12; text: modelData.day; color: visualRoot.style.accent; font.pixelSize: visualRoot.style.font24; font.weight: (true ) ? visualRoot.style.headingWeight : visualRoot.style.bodyWeight}
            AppText { style: visualRoot.style; x: 22; y: 48; width: 370; text: modelData.description; color: visualRoot.style.textPrimary; font.pixelSize: visualRoot.style.font25; elide: Text.ElideRight }
            AppIcon { style: visualRoot.style; x: 440; y: 22; opticalSize: 30; iconId: IconIds.weather(modelData.code) }
            AppText { role: "numbers"; style: visualRoot.style; x: 515; y: 18; text: modelData.high + " / " + modelData.low; color: visualRoot.style.textPrimary; font.pixelSize: visualRoot.style.font32 }
            AppText { style: visualRoot.style; x: 712; y: 55; text: "PIOGGIA " + modelData.rain; color: visualRoot.style.textSecondary; font.pixelSize: visualRoot.style.font20 }
        }
    }
    AppText { style: visualRoot.style; visible: !(dashboard.weatherData.forecast && dashboard.weatherData.forecast.length); y: 120; text: "Previsioni non disponibili"; color: visualRoot.style.textSecondary; font.pixelSize: visualRoot.style.font31 }
    AppText { style: visualRoot.style; y: 404; text: dashboard.weatherStatus() + "  ·  OPEN-METEO"; color: visualRoot.style.textSecondary; font.pixelSize: visualRoot.style.font22 }
}
