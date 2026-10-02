import QtQuick
import "themes"
import "components"

Item {
    id: root
    property StyleFacade style: Theme
    required property var dashboard
    readonly property var sportState: dashboard.sport
    readonly property var sportInfo: dashboard.sportData
    readonly property bool results: dashboard.sportView === "RISULTATI"
    function stamp(seconds) {
        return seconds ? new Date(seconds * 1000).toLocaleString(Qt.locale("it_IT"), "dd/MM hh:mm") : "—"
    }
    function score(value) { return value.status === "scheduled" ? "VS" : value.scoreText || "—" }
    function status() {
        if (sportState.status === "offline") return "OFFLINE · DATI PRECEDENTI"
        if (sportState.status === "stale") return "DATI PRECEDENTI"
        if (sportState.status === "error") return "AGGIORNAMENTO NON RIUSCITO"
        if (sportState.status === "updating") return "AGGIORNAMENTO"
        if (sportState.status === "unavailable") return "IN ATTESA DEI DATI"
        return "VERIFICATO " + stamp(sportState.updatedAt)
    }
    Rectangle { width: 872; height: 76; radius: root.style.radiusRow; color: root.style.surface; border.color: root.style.border }
    AppText { style: root.style; x: 18; y: 9; text: "SERIE A · " + (sportInfo.season || ""); color: root.style.textPrimary; font.pixelSize: root.style.font27; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
    AppText { style: root.style; objectName: "sportSourceText"; x: 18; y: 43; width: 365; text: "Fonte: " + sportState.source + (sportInfo.calendarScope === "nearby" ? " · calendario parziale" : ""); color: root.style.textSecondary; font.pixelSize: root.style.font19; elide: Text.ElideRight }
    AppText { style: root.style; x: 397; y: 14; width: 455; horizontalAlignment: Text.AlignRight; text: root.status(); color: sportState.status === "active" || sportState.status === "updating" ? root.style.accent : SemanticStyle.warning; font.pixelSize: root.style.font21; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; elide: Text.ElideRight }
    AppText { style: root.style; x: 397; y: 44; width: 455; horizontalAlignment: Text.AlignRight; text: sportInfo.cacheError || (sportState.status === "offline" || sportState.status === "stale" ? "Ultimo dato " + root.stamp(sportState.updatedAt) : sportInfo.fallbackReason ? "Fonte di riserva" : "Orari italiani"); color: root.style.textSecondary; font.pixelSize: root.style.font19 }

    readonly property bool tableView: dashboard.sportView === "CLASSIFICA"
    readonly property bool inProgress: dashboard.sportView === "IN CORSO"
    readonly property var rows: tableView ? (sportInfo.standings || []).slice(0, root.style.overviewRows) : results ? (sportInfo.lastFinished || []).slice(0, root.style.overviewRows) : dashboard.sportOverviewMatches.slice(dashboard.sportOverviewPage * root.style.overviewRows, dashboard.sportOverviewPage * root.style.overviewRows + root.style.overviewRows)
    AppText { style: root.style;
        x: 0; y: 94; width: 872
        text: root.tableView ? "CLASSIFICA · PRIME POSIZIONI" : root.results ? "ULTIMI RISULTATI" + (sportInfo.resultsRound ? " · GIORNATA " + sportInfo.resultsRound : "") : root.inProgress ? ((sportInfo.activeMatches || []).length ? "PARTITE IN CORSO" : "RISULTATO FINALE") : "PROSSIME PARTITE" + (root.rows.length && root.rows[0].round ? " · GIORNATA " + root.rows[0].round : "")
        color: root.style.accent; font.pixelSize: root.style.font26; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight
    }
    Repeater {
        model: root.rows
        delegate: Rectangle {
            required property var modelData
            required property int index
            readonly property bool favourite: !!root.sportInfo.favourite && (modelData.homeTeamId === root.sportInfo.favourite || modelData.awayTeamId === root.sportInfo.favourite || root.tableView && modelData.teamId === root.sportInfo.favourite)
            x: 0; y: 138 + index * 86; width: 872; height: 76; radius: root.style.radiusRow; color: root.style.surface; border.color: root.style.border
            Rectangle { visible: parent.favourite; x: 1; y: 10; width: 5; height: 56; radius: root.style.radiusMarker; color: root.style.accent }
            AppText { style: root.style; x: 16; y: 7; width: 664; text: root.tableView ? modelData.position + ".  " + modelData.team : modelData.homeTeam + " – " + modelData.awayTeam; color: root.style.textPrimary; font.pixelSize: root.style.font29; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; elide: Text.ElideRight }
            AppText { style: root.style; x: 16; y: 43; width: 694; text: root.tableView ? "G " + modelData.played + " · DR " + (modelData.goalDifference === null ? "—" : modelData.goalDifference) : modelData.when + " · " + modelData.statusText + (modelData.minute ? " " + modelData.minute : "") + (modelData.pendingVAR ? " · VAR" : ""); color: modelData.isLive ? root.style.accent : root.style.textSecondary; font.pixelSize: root.style.font21; elide: Text.ElideRight }
            AppText { role: "numbers"; style: root.style; x: 689; y: 17; width: 163; horizontalAlignment: Text.AlignRight; text: root.tableView ? modelData.points + " PT" : root.score(modelData); color: root.style.accent; font.pixelSize: root.style.font33; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
        }
    }
    AppText { style: root.style;
        visible: !root.rows.length; x: 0; y: 155; width: 872
        text: sportState.error || (root.tableView ? "Classifica non disponibile" : root.results ? "Risultati non disponibili" : root.inProgress ? "Le partite sono terminate · 5 per consultare" : "Nessun prossimo incontro disponibile")
        color: root.style.textPrimary; font.pixelSize: root.style.font32; wrapMode: Text.WordWrap
    }
    AppText { style: root.style;
        x: 0; y: 408; width: 872; color: root.style.textSecondary; font.pixelSize: root.style.font22; elide: Text.ElideRight
        text: root.tableView ? "5 TUTTE LE 20 SQUADRE · 2/8 CAMBIA VISTA" : root.results ? "5 TUTTI I RISULTATI · 2/8 ANCHE CLASSIFICA" :
            dashboard.sportOverviewMatches.length + " partite" + (dashboard.sportOverviewPages > 1 ? " · Pagina " + (dashboard.sportOverviewPage + 1) + "/" + dashboard.sportOverviewPages + " · cambia ogni 8 s" : "") + " · 5 ELENCO" + (root.inProgress && !sportInfo.liveVerified ? " · feed da collaudare" : "")
    }
}
