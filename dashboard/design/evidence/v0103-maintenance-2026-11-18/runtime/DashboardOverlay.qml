import QtQuick
import "themes"
import "components"

Item {
    id: overlayRoot
    property StyleFacade style: Theme
    required property var dashboard
    Rectangle { visible: dashboard.overlay !== ""; anchors.fill: parent; color: overlayRoot.style.backgroundOverlay }
    Item {
        visible: dashboard.overlay !== ""
        x: 44; y: 35; width: 872; height: 570
        AppText { style: overlayRoot.style;
            text: dashboard.overlay === "menu" ? "MENU" : dashboard.overlay === "alerts" ? "AVVISI" :
                  dashboard.overlay === "commands" ? "COMANDI" : dashboard.overlay === "settings" ? "IMPOSTAZIONI" :
                  dashboard.overlay === "modules" ? "MODULI VISIBILI" :
                  dashboard.overlay === "system" ? "ASPETTO E DISPOSITIVO" :
                  dashboard.overlay === "notifications" ? "NOTIFICHE" :
                  dashboard.overlay === "alertDetail" ? "DETTAGLIO AVVISO" : "DETTAGLI"
            color: overlayRoot.style.accentTextOnOverlay; font.pixelSize: overlayRoot.style.font37; font.weight: (true) ? overlayRoot.style.headingWeight : overlayRoot.style.bodyWeight
        }
        Repeater {
            model: dashboard.overlay === "menu" ? dashboard.menuItems : []
            delegate: Rectangle {
                required property string modelData
                required property int index
                x: 0; y: 77 + index * 86; width: 872; height: 72
                radius: overlayRoot.style.radiusRow; color: index === dashboard.menuIndex ? overlayRoot.style.surfaceFocused : overlayRoot.style.surface
                border.color: index === dashboard.menuIndex ? overlayRoot.style.focusIndicator : overlayRoot.style.border
                border.width: index === dashboard.menuIndex ? overlayRoot.style.focusWidth : overlayRoot.style.hairlineWidth
                AppText { style: overlayRoot.style; x: 24; anchors.verticalCenter: parent.verticalCenter; text: modelData; color: overlayRoot.style.textPrimary; font.pixelSize: overlayRoot.style.font31 }
                AppText { style: overlayRoot.style;
                    anchors.right: parent.right; anchors.rightMargin: 24; anchors.verticalCenter: parent.verticalCenter
                    text: index < 3 ? "›" : ""
                    color: overlayRoot.style.textSecondary; font.pixelSize: overlayRoot.style.font24
                }
                MouseArea { anchors.fill: parent; onClicked: { dashboard.menuIndex = index; dashboard.selectMenu() } }
            }
        }
        AppText { style: overlayRoot.style; visible: dashboard.overlay === "commands"; x: 0; y: 105; width: 850; text: "1 HOME      2 SU       3 AVVISI\n4 SINISTRA  5 OK       6 DESTRA\n7 INDIETRO  8 GIÙ      9 MENU"; color: overlayRoot.style.textPrimary; font.pixelSize: overlayRoot.style.font34; lineHeight: 1.7 }
        AppText { style: overlayRoot.style;
            visible: dashboard.overlay === "detail"; x: 0; y: 130; width: 850
            text: dashboard.familyId === "meteo" ? "Fonte: Open-Meteo\n" + dashboard.weatherStatus() + "\nVento: " + (dashboard.weatherData.wind || "—") + "\nUmidità: " + (dashboard.weatherData.humidity || "—") :
                  "Oggi · " + dashboard.dateText() + "\n" + dashboard.weatherStatus()
            color: overlayRoot.style.textPrimary; font.pixelSize: overlayRoot.style.font31; lineHeight: 1.5
        }
        AppText { style: overlayRoot.style; x: 0; y: 522; text: "7  INDIETRO      1  HOME"; color: overlayRoot.style.accentTextOnOverlay; font.pixelSize: overlayRoot.style.font27 }
    }

}
