import QtQuick
import "../../themes"
import "../../components"
import "../.."
Item {
    id: root
    required property var context
    readonly property StyleFacade style: context.style
    readonly property int clockInset: style.tokens["ext.summary.clockInset"]
    readonly property var weather: context.model.weather.data || ({})
    readonly property var event: context.model.nextEvent
    AppText { style: root.style; role: "display"; x: root.clockInset; width: 824; text: context.clockText; color: root.style.accent; font.pixelSize: root.style.font139; horizontalAlignment: Text.AlignHCenter }
    AppText { style: root.style; y: 165; width: 872; text: context.dateText; color: root.style.textSecondary; font.pixelSize: root.style.font31; horizontalAlignment: Text.AlignHCenter }
    InfoCard { style: root.style; y: 245; width: event.title ? 425 : 872; height: 157; heading: "METEO · ANGRI"; value: weather.temperature || "Meteo non disponibile"; detail: weather.description || "Fonte non disponibile"; compact: !!event.title }
    InfoCard { style: root.style; x: 443; y: 245; width: 429; height: 157; visible: !!event.title; heading: "PROSSIMO EVENTO"; value: event.title || ""; detail: event.when || ""; compact: true }
}
