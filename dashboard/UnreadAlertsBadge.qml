import QtQuick

Rectangle {
    required property var dashboard
    objectName: "unreadAlertsBadge"
    x: 487; y: 31; width: 276; height: 36; radius: 8
    color: dashboard.panel
    border.color: dashboard.edge
    Text {
        anchors.centerIn: parent
        text: dashboard.unreadAlertCount === 1 ? "3 · NUOVO AVVISO" :
              "3 · " + dashboard.unreadAlertCount + " NUOVI AVVISI"
        color: dashboard.accent; font.pixelSize: 21; font.bold: true
    }
    MouseArea { anchors.fill: parent; onClicked: dashboard.activateKey(3) }
}
