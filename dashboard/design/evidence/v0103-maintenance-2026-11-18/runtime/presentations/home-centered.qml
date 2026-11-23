import QtQuick
import "../themes"
import "../components"
import ".."
Item {
    id: root
    required property var context
    readonly property var dashboard: context.controller
    property StyleFacade style: context.style
    AppText { style: root.style; role: "display"; x: 0; y: 0; width: root.width; horizontalAlignment: Text.AlignHCenter; text: dashboard.timeText(); font.pixelSize: root.style.font139; color: root.style.textPrimary }
    AppText { style: root.style; x: 0; y: 160; width: root.width; horizontalAlignment: Text.AlignHCenter; text: dashboard.dateText(); font.pixelSize: root.style.font31; color: root.style.textSecondary }
    InfoCard { style: root.style; x: 0; y: 239; width: dashboard.hasEvent ? (root.width-16)*0.6 : root.width; height: root.height-239; heading: "METEO · ANGRI"; value: dashboard.weatherData.temperature || "Meteo non disponibile"; detail: (dashboard.weatherData.description || "") + " · " + dashboard.weatherStatus(); compact: dashboard.hasEvent || !dashboard.weatherData.temperature }
    InfoCard { style: root.style; visible: dashboard.hasEvent; x: (root.width-16)*0.6+16; y: 239; width: (root.width-16)*0.4; height: root.height-239; heading: "PROSSIMO EVENTO"; value: dashboard.nextEvent.title || ""; detail: dashboard.nextEvent.when || dashboard.eventWhen(dashboard.nextEvent); compact: true }
}
