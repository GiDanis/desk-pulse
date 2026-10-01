import QtQuick

Item {
    required property var dashboard
    objectName: "eventUrgent"

    Rectangle { anchors.fill: parent; color: "#0b1219" }
    Rectangle {
        x: 0; y: 0; width: parent.width; height: 8
        color: dashboard.urgentEvent.title && dashboard.urgentEvent.title.indexOf("rossa") !== -1 ? "#f08779" : "#efbd75"
    }
    Text {
        x: 44; y: 52; width: 850
        text: "AVVISO PRIORITARIO"
        color: dashboard.accent; font.pixelSize: 30; font.bold: true
    }
    Text {
        id: urgentTitle
        x: 44; y: 132; width: 860
        text: dashboard.urgentEvent.title || ""
        color: dashboard.ink; font.pixelSize: 56; font.bold: true
        wrapMode: Text.WordWrap
        maximumLineCount: 2; elide: Text.ElideRight
    }
    Text {
        id: urgentDetail
        x: 44; y: urgentTitle.y + urgentTitle.height + 20; width: 850
        text: dashboard.urgentEvent.detail || ""
        color: dashboard.ink; font.pixelSize: 30
        wrapMode: Text.WordWrap
        maximumLineCount: 3; elide: Text.ElideRight
    }
    Text {
        x: 44; y: Math.max(421, urgentDetail.y + urgentDetail.height + 18); width: 850
        text: "Fonte: " + (dashboard.urgentEvent.sourceLabel || dashboard.urgentEvent.source || "") +
              " · Emesso " + dashboard.eventStamp(dashboard.urgentEvent.issuedAt)
        color: dashboard.muted; font.pixelSize: 23; wrapMode: Text.WordWrap
    }
    Rectangle { x: 44; y: 526; width: 872; height: 2; color: dashboard.edge }
    Text {
        x: 44; y: 552; width: 872
        text: "5 DETTAGLI          1 CHIUDI          7 HOME"
        color: dashboard.accent; font.pixelSize: 27
    }
}
