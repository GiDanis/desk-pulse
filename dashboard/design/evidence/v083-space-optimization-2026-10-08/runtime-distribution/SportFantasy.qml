import QtQuick
import "themes"
import "components"

Item {
    id: root
    property StyleFacade style: Theme
    required property var dashboard
    readonly property var fantasy: dashboard.fantasyData
    readonly property var team: (fantasy.teams || [])[dashboard.fantasyTeamIndex] || ({})
    readonly property var rows: dashboard.fantasyRows
    readonly property int start: Math.floor(Math.max(0, dashboard.fantasyPlayerIndex) / root.style.fantasyRows) * root.style.fantasyRows
    AppText { style: root.style; width: 872; text: (dashboard.sportMatch.homeTeam || "") + " – " + (dashboard.sportMatch.awayTeam || "") + " · " + (dashboard.sportMatch.status === "scheduled" ? "VS" : dashboard.sportMatch.scoreText || "—"); color: root.style.textSecondary; font.pixelSize: root.style.font23; elide: Text.ElideRight }
    AppText { style: root.style; y: 37; width: 660; text: (root.team.name || "") + (root.team.formation ? " · " + root.team.formation : ""); color: root.style.accentTextOnCard; font.pixelSize: root.style.font30; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; elide: Text.ElideRight }
    AppText { style: root.style; x: 662; y: 42; width: 210; horizontalAlignment: Text.AlignRight; text: "5 CAMBIA SQUADRA"; color: root.style.textSecondary; font.pixelSize: root.style.font20 }
    Rectangle { y: 81; width: 872; height: 39; radius: root.style.radiusButton; color: dashboard.fantasyPlayerIndex === -1 ? root.style.surfaceFocused : "transparent"; border.width: root.style.borderWidth; border.color: dashboard.fantasyPlayerIndex === -1 ? root.style.focusIndicator : "transparent" }
    AppText { style: root.style; x: 12; y: 89; width: 580; text: dashboard.fantasyPlayerIndex === -1 ? "5 AGGIORNA VOTI · 8 CALCIATORI" : fantasy.provisional ? "PROVVISORI · FANTAVOTO CALCOLATO" : "TITOLARI · SUBENTRATI · PANCHINA"; color: root.style.textSecondary; font.pixelSize: root.style.font20; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
    AppText { style: root.style; x: 589; y: 89; width: 133; horizontalAlignment: Text.AlignHCenter; text: "VOTO BASE"; color: root.style.textSecondary; font.pixelSize: root.style.font20; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
    AppText { style: root.style; x: 735; y: 89; width: 125; horizontalAlignment: Text.AlignHCenter; text: "FANTAVOTO"; color: root.style.accentTextOnCard; font.pixelSize: root.style.font20; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
    Repeater {
        model: root.rows.slice(root.start, root.start + root.style.fantasyRows)
        delegate: Rectangle {
            required property var modelData
            required property int index
            y: 131 + index * 48; width: 872; height: 44; radius: root.style.radiusButton
            color: root.start + index === dashboard.fantasyPlayerIndex ? root.style.surfaceFocused : root.style.surface
            border.color: root.start + index === dashboard.fantasyPlayerIndex ? root.style.focusIndicator : root.style.border
            border.width: root.start + index === dashboard.fantasyPlayerIndex ? root.style.borderWidth : root.style.hairlineWidth
            AppText { style: root.style; x: 12; width: 95; anchors.verticalCenter: parent.verticalCenter; text: (modelData.role || "—") + (modelData.shirtNumber == null ? "" : " · " + modelData.shirtNumber); color: root.style.textSecondary; font.pixelSize: root.style.font21 }
            AppText { style: root.style; x: 107; width: 390; anchors.verticalCenter: parent.verticalCenter; text: modelData.name || ""; color: root.style.textPrimary; font.pixelSize: root.style.font25; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; elide: Text.ElideRight }
            AppText { style: root.style; x: 501; width: 87; anchors.verticalCenter: parent.verticalCenter; text: modelData.group === "Titolari" ? (modelData.outMinute == null ? "TIT" : "↓ " + modelData.outMinute + "′") : modelData.group === "Subentrati" ? (modelData.inMinute == null ? "SUB" : "↑ " + modelData.inMinute + "′") : modelData.group === "Panchina" ? "PAN" : "FONTE"; color: root.style.textSecondary; font.pixelSize: root.style.font19 }
            AppText { role: "numbers"; style: root.style; objectName: "fantasyBaseVote"; x: 590; width: 132; anchors.verticalCenter: parent.verticalCenter; text: modelData.voteText || "—"; color: root.style.textPrimary; font.pixelSize: root.style.font29; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; horizontalAlignment: Text.AlignHCenter }
            AppText { style: root.style; objectName: "fantasyFinalVote"; x: 735; width: 125; anchors.verticalCenter: parent.verticalCenter; text: modelData.fantavoteText || "—"; color: root.style.accentTextOnCard; font.pixelSize: root.style.font29; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; horizontalAlignment: Text.AlignHCenter }
        }
    }
    AppText { style: root.style; objectName: "fantasyEmptyText"; visible: !rows.length; x: 12; y: 155; width: 848; text: fantasy.message || "Formazioni e voti non ancora disponibili."; color: root.style.textPrimary; font.pixelSize: root.style.font28; wrapMode: Text.WordWrap }
    AppText { style: root.style; x: 0; y: 384; width: 872; text: root.rows.length ? (Math.max(0, dashboard.fantasyPlayerIndex) + 1) + "/" + root.rows.length + " · 2/8 SCORRI · — NON DISPONIBILE · SV SENZA VOTO" : "I voti riguardano esclusivamente il campionato Serie A."; color: root.style.textSecondary; font.pixelSize: root.style.font20; elide: Text.ElideRight }
}
