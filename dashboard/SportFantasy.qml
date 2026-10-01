import QtQuick

Item {
    id: root
    required property var dashboard
    readonly property var fantasy: dashboard.fantasyData
    readonly property var team: (fantasy.teams || [])[dashboard.fantasyTeamIndex] || ({})
    readonly property var rows: dashboard.fantasyRows
    readonly property int start: Math.floor(Math.max(0, dashboard.fantasyPlayerIndex) / 5) * 5
    Text { width: 872; text: (dashboard.sportMatch.homeTeam || "") + " – " + (dashboard.sportMatch.awayTeam || "") + " · " + (dashboard.sportMatch.status === "scheduled" ? "VS" : dashboard.sportMatch.scoreText || "—"); color: dashboard.muted; font.pixelSize: 23; elide: Text.ElideRight }
    Text { y: 37; width: 660; text: (root.team.name || "") + (root.team.formation ? " · " + root.team.formation : ""); color: dashboard.accent; font.pixelSize: 30; font.bold: true; elide: Text.ElideRight }
    Text { x: 662; y: 42; width: 210; horizontalAlignment: Text.AlignRight; text: "5 CAMBIA SQUADRA"; color: dashboard.muted; font.pixelSize: 20 }
    Rectangle { y: 81; width: 872; height: 39; radius: 6; color: dashboard.fantasyPlayerIndex === -1 ? "#28403f" : "transparent"; border.width: 2; border.color: dashboard.fantasyPlayerIndex === -1 ? dashboard.accent : "transparent" }
    Text { x: 12; y: 89; width: 580; text: dashboard.fantasyPlayerIndex === -1 ? "5 AGGIORNA VOTI · 8 CALCIATORI" : "TITOLARI · SUBENTRATI · PANCHINA"; color: dashboard.muted; font.pixelSize: 20; font.bold: true }
    Text { x: 589; y: 89; width: 133; horizontalAlignment: Text.AlignHCenter; text: "VOTO BASE"; color: dashboard.muted; font.pixelSize: 20; font.bold: true }
    Text { x: 735; y: 89; width: 125; horizontalAlignment: Text.AlignHCenter; text: "FANTAVOTO"; color: dashboard.accent; font.pixelSize: 20; font.bold: true }
    Repeater {
        model: root.rows.slice(root.start, root.start + 5)
        delegate: Rectangle {
            required property var modelData
            required property int index
            y: 131 + index * 48; width: 872; height: 44; radius: 6
            color: root.start + index === dashboard.fantasyPlayerIndex ? "#28403f" : dashboard.panel
            border.color: root.start + index === dashboard.fantasyPlayerIndex ? dashboard.accent : dashboard.edge
            border.width: root.start + index === dashboard.fantasyPlayerIndex ? 2 : 1
            Text { x: 12; width: 95; anchors.verticalCenter: parent.verticalCenter; text: (modelData.role || "—") + (modelData.shirtNumber == null ? "" : " · " + modelData.shirtNumber); color: dashboard.muted; font.pixelSize: 21 }
            Text { x: 107; width: 390; anchors.verticalCenter: parent.verticalCenter; text: modelData.name || ""; color: dashboard.ink; font.pixelSize: 25; font.bold: true; elide: Text.ElideRight }
            Text { x: 501; width: 87; anchors.verticalCenter: parent.verticalCenter; text: modelData.group === "Titolari" ? (modelData.outMinute == null ? "TIT" : "↓ " + modelData.outMinute + "′") : modelData.group === "Subentrati" ? (modelData.inMinute == null ? "SUB" : "↑ " + modelData.inMinute + "′") : modelData.group === "Panchina" ? "PAN" : "FONTE"; color: dashboard.muted; font.pixelSize: 19 }
            Text { objectName: "fantasyBaseVote"; x: 590; width: 132; anchors.verticalCenter: parent.verticalCenter; text: modelData.voteText || "—"; color: dashboard.ink; font.pixelSize: 29; font.bold: true; horizontalAlignment: Text.AlignHCenter }
            Text { objectName: "fantasyFinalVote"; x: 735; width: 125; anchors.verticalCenter: parent.verticalCenter; text: modelData.fantavoteText || "—"; color: dashboard.accent; font.pixelSize: 29; font.bold: true; horizontalAlignment: Text.AlignHCenter }
        }
    }
    Text { objectName: "fantasyEmptyText"; visible: !rows.length; x: 12; y: 155; width: 848; text: fantasy.message || "Formazioni e voti non ancora disponibili."; color: dashboard.ink; font.pixelSize: 28; wrapMode: Text.WordWrap }
    Text { x: 0; y: 384; width: 872; text: root.rows.length ? (Math.max(0, dashboard.fantasyPlayerIndex) + 1) + "/" + root.rows.length + " · 2/8 SCORRI · — NON DISPONIBILE · SV SENZA VOTO" : "I voti riguardano esclusivamente il campionato Serie A."; color: dashboard.muted; font.pixelSize: 20; elide: Text.ElideRight }
}
