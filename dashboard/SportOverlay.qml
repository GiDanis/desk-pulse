import QtQuick
import "themes"
import "components"

Item {
    id: root
    property StyleFacade style: Theme
    required property var dashboard
    readonly property bool table: dashboard.overlay === "sportTable"
    readonly property bool listing: table || dashboard.overlay === "sportList"
    readonly property bool detail: dashboard.overlay === "sportDetail"
    readonly property bool settings: dashboard.overlay === "sportSettings"
    readonly property var match: dashboard.sportMatch
    readonly property var sportInfo: root.detail && dashboard.sportTeamDetail && dashboard.sportMatchId.indexOf("team:foto:") === 0 ? dashboard.teamData : dashboard.sportData
    function settingValue(index) {
        if (index === 0) return (sportInfo.teams || []).find(t => t.id === sportInfo.favourite)?.name || "Nessuna"
        if (index === 1) return sportInfo.showOnHome ? "ATTIVO" : "DISATTIVO"
        if (index === 2) return "APRI"
        if (index === 3) return sportInfo.selectedSeason || "—"
        return "APRI"
    }
    Rectangle { anchors.fill: parent; color: dashboard.color }
    readonly property int listStart: Math.floor(Math.max(0, dashboard.sportIndex) / root.style.compactRows) * root.style.compactRows
    readonly property bool scheduled: match.status === "scheduled"
    readonly property bool loading: sportInfo.selectedMatchId === match.canonicalMatchId && !!sportInfo.detailLoading
    readonly property string detailError: sportInfo.detailErrorMatchId === match.canonicalMatchId ? (sportInfo.detailError || "") : ""
    function lineup(side) { return (root.match.lineups || []).find(l => l.side === side) || ({players: []}) }
    AppText { style: root.style; x: 44; y: 30; width: 872; text: settings ? "IMPOSTAZIONI SPORT" : detail ? (root.match.competitionName || "SERIE A") + " · " + (root.match.season || root.sportInfo.season || "") : "SERIE A · " + dashboard.sportView + " · " + (root.sportInfo.season || ""); color: root.style.accent; font.pixelSize: root.style.font35; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
    Repeater {
        model: root.listing ? ["PARTITE", "CLASSIFICA"] : root.detail ? dashboard.sportDetailTabs : []
        delegate: SelectableRow { style: root.style; selectedState: selected;
            required property string modelData
            required property int index
            readonly property bool selected: root.listing ? index === (root.table ? 1 : 0) : index === dashboard.sportDetailPage
            x: 44 + index * (root.listing ? 442 : dashboard.sportDetailTabs.length === 4 ? 222 : 296); y: 87
            width: root.listing ? 430 : dashboard.sportDetailTabs.length === 4 ? 206 : 280; height: 43; radius: root.style.radiusPill
            color: selected ? root.style.surfaceFocused : root.style.surface
            border.color: selected ? root.style.accent : root.style.border
            border.width: selected ? root.style.borderWidth : root.style.hairlineWidth
            AppText { style: root.style; anchors.centerIn: parent; text: modelData; color: selected ? root.style.accent : root.style.textSecondary; font.pixelSize: root.style.font24; font.weight: (selected ) ? root.style.headingWeight : root.style.bodyWeight}
        }
    }
    Rectangle {
        visible: root.listing; x: 44; y: 143; width: 872; height: 43; radius: root.style.radiusPill
        color: dashboard.sportIndex === -1 ? root.style.surfaceFocused : "transparent"
        border.color: dashboard.sportIndex === -1 ? root.style.accent : "transparent"; border.width: root.style.borderWidth
        AppText { style: root.style; x: 16; anchors.verticalCenter: parent.verticalCenter; text: root.table ? "POSIZIONE / SQUADRA" : dashboard.sportView === "IN CORSO" ? "PARTITE IN CORSO" : "GIORNATA " + (dashboard.sportRound || "—"); color: root.style.textPrimary; font.pixelSize: root.style.font24; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
        AppText { style: root.style; x: 380; width: 474; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignRight; text: root.table ? "PARTITE · DIFFERENZA RETI · PUNTI" : dashboard.sportIndex === -1 ? "4/6 GIORNATA · 8 PARTITE" : dashboard.sportView === "IN CORSO" ? "4/6 CLASSIFICA" : "2 IN ALTO PER CAMBIARE GIORNATA"; color: root.style.textSecondary; font.pixelSize: root.style.font20 }
    }
    Repeater {
        model: root.listing ? dashboard.sportRows.slice(root.listStart, root.listStart + root.style.compactRows) : []
        delegate: SelectableRow { style: root.style; selectedState: absoluteIndex === dashboard.sportIndex;
            required property var modelData
            required property int index
            readonly property int absoluteIndex: root.listStart + index
            readonly property bool favourite: !!root.sportInfo.favourite && (modelData.homeTeamId === root.sportInfo.favourite || modelData.awayTeamId === root.sportInfo.favourite || root.table && modelData.teamId === root.sportInfo.favourite)
            x: 44; y: 200 + index * 102; width: 872; height: 90; radius: root.style.radiusRow
            color: absoluteIndex === dashboard.sportIndex ? root.style.surfaceFocused : root.style.surface
            border.color: absoluteIndex === dashboard.sportIndex ? root.style.accent : root.style.border
            border.width: absoluteIndex === dashboard.sportIndex ? root.style.focusWidth : root.style.hairlineWidth
            Rectangle { visible: parent.favourite; x: 1; y: 12; width: 5; height: 66; color: root.style.accent; radius: root.style.radiusMarker }
            AppText { style: root.style; x: 18; y: 12; width: 645; text: root.table ? modelData.position + ".  " + modelData.team : modelData.homeTeam + " – " + modelData.awayTeam; color: root.style.textPrimary; font.pixelSize: root.style.font30; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; elide: Text.ElideRight }
            AppText { style: root.style; x: 18; y: 53; width: 710; text: root.table ? "G " + modelData.played + " · DR " + (modelData.goalDifference === null ? "—" : modelData.goalDifference) : modelData.when + " · " + modelData.statusText; color: root.style.textSecondary; font.pixelSize: root.style.font22; elide: Text.ElideRight }
            AppText { style: root.style; x: 676; y: 22; width: 174; horizontalAlignment: Text.AlignRight; text: root.table ? modelData.points + " PT" : modelData.status === "scheduled" ? "VS" : (modelData.scoreText || "—"); color: root.style.accent; font.pixelSize: root.style.font30; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
        }
    }
    AppText { style: root.style; visible: listing; x: 44; y: 525; width: 872; text: dashboard.sportRows.length ? (Math.max(0, dashboard.sportIndex) + 1) + "/" + dashboard.sportRows.length + " · 2/8 SCORRI · " + (dashboard.sportIndex === -1 ? "4/6 GIORNATA" : "4/6 SCHEDE") + (table ? "" : " · 5 APRI") : "Nessuna partita disponibile per questa giornata"; color: root.style.textSecondary; font.pixelSize: root.style.font23 }
    Item {
        visible: root.detail && dashboard.sportDetailPage !== 3; x: 44; y: 146; width: 872; height: 420
        AppText { style: root.style; x: 0; width: 315; height: 68; text: root.match.homeTeam || ""; color: root.style.textPrimary; font.pixelSize: root.style.font33; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
        AppText { style: root.style; x: 322; y: 4; width: 228; text: root.scheduled ? "VS" : root.match.scoreText || "—"; color: root.style.accent; font.pixelSize: root.style.font52; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; horizontalAlignment: Text.AlignHCenter }
        AppText { style: root.style; x: 557; width: 315; height: 68; text: root.match.awayTeam || ""; color: root.style.textPrimary; font.pixelSize: root.style.font33; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
        AppText { style: root.style; y: 78; width: 872; horizontalAlignment: Text.AlignHCenter; text: (root.match.when || "") + " · " + (root.match.statusText || "") + (root.match.round ? " · Giornata " + root.match.round : "") + (root.match.pendingVAR ? " · VAR" : ""); color: root.style.textSecondary; font.pixelSize: root.style.font23 }
        Item {
            visible: dashboard.sportDetailPage === 0; y: 125; width: 872
            AppText { style: root.style; width: 872; text: root.match.venue || (root.scheduled ? "Stadio da confermare" : "Riepilogo della partita"); color: root.style.textPrimary; font.pixelSize: root.style.font27; elide: Text.ElideRight }
            AppText { style: root.style; objectName: "sportDetailSummary"; y: 61; width: 872; height: 144; visible: !(root.match.events || []).length; text: root.scheduled ? "Calcio d’inizio " + (root.match.when || "da confermare") + "\nMarcatori e statistiche arriveranno durante la partita." : root.match.homeScore === 0 && root.match.awayScore === 0 ? "Nessun gol nella partita." : "Marcatori non disponibili dalla fonte."; color: root.style.textSecondary; font.pixelSize: root.style.font28; wrapMode: Text.WordWrap; lineHeight: 1.4 }
            Repeater {
                model: (root.match.events || []).slice(dashboard.sportDetailOffset, dashboard.sportDetailOffset + root.style.listRows)
                delegate: SelectableRow { style: root.style; selectedState: index === dashboard.sportSettingsIndex;
                    required property var modelData
                    required property int index
                    x: 0; y: 49 + index * 45; width: 872; height: 40; radius: root.style.radiusDense; color: root.style.surface
                    AppText { style: root.style; x: 13; anchors.verticalCenter: parent.verticalCenter; width: 575; text: modelData.minute + "′  " + modelData.player; color: root.style.textPrimary; font.pixelSize: root.style.font25; elide: Text.ElideRight }
                    AppText { style: root.style; x: 600; width: 258; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignRight; text: modelData.side === "home" ? root.match.homeTeam : root.match.awayTeam; color: root.style.textSecondary; font.pixelSize: root.style.font22; elide: Text.ElideRight }
                }
            }
            AppText { style: root.style; y: 236; visible: (root.match.events || []).length > 4; text: "2/8 SCORRI MARCATORI"; color: root.style.textSecondary; font.pixelSize: root.style.font20 }
        }
        Item {
            visible: dashboard.sportDetailPage === 1; y: 125; width: 872
            AppText { style: root.style; objectName: "sportDetailStatsEmpty"; visible: !(root.match.stats || []).length; y: 44; width: 872; horizontalAlignment: Text.AlignHCenter; text: root.scheduled ? "Statistiche disponibili dopo il calcio d’inizio" : "Statistiche non disponibili dalla fonte"; color: root.style.textSecondary; font.pixelSize: root.style.font28; wrapMode: Text.WordWrap }
            Repeater {
                model: root.match.stats || []
                delegate: SelectableRow { style: root.style;
                    required property var modelData
                    required property int index
                    y: index * 77; width: 872; height: 64; radius: root.style.radiusPill; color: root.style.surface
                    AppText { style: root.style; x: 25; width: 160; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignHCenter; text: modelData.home; color: root.style.accent; font.pixelSize: root.style.font35; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
                    AppText { style: root.style; x: 194; width: 484; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignHCenter; text: modelData.label; color: root.style.textPrimary; font.pixelSize: root.style.font27 }
                    AppText { style: root.style; x: 687; width: 160; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignHCenter; text: modelData.away; color: root.style.accent; font.pixelSize: root.style.font35; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
                }
            }
        }
        Item {
            visible: dashboard.sportDetailPage === 2; y: 120; width: 872
            AppText { style: root.style; objectName: "sportDetailLineupsEmpty"; visible: !(root.match.lineups || []).length; y: 44; width: 872; horizontalAlignment: Text.AlignHCenter; text: root.scheduled ? "Formazioni non ancora pubblicate" : "Formazioni non disponibili dalla fonte"; color: root.style.textSecondary; font.pixelSize: root.style.font28 }
            Repeater {
                model: (root.match.lineups || []).length ? ["home", "away"] : []
                delegate: Item {
                    required property string modelData
                    required property int index
                    readonly property var teamLineup: root.lineup(modelData)
                    x: index * 448; width: 424
                    AppText { style: root.style; width: 424; text: (index === 0 ? root.match.homeTeam : root.match.awayTeam) + " · " + (parent.teamLineup.formation || "—"); color: root.style.accent; font.pixelSize: root.style.font24; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; elide: Text.ElideRight }
                    Repeater {
                        model: parent.teamLineup.players || []
                        delegate: AppText { style: root.style; required property string modelData; required property int index; y: 34 + index * 22; width: 424; text: modelData; color: root.style.textPrimary; font.pixelSize: root.style.font22; elide: Text.ElideRight }
                    }
                    AppText { style: root.style; visible: !parent.teamLineup.players.length; y: 50; text: "Non disponibile"; color: root.style.textSecondary; font.pixelSize: root.style.font24 }
                }
            }
        }
    }
    SportFantasy { style: root.style; dashboard: root.dashboard; visible: root.detail && dashboard.sportDetailPage === 3; x: 44; y: 146; width: 872; height: 420 }
    AppText { style: root.style; objectName: "fantasySourceText"; visible: root.detail && dashboard.sportDetailPage === 3; x: 44; y: 552; width: 872; text: "Fonte " + dashboard.fantasyState.source + " · " + (dashboard.fantasyData.loading ? "Caricamento voti…" : dashboard.fantasyState.error || dashboard.fantasyData.cacheError || dashboard.fantasyData.warning || dashboard.fantasyData.liveNotice || (dashboard.fantasyState.updatedAt ? new Date(dashboard.fantasyState.updatedAt * 1000).toLocaleString(Qt.locale("it_IT"), "dd/MM hh:mm") + (dashboard.fantasyState.status === "offline" || dashboard.fantasyState.status === "stale" ? " · Dati salvati" : "") : dashboard.fantasyData.message || "Voti in attesa")); color: dashboard.fantasyState.error ? SemanticStyle.warning : root.style.textSecondary; font.pixelSize: root.style.font20; elide: Text.ElideRight }
    AppText { style: root.style; visible: root.detail && dashboard.sportDetailPage !== 3; x: 44; y: 552; width: 872; text: root.loading ? "Caricamento dettaglio…" : root.detailError || (root.match.detailFetchedAt ? "Fonte " + (root.match.provider === "fotmob" ? "FotMob" : "ESPN") + " · Dettaglio " + new Date(root.match.detailFetchedAt * 1000).toLocaleString(Qt.locale("it_IT"), "dd/MM hh:mm") + ((dashboard.sportTeamDetail ? dashboard.teamState.status : dashboard.sport.status) === "offline" || (dashboard.sportTeamDetail ? dashboard.teamState.status : dashboard.sport.status) === "stale" ? " · Dati salvati" : "") : "Dettaglio da aggiornare · 5 AGGIORNA"); color: root.detailError ? SemanticStyle.warning : root.style.textSecondary; font.pixelSize: root.style.font21; elide: Text.ElideRight }
    AppText { style: root.style; visible: settings; x: 44; y: 94; width: 872; text: "Serie A · seleziona la squadra e i riepiloghi desiderati."; color: root.style.textSecondary; font.pixelSize: root.style.font24 }
    Repeater {
        model: root.settings ? ["Squadra preferita", "Prossima Serie A in Home", "Notifiche gol", "Stagione", "Dati e aggiornamenti"] : []
        delegate: SelectableRow { style: root.style;
            required property string modelData
            required property int index
            x: 44; y: 140 + index * 65; width: 872; height: 58; radius: root.style.radiusRow
            color: index === dashboard.sportSettingsIndex ? root.style.surfaceFocused : root.style.surface
            border.color: index === dashboard.sportSettingsIndex ? root.style.accent : root.style.border
            border.width: index === dashboard.sportSettingsIndex ? root.style.focusWidth : root.style.hairlineWidth
            AppText { style: root.style; x: 18; anchors.verticalCenter: parent.verticalCenter; text: modelData; color: root.style.textPrimary; font.pixelSize: root.style.font28 }
            AppText { style: root.style; x: 476; width: 378; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignRight; text: root.settingValue(index); color: root.style.accent; font.pixelSize: root.style.font27; elide: Text.ElideRight }
        }
    }
    AppText { style: root.style; visible: settings; x: 44; y: 481; width: 872; text: dashboard.sportSettingsIndex === 4 ? "5 APRI DATI E AGGIORNAMENTI\nUn unico menu per aggiornare tutte le fonti." : dashboard.sportSettingsIndex === 2 ? "5 APRI NOTIFICHE / AVVISI A SCHERMO\nLe notifiche si regolano nel menu dedicato." : "2/8 SELEZIONA · 4/6 REGOLA · 5 CAMBIA\nPreferenze Serie A e Fantacalcio salvate sul dispositivo."; color: root.style.textSecondary; font.pixelSize: root.style.font22; lineHeight: 1.4 }
    AppText { style: root.style; x: 44; y: 592; text: root.detail ? dashboard.sportDetailPage === 3 ? "4/6 SCHEDE   ·   5 SQUADRA   ·   7 INDIETRO   ·   1 HOME" : "4/6 SCHEDE   ·   5 AGGIORNA   ·   7 INDIETRO   ·   1 HOME" : "7  INDIETRO      1  HOME"; color: root.style.accent; font.pixelSize: root.style.font23 }
}
