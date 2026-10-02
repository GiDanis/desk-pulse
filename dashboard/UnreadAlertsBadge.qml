import QtQuick
import "themes"
import "components"

Rectangle {
    id: visualRoot
    property StyleFacade style: Theme
    required property var dashboard
    objectName: "unreadAlertsBadge"
    x: 487; y: 31; width: 276; height: 36; radius: visualRoot.style.radiusBadge
    color: visualRoot.style.surface
    border.color: visualRoot.style.border
    AppText { style: visualRoot.style;
        anchors.centerIn: parent
        text: dashboard.unreadAlertCount === 1 ? "3 · NUOVO AVVISO" :
              "3 · " + dashboard.unreadAlertCount + " NUOVI AVVISI"
        color: visualRoot.style.accent; font.pixelSize: visualRoot.style.font21; font.weight: (true) ? visualRoot.style.headingWeight : visualRoot.style.bodyWeight
    }
    MouseArea { anchors.fill: parent; onClicked: dashboard.activateKey(3) }
}
