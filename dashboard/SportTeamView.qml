import QtQuick
import "themes"
import "components"

Item {
    id: root
    property StyleFacade style: Theme
    required property var dashboard
    readonly property var teamInfo: dashboard.teamData
    readonly property var teamStatus: dashboard.teamState
    readonly property var rows: (teamInfo.active || []).concat(teamInfo.upcoming || []).slice(0, root.style.overviewRows)
    Rectangle { width: 872; height: 76; radius: root.style.radiusRow; color: root.style.surface; border.color: root.style.border }
    AppText { style: root.style; x: 18; y: 9; width: 500; text: "LA MIA SQUADRA · " + (teamInfo.season || ""); color: root.style.textPrimary; font.pixelSize: root.style.font27; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
    AppText { style: root.style; x: 18; y: 43; width: 835; text: "Fonte " + teamStatus.source + " · " + (teamInfo.calendarScope === "league" ? "Solo Serie A disponibile" : "Tutte le competizioni") + (teamStatus.updatedAt ? " · " + new Date(teamStatus.updatedAt * 1000).toLocaleString(Qt.locale("it_IT"), "dd/MM hh:mm") : ""); color: root.style.textSecondary; font.pixelSize: root.style.font20; elide: Text.ElideRight }
    AppText { style: root.style; x: 548; y: 13; width: 306; horizontalAlignment: Text.AlignRight; text: teamStatus.status === "updating" ? "AGGIORNAMENTO" : teamStatus.status === "stale" || teamStatus.status === "offline" ? "DATI SALVATI" : teamStatus.status === "error" ? "NON DISPONIBILE" : ""; color: SemanticStyle.warning; font.pixelSize: root.style.font21 }
    AppText { style: root.style; y: 95; width: 872; text: teamInfo.name || "SCEGLI LA TUA SQUADRA"; color: root.style.accent; font.pixelSize: root.style.font36; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
    AppText { style: root.style; y: 143; width: 872; text: dashboard.sportData.favourite ? "Serie A · " + dashboard.teamStandingText() : "5 per impostare una preferita tra le 20 squadre di Serie A"; color: root.style.textSecondary; font.pixelSize: root.style.font24; elide: Text.ElideRight }
    Repeater {
        model: root.rows
        delegate: Rectangle {
            required property var modelData
            required property int index
            y: 186 + index * 68; width: 872; height: 60; radius: root.style.radiusBadge; color: root.style.surface; border.color: root.style.border
            AppText { style: root.style; x: 16; y: 5; width: 672; text: modelData.homeTeam + " – " + modelData.awayTeam; color: root.style.textPrimary; font.pixelSize: root.style.font27; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; elide: Text.ElideRight }
            AppText { style: root.style; x: 16; y: 35; width: 835; text: modelData.when + " · " + modelData.competitionName; color: root.style.textSecondary; font.pixelSize: root.style.font20; elide: Text.ElideRight }
            AppText { style: root.style; x: 708; y: 9; width: 147; horizontalAlignment: Text.AlignRight; text: modelData.status === "scheduled" ? "VS" : modelData.scoreText; color: root.style.accent; font.pixelSize: root.style.font29; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
        }
    }
    AppText { style: root.style; visible: !root.rows.length; y: 218; width: 872; text: !dashboard.sportData.favourite ? "Calendario, risultati, club e rosa\nin un unico spazio." : teamStatus.error || "Nessuna prossima partita pubblicata dalla fonte."; color: root.style.textPrimary; font.pixelSize: root.style.font30; wrapMode: Text.WordWrap; lineHeight: 1.4 }
    AppText { style: root.style; y: 408; width: 872; text: dashboard.sportData.favourite ? (teamInfo.upcoming || []).length + " future pubblicate · 5 CALENDARIO, INFO E ROSA" : "5 SCEGLI SQUADRA · preferenza salvata sul dispositivo"; color: root.style.textSecondary; font.pixelSize: root.style.font22; elide: Text.ElideRight }
}
