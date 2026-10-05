import QtQuick

// Application-owned feedback stays usable while an author renderer is loading.
// No author fonts, scene, motion recipe or theme component is required here.
Rectangle {
    id: loading
    required property var controller
    property bool delayElapsed: false
    readonly property bool preparing: !!controller.themeCandidate.generation
    objectName: "themeLoading"
    anchors.fill: parent
    color: "#17242d"
    visible: preparing && delayElapsed && !controller.urgentEvent.id
    onPreparingChanged: {
        delayElapsed = false
        if (preparing) showDelay.restart()
        else showDelay.stop()
    }
    Timer { id: showDelay; interval: 120; onTriggered: loading.delayElapsed = true }
    Column {
        anchors.centerIn: parent
        spacing: 18
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Preparazione del tema…"; color: "#ffffff"; font.pixelSize: 30 }
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Le nuove schermate saranno visibili appena pronte."; color: "#bdcbd3"; font.pixelSize: 20 }
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "7 ANNULLA  ·  1 HOME"; color: "#bdcbd3"; font.pixelSize: 20 }
    }
    MouseArea { anchors.fill: parent }
}
