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
                  dashboard.overlay === "system" ? "ASPETTO E DISPOSITIVO" : "DETTAGLI"
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
                    text: index === 1 ? "›" : ""
                    color: dashboard.muted; font.pixelSize: 24
                }
                MouseArea { anchors.fill: parent; onClicked: { dashboard.menuIndex = index; dashboard.selectMenu() } }
            }
        }
        Text { visible: dashboard.overlay === "alerts"; x: 0; y: 147; text: "Nessun avviso"; color: dashboard.ink; font.pixelSize: 44 }
        Repeater {
            model: dashboard.overlay === "settings" ? dashboard.settingsItems : []
            delegate: Rectangle {
                required property string modelData
                required property int index
                x: 0; y: 88 + index * 92; width: 872; height: 76; radius: 9
                color: index === dashboard.settingsIndex ? "#28403f" : dashboard.panel
                border.color: index === dashboard.settingsIndex ? dashboard.accent : dashboard.edge
                border.width: index === dashboard.settingsIndex ? 3 : 1
                Text { x: 24; anchors.verticalCenter: parent.verticalCenter; text: modelData; color: dashboard.ink; font.pixelSize: 31 }
                MouseArea { anchors.fill: parent; onClicked: { dashboard.settingsIndex = index; dashboard.selectSettings() } }
            }
        }
        Text {
            visible: dashboard.overlay === "modules"
            x: 0; y: 78; width: 850
            text: "Scegli quali moduli mostrare nello scorrimento orizzontale."
            color: dashboard.muted; font.pixelSize: 23
        }
        Repeater {
            model: dashboard.overlay === "modules" ? dashboard.allFamilies : []
            delegate: Rectangle {
                required property var modelData
                required property int index
                objectName: "moduleRow" + index
                x: 0; y: 125 + index * 94; width: 872; height: 78; radius: 9
                color: index === dashboard.modulesIndex ? "#28403f" : dashboard.panel
                border.color: index === dashboard.modulesIndex ? dashboard.accent : dashboard.edge
                border.width: index === dashboard.modulesIndex ? 3 : 1
                Text { x: 24; anchors.verticalCenter: parent.verticalCenter; text: modelData.name; color: dashboard.ink; font.pixelSize: 30 }
                Text {
                    anchors.right: parent.right; anchors.rightMargin: 24; anchors.verticalCenter: parent.verticalCenter
                    text: modelData.id === "oggi" ? "SEMPRE VISIBILE" :
                          dashboard.visibleModules.indexOf(modelData.id) !== -1 ? "VISIBILE" : "NASCOSTO"
                    color: modelData.id === "oggi" ? dashboard.muted :
                           dashboard.visibleModules.indexOf(modelData.id) !== -1 ? dashboard.accent : "#efbd75"
                    font.pixelSize: 23; font.bold: true
                }
                MouseArea { anchors.fill: parent; enabled: modelData.id !== "oggi"; onClicked: { dashboard.modulesIndex = index; dashboard.toggleModule(index) } }
            }
        }
        Text {
            visible: dashboard.overlay === "modules"; x: 0; y: 441; width: 850
            text: "2/8 SELEZIONA     5 MOSTRA/NASCONDI     ·     OGGI RESTA SEMPRE VISIBILE"
            color: dashboard.muted; font.pixelSize: 21
        }
        Text { visible: dashboard.overlay === "commands"; x: 0; y: 105; width: 850; text: "1 HOME     2 SU       3 AVVISI\n4 SINISTRA 5 OK       6 DESTRA\n7 INDIETRO 8 GIÙ      9 MENU"; color: dashboard.ink; font.pixelSize: 34; lineHeight: 1.7 }
        Repeater {
            model: dashboard.systemLabels
            delegate: Rectangle {
                required property string modelData
                required property int index
                objectName: "systemRow" + index
                visible: dashboard.overlay === "system"
                x: 0; y: 87 + index * 52; width: 555; height: 47
                radius: 8
                color: index === dashboard.systemIndex ? "#28403f" : dashboard.panel
                border.color: index === dashboard.systemIndex ? dashboard.accent : dashboard.edge
                border.width: index === dashboard.systemIndex ? 3 : 1
                Text { x: 17; anchors.verticalCenter: parent.verticalCenter; text: modelData; color: dashboard.ink; font.pixelSize: 24 }
                Text {
                    anchors.right: parent.right; anchors.rightMargin: 17; anchors.verticalCenter: parent.verticalCenter
                    text: "‹ " + dashboard.systemValue(index) + " ›"
                    color: index === dashboard.systemIndex ? dashboard.accent : dashboard.muted
                    font.pixelSize: 23; font.bold: index === dashboard.systemIndex
                }
                MouseArea { anchors.fill: parent; onClicked: { dashboard.systemIndex = index; dashboard.adjustSystem(1) } }
            }
        }
        Rectangle {
            visible: dashboard.overlay === "system"
            x: 577; y: 87; width: 295; height: 359; radius: 9
            color: dashboard.panel; border.color: dashboard.edge
            Text { x: 18; y: 14; text: "STATO"; color: dashboard.accent; font.pixelSize: 23; font.bold: true }
            Text {
                x: 18; y: 53; width: 259
                text: "Dashboard v0.4\nCPU " + (dashboard.dashboardState ? dashboard.dashboardState.systemState.data.cpuTemperature : "N/D") +
                      "\nRAM " + (dashboard.dashboardState ? dashboard.dashboardState.systemState.data.memoryUsage : "N/D") +
                      "\nAccesa da " + (dashboard.dashboardState ? dashboard.dashboardState.systemState.data.uptime : "N/D") +
                      "\nTastiera " + (dashboard.keypad && dashboard.keypad.connected ? "collegata" : "assente")
                color: dashboard.ink; font.pixelSize: 22; lineHeight: 1.32; wrapMode: Text.WordWrap
            }
            Text {
                x: 18; y: 248; width: 259
                text: "Luce: " + dashboard.brightnessPercent + "%\nImmagine, non pannello"
                color: dashboard.muted; font.pixelSize: 20; lineHeight: 1.25; wrapMode: Text.WordWrap
            }
        }
        Text {
            visible: dashboard.overlay === "system"; x: 1; y: 465; width: 870
            text: "2/8 SELEZIONA    4/6 REGOLA    5 CAMBIA    ·    20–100%, passi di 5%"
            color: dashboard.muted; font.pixelSize: 21
        }
        Text {
            visible: dashboard.overlay === "detail"; x: 0; y: 130; width: 850
            text: dashboard.familyId === "meteo" ? "Fonte: Open-Meteo\n" + dashboard.weatherStatus() + "\nVento: " + (dashboard.weatherData.wind || "—") + "\nUmidità: " + (dashboard.weatherData.humidity || "—") :
                  "Oggi · " + dashboard.dateText() + "\n" + dashboard.weatherStatus()
            color: dashboard.ink; font.pixelSize: 31; lineHeight: 1.5
        }
        Text { x: 0; y: 522; text: "7  INDIETRO      1  HOME"; color: dashboard.accent; font.pixelSize: 27 }
    }

}
