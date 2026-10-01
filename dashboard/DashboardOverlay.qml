import QtQuick

Item {
    id: overlayRoot
    required property var dashboard
    Rectangle { visible: dashboard.overlay !== ""; anchors.fill: parent; color: "#0b1219" }
    Item {
        visible: dashboard.overlay !== ""
        x: 44; y: 35; width: 872; height: 570
        Text {
            text: dashboard.overlay === "menu" ? "MENU" : dashboard.overlay === "alerts" ? "AVVISI" :
                  dashboard.overlay === "commands" ? "COMANDI" : dashboard.overlay === "settings" ? "IMPOSTAZIONI" :
                  dashboard.overlay === "modules" ? "MODULI VISIBILI" :
                  dashboard.overlay === "system" ? "ASPETTO E DISPOSITIVO" :
                  dashboard.overlay === "notifications" ? "NOTIFICHE" :
                  dashboard.overlay === "alertDetail" ? "DETTAGLIO AVVISO" : "DETTAGLI"
            color: dashboard.accent; font.pixelSize: 37; font.bold: true
        }
        Repeater {
            model: dashboard.overlay === "menu" ? dashboard.menuItems : []
            delegate: Rectangle {
                required property string modelData
                required property int index
                x: 0; y: 77 + index * 86; width: 872; height: 72
                radius: 9; color: index === dashboard.menuIndex ? "#28403f" : dashboard.panel
                border.color: index === dashboard.menuIndex ? dashboard.accent : dashboard.edge
                border.width: index === dashboard.menuIndex ? 3 : 1
                Text { x: 24; anchors.verticalCenter: parent.verticalCenter; text: modelData; color: dashboard.ink; font.pixelSize: 31 }
                Text {
                    anchors.right: parent.right; anchors.rightMargin: 24; anchors.verticalCenter: parent.verticalCenter
                    text: index < 3 ? "›" : ""
                    color: dashboard.muted; font.pixelSize: 24
                }
                MouseArea { anchors.fill: parent; onClicked: { dashboard.menuIndex = index; dashboard.selectMenu() } }
            }
        }
        Text {
            visible: dashboard.overlay === "alerts" && dashboard.alertItems.length === 0
            x: 0; y: 133; text: "Nessun avviso attivo"; color: dashboard.ink; font.pixelSize: 39
        }
        Repeater {
            model: dashboard.overlay === "alerts" ? dashboard.alertItems : []
            delegate: Rectangle {
                required property var modelData
                required property int index
                objectName: "alertRow" + index
                visible: index >= Math.floor(dashboard.alertIndex / 3) * 3 && index < Math.floor(dashboard.alertIndex / 3) * 3 + 3
                x: 0; y: 92 + (index % 3) * 117; width: 872; height: 101; radius: 9
                color: index === dashboard.alertIndex ? "#28403f" : dashboard.panel
                border.color: index === dashboard.alertIndex ? dashboard.accent : dashboard.edge
                border.width: index === dashboard.alertIndex ? 3 : 1
                Text {
                    x: 18; y: 10; width: 760
                    text: (modelData.seen ? "" : "●  ") + modelData.title
                    color: dashboard.ink; font.pixelSize: 28; font.bold: true; elide: Text.ElideRight
                }
                Text {
                    x: 18; y: 56; width: 815
                    text: modelData.detail
                    color: dashboard.muted; font.pixelSize: 21; elide: Text.ElideRight
                }
                MouseArea { anchors.fill: parent; onClicked: { dashboard.alertIndex = index; dashboard.openSelectedAlert() } }
            }
        }
        Text {
            visible: dashboard.overlay === "alerts"
            x: 0; y: 463; width: 872
            text: (dashboard.alertItems.length ? "AVVISO " + (dashboard.alertIndex + 1) + "/" + dashboard.alertItems.length + " · " : "") +
                  "Fonte meteo: " + (dashboard.events.sourceStatus || "in attesa")
            color: dashboard.muted; font.pixelSize: 20; elide: Text.ElideRight
        }
        Text { visible: dashboard.overlay === "commands"; x: 0; y: 105; width: 850; text: "1 INDIETRO  2 SU       3 AVVISI\n4 SINISTRA  5 OK       6 DESTRA\n7 HOME      8 GIÙ      9 MENU"; color: dashboard.ink; font.pixelSize: 34; lineHeight: 1.7 }
        Text {
            visible: dashboard.overlay === "alertDetail"; x: 0; y: 94; width: 850
            text: dashboard.selectedAlert.title || ""
            color: dashboard.ink; font.pixelSize: 45; font.bold: true; wrapMode: Text.WordWrap
        }
        Text {
            visible: dashboard.overlay === "alertDetail"; x: 0; y: 209; width: 850
            text: dashboard.selectedAlert.detail || ""
            color: dashboard.ink; font.pixelSize: 30; wrapMode: Text.WordWrap
        }
        Text {
            visible: dashboard.overlay === "alertDetail"; x: 0; y: 368; width: 850
            text: "Fonte: " + (dashboard.selectedAlert.sourceLabel || dashboard.selectedAlert.source || "") +
                  " · Emesso " + dashboard.eventStamp(dashboard.selectedAlert.issuedAt) +
                  "\nValido fino al " + (dashboard.selectedAlert.expiresAt ? new Date(dashboard.selectedAlert.expiresAt * 1000).toLocaleString(Qt.locale("it_IT"), "dd/MM hh:mm") : "—")
            color: dashboard.muted; font.pixelSize: 25; lineHeight: 1.5
        }
        Text {
            visible: dashboard.overlay === "detail"; x: 0; y: 130; width: 850
            text: dashboard.familyId === "meteo" ? "Fonte: Open-Meteo\n" + dashboard.weatherStatus() + "\nVento: " + (dashboard.weatherData.wind || "—") + "\nUmidità: " + (dashboard.weatherData.humidity || "—") :
                  "Oggi · " + dashboard.dateText() + "\n" + dashboard.weatherStatus()
            color: dashboard.ink; font.pixelSize: 31; lineHeight: 1.5
        }
        Text { x: 0; y: 522; text: "1  INDIETRO      7  HOME"; color: dashboard.accent; font.pixelSize: 27 }
    }

}
