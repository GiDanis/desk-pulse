import QtQuick
import "../themes"
import "../components"
import ".."
Item {
    id: root
    required property var context
    readonly property var dashboard: context.controller
    property StyleFacade style: context.style
    AppText { style: root.style; role: "display"; x: 0; y: 0; width: 872; horizontalAlignment: Text.AlignHCenter; text: dashboard.timeText(); font.pixelSize: root.style.font139; color: root.style.textPrimary }
    AppText { style: root.style; x: 0; y: 160; width: 872; horizontalAlignment: Text.AlignHCenter; text: dashboard.dateText(); font.pixelSize: root.style.font31; color: root.style.textSecondary }
    InfoCard { style: root.style; x: 0; y: 239; width: dashboard.hasEvent ? 520 : 872; height: 157; heading: "METEO · ANGRI"; value: dashboard.weatherData.temperature || "Meteo non disponibile"; detail: (dashboard.weatherData.description || "") + " · " + dashboard.weatherStatus(); compact: dashboard.hasEvent || !dashboard.weatherData.temperature }
    InfoCard { style: root.style; visible: dashboard.hasEvent; x: 538; y: 239; width: 334; height: 157; heading: "PROSSIMO EVENTO"; value: dashboard.nextEvent.title || ""; detail: dashboard.nextEvent.when || dashboard.eventWhen(dashboard.nextEvent); compact: true }
}
