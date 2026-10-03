import QtQuick
import "../themes"

Item {
    id: root
    required property var controller
    property string mode: ""
    anchors.fill: parent
    readonly property var sample: ({version:1,id:"preview",source:"demo",sourceLabel:"Demo",category:"demo",priority:mode === "urgent" ? 3 : 2,
        bannerSize:mode === "large" ? "large" : "small",title:"Anteprima del tema · nessuna notifica reale",
        detail:"Testo, font, forme e animazioni della presentazione selezionata. 7 torna all'editor; 4/6 cambiano modalità.",issuedAt:0,expiresAt:0})
    Rectangle { anchors.fill: parent; color: Theme.backgroundOverlay }
    NotificationHost {
        controller: root.controller; service: null; preview: true; active: root.visible
        contentId: root.mode === "small" || root.mode === "large" ? "alerts.banner."+root.mode : "alerts."+(root.mode || "small")
        show: root.visible; eventSource: root.sample; previewItems: [root.sample]; exitAllowed: false
    }
    AppText { style: Theme; x: 44; y: 604; width: 872; text: "ANTEPRIMA · 7 TORNA · 4/6 MODALITÀ"; font.pixelSize: Theme.font18; color: Theme.accent }
}
