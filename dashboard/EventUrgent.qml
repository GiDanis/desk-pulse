import QtQuick
import "themes"
import "components"

Item {
    id: visualRoot
    property StyleFacade style: Theme
    required property var dashboard
    objectName: "eventUrgent"

    Rectangle { anchors.fill: parent; color: visualRoot.style.backgroundOverlay }
    Rectangle {
        x: 0; y: 0; width: parent.width; height: 8
        color: dashboard.urgentEvent.weatherSeverity === "rossa" ? SemanticStyle.critical : SemanticStyle.warning
    }
    AppText { style: visualRoot.style;
        x: 44; y: 52; width: 850
        text: "AVVISO PRIORITARIO"
        color: visualRoot.style.accent; font.pixelSize: visualRoot.style.font30; font.weight: (true) ? visualRoot.style.headingWeight : visualRoot.style.bodyWeight
    }
    AppText { style: visualRoot.style;
        id: urgentTitle
        x: 44; y: 132; width: 860
        text: dashboard.urgentEvent.title || ""
        color: visualRoot.style.textPrimary; font.pixelSize: visualRoot.style.font56; font.weight: (true) ? visualRoot.style.headingWeight : visualRoot.style.bodyWeight
        wrapMode: Text.WordWrap
        maximumLineCount: 2; elide: Text.ElideRight
    }
    AppText { style: visualRoot.style;
        id: urgentDetail
        x: 44; y: urgentTitle.y + urgentTitle.height + 20; width: 850
        text: dashboard.urgentEvent.detail || ""
        color: visualRoot.style.textPrimary; font.pixelSize: visualRoot.style.font30
        wrapMode: Text.WordWrap
        maximumLineCount: 3; elide: Text.ElideRight
    }
    AppText { style: visualRoot.style;
        x: 44; y: Math.max(421, urgentDetail.y + urgentDetail.height + 18); width: 850
        text: "Fonte: " + (dashboard.urgentEvent.sourceLabel || dashboard.urgentEvent.source || "") +
              " · Emesso " + dashboard.eventStamp(dashboard.urgentEvent.issuedAt)
        color: visualRoot.style.textSecondary; font.pixelSize: visualRoot.style.font23; wrapMode: Text.WordWrap
    }
    Rectangle { x: 44; y: 526; width: 872; height: 2; color: visualRoot.style.border }
    AppText { style: visualRoot.style;
        x: 44; y: 552; width: 872
        text: "5 DETTAGLI          7 CHIUDI          1 HOME"
        color: visualRoot.style.accent; font.pixelSize: visualRoot.style.font27
    }
}
