import QtQuick

Item {
    id: root
    required property var dashboard
    readonly property var teamInfo: dashboard.teamData
    readonly property var teamStatus: dashboard.teamState
    readonly property var rows: (teamInfo.active || []).concat(teamInfo.upcoming || []).slice(0, 3)
    Rectangle { width: 872; height: 76; radius: 9; color: dashboard.panel; border.color: dashboard.edge }
    Text { x: 18; y: 9; width: 500; text: "LA MIA SQUADRA · " + (teamInfo.season || ""); color: dashboard.ink; font.pixelSize: 27; font.bold: true }
    Text { x: 18; y: 43; width: 835; text: "Fonte " + teamStatus.source + " · " + (teamInfo.calendarScope === "league" ? "Solo Serie A disponibile" : "Tutte le competizioni") + (teamStatus.updatedAt ? " · " + new Date(teamStatus.updatedAt * 1000).toLocaleString(Qt.locale("it_IT"), "dd/MM hh:mm") : ""); color: dashboard.muted; font.pixelSize: 20; elide: Text.ElideRight }
    Text { x: 548; y: 13; width: 306; horizontalAlignment: Text.AlignRight; text: teamStatus.status === "updating" ? "AGGIORNAMENTO" : teamStatus.status === "stale" || teamStatus.status === "offline" ? "DATI SALVATI" : teamStatus.status === "error" ? "NON DISPONIBILE" : ""; color: "#efbd75"; font.pixelSize: 21 }
    Text { y: 95; width: 872; text: teamInfo.name || "SCEGLI LA TUA SQUADRA"; color: dashboard.accent; font.pixelSize: 36; font.bold: true }
    Text { y: 143; width: 872; text: dashboard.sportData.favourite ? "Serie A · " + dashboard.teamStandingText() : "5 per impostare una preferita tra le 20 squadre di Serie A"; color: dashboard.muted; font.pixelSize: 24; elide: Text.ElideRight }
    Repeater {
        model: root.rows
        delegate: Rectangle {
            required property var modelData
            required property int index
            y: 186 + index * 68; width: 872; height: 60; radius: 8; color: dashboard.panel; border.color: dashboard.edge
            Text { x: 16; y: 5; width: 672; text: modelData.homeTeam + " – " + modelData.awayTeam; color: dashboard.ink; font.pixelSize: 27; font.bold: true; elide: Text.ElideRight }
            Text { x: 16; y: 35; width: 835; text: modelData.when + " · " + modelData.competitionName; color: dashboard.muted; font.pixelSize: 20; elide: Text.ElideRight }
            Text { x: 708; y: 9; width: 147; horizontalAlignment: Text.AlignRight; text: modelData.status === "scheduled" ? "VS" : modelData.scoreText; color: dashboard.accent; font.pixelSize: 29; font.bold: true }
        }
    }
    Text { visible: !root.rows.length; y: 218; width: 872; text: !dashboard.sportData.favourite ? "Calendario, risultati, club e rosa\nin un unico spazio." : teamStatus.error || "Nessuna prossima partita pubblicata dalla fonte."; color: dashboard.ink; font.pixelSize: 30; wrapMode: Text.WordWrap; lineHeight: 1.4 }
    Text { y: 408; width: 872; text: dashboard.sportData.favourite ? (teamInfo.upcoming || []).length + " future pubblicate · 5 CALENDARIO, INFO E ROSA" : "5 SCEGLI SQUADRA · preferenza salvata sul dispositivo"; color: dashboard.muted; font.pixelSize: 22; elide: Text.ElideRight }
}
