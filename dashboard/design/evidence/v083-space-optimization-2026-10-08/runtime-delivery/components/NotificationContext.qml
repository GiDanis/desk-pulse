import QtQuick
import "../themes"

QtObject {
    id: context
    readonly property int apiVersion: 1
    property string contentId: "alerts.banner.small"
    readonly property string mode: contentId.split(".").pop()
    property StyleFacade style: Theme
    readonly property NotificationStyle visualStyle: NotificationStyle { appearance: context.style.appearance; mode: context.mode }
    property bool active: false
    property bool interactive: false
    property bool exiting: false
    property bool preview: false
    property bool ready: false
    property string error: ""
    property int viewportWidth: 960
    property int viewportHeight: 640
    property var sourceEvent: ({})
    property var sourceItems: []
    property string selectedEventId: ""
    property int unreadCount: 0
    property string sourceStatus: ""
    property real scrollOffset: 0
    property real scrollMaximum: 0
    property var actionHandler: null
    property var occupiedRegions: []
    signal settleMotionRequested()
    function settleMotion() { settleMotionRequested() }
    readonly property var event: sourceEvent || ({})
    readonly property var items: sourceItems || []
    readonly property int appearanceRevision: style.appearance ? style.appearance.revision : 0
    readonly property rect safeArea: Qt.rect(visualStyle.padding, visualStyle.padding,
        Math.max(0, viewportWidth-2*visualStyle.padding), Math.max(0, viewportHeight-2*visualStyle.padding))
    readonly property var actions: preview ? [] : mode === "urgent" ? ["openDetails","dismiss","home"] :
        mode === "inbox" ? ["selectEvent","moveSelection","openDetails","back","home"] :
        mode === "detail" ? ["scrollDetails","back","home"] : ["openInbox","home"]
    readonly property var commandHints: preview ? [{key:7,label:"TORNA"},{key:4,label:"MODALITÀ"},{key:6,label:"MODALITÀ"}] :
        mode === "urgent" ? [{key:5,label:"DETTAGLI"},{key:7,label:"CHIUDI"},{key:1,label:"HOME"}] :
        mode === "inbox" ? [{key:2,label:"SU"},{key:8,label:"GIÙ"},{key:5,label:"APRI"},{key:7,label:"INDIETRO"}] :
        mode === "detail" ? [{key:2,label:"SU"},{key:8,label:"GIÙ"},{key:7,label:"INDIETRO"},{key:1,label:"HOME"}] : [{key:3,label:"AVVISI"}]
    readonly property string guideText: commandHints.map(hint => hint.key + " " + hint.label).join("     ")
    readonly property string sourceText: "Fonte: " + (event.sourceLabel || event.source || "—") +
        " · Emesso " + formatStamp(event.issuedAt)
    readonly property string validityText: "Valido fino al " + formatStamp(event.expiresAt)
    readonly property string iconId: event.category === "weather" || event.source === "weather-alert" ? "notification.weather" :
        event.category === "account" ? "notification.account" : "notification.default"
    function formatStamp(value) { return value ? new Date(value*1000).toLocaleString(Qt.locale("it_IT"),"dd/MM hh:mm") : "—" }
    function requestAction(actionId, eventId, arguments) {
        if (!active || !interactive || preview || actions.indexOf(actionId) < 0 || !actionHandler) return false
        return actionHandler(actionId, eventId || event.id || selectedEventId, arguments)
    }
}
