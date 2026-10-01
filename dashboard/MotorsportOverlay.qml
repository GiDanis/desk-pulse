import QtQuick

Item {
    id: root
    required property var dashboard
    readonly property bool settings: dashboard.overlay === "racingSettings"
    readonly property bool detail: dashboard.overlay === "racingSession"
    readonly property bool eventList: dashboard.overlay === "racingList"
    readonly property bool programme: dashboard.overlay === "racingEvent"
    readonly property bool table: dashboard.overlay === "racingTable"
    readonly property bool timing: dashboard.overlay === "racingTiming"
    readonly property bool driver: dashboard.overlay === "racingDriver"
    readonly property bool infoPage: driver || (programme && dashboard.racingEventPage > 0) || (detail && dashboard.racingDetailPage === 1) || (timing && dashboard.racingTimingPage > 0)
    readonly property var infoRows: driver ? dashboard.racingDriverRows : dashboard.racingInfoRows
    readonly property int infoIndex: driver ? dashboard.racingDriverIndex : dashboard.racingInfoIndex
    readonly property var tabs: root.table && dashboard.familyId === "f1" ? ["PILOTI", "COSTRUTTORI"] : root.detail ? ["RISULTATI", "SESSIONE"] : root.programme ? ["SESSIONI", "CIRCUITO", "RIEPILOGO"] : root.driver ? dashboard.racingDriverTabs : root.timing ? ["TEMPI", "PISTA", "DIREZIONE"] : []
    readonly property var racingInfo: settings ? ((dashboard.racingStates[dashboard.racingSettingsKind] || {}).data || ({})) : dashboard.racingData
    readonly property var event: dashboard.racingEvent
    readonly property var session: dashboard.racingSession
    readonly property var rows: timing ? ((racingInfo.live || {}).rows || []) : dashboard.racingRows
    readonly property int pageStart: Math.floor(Math.max(0, dashboard.racingIndex) / 3) * 3
    function settingValue(index) { return index === 0 ? "" + (racingInfo.selectedYear || racingInfo.year || "—") : index === 1 ? (racingInfo.showOnHome ? "ATTIVO" : "DISATTIVO") : "APRI" }
    function acquired(seconds) { return seconds ? new Date(seconds * 1000).toLocaleString(Qt.locale("it_IT"), "dd/MM hh:mm") : "" }
    function sourceFooter() {
        if (racingInfo.detailLoading) return "Aggiornamento…"
        if ((detail || programme) && racingInfo.detailErrorEventId === event.id && racingInfo.detailError) return racingInfo.detailError
        let source = timing || (driver && dashboard.racingDriverLive) ? (racingInfo.live || {}).source || dashboard.racing.source : detail || driver ? session.resultSource || dashboard.racing.source : dashboard.racing.source
        if (driver && !dashboard.racingDriverLive && dashboard.racingDriverPage > 0) source = dashboard.racingDriverPane === "GOMME" ? "OpenF1" : "Jolpica"
        let label = "Fonte " + source
        if (dashboard.racing.status === "offline" || dashboard.racing.status === "stale") label += " · dati salvati"
        if (table) return label + " · Classifica " + acquired(racingInfo.standingsAt) + (racingInfo.standingsRound ? " · GP " + racingInfo.standingsRound : racingInfo.standingsLabel ? " · " + racingInfo.standingsLabel : "")
        if (timing || (driver && dashboard.racingDriverLive)) return label + " · " + ((racingInfo.live || {}).isLive ? "Live" : "Tempi da verificare") + " · " + acquired((racingInfo.live || {}).dataAt || (racingInfo.live || {}).fetchedAt)
        if (driver) {
            let row = dashboard.racingDriver
            let at = dashboard.racingDriverPane === "SOSTE" ? row.pitsAt : dashboard.racingDriverPane === "GIRI" ? row.lapsAt : dashboard.racingDriverPane === "GOMME" ? row.stintsAt : session.resultsAt
            return at ? label + " · GP " + (event.round || "—") + " / " + (racingInfo.year || "") + " · " + acquired(at) : row.extraError || "Dettagli aggiuntivi non ancora disponibili"
        }
        if (detail) return label + (dashboard.racingDetailPage === 1 ? " · Sessione " + acquired(session.infoAt || session.resultsAt || racingInfo.fetchedAt) : session.resultsAt ? " · Risultati " + acquired(session.resultsAt) : "")
        return label + " · " + (programme ? "Programma " + acquired(event.programmeAt || racingInfo.fetchedAt) : "Calendario " + acquired(racingInfo.fetchedAt))
    }
    Rectangle { anchors.fill: parent; color: dashboard.color }
    Text { x: 44; y: 29; width: 872; text: settings ? "IMPOSTAZIONI · " + (dashboard.racingSettingsKind === "f1" ? "F1" : "MOTOGP") : driver ? dashboard.racingDriverLive ? "TEMPI DEL PILOTA" : (root.session.name || "SESSIONE").toUpperCase() + " · DETTAGLI PILOTA" : table ? "CLASSIFICA · " + (racingInfo.year || "") : timing ? "TEMPI DELLA SESSIONE" : detail ? (root.session.name || "SESSIONE") : eventList ? "CALENDARIO · " + (racingInfo.year || "") : "PROGRAMMA DEL WEEKEND"; color: dashboard.accent; font.pixelSize: driver ? 30 : 35; font.bold: true; elide: Text.ElideRight }
    Text { visible: !settings && !table && !eventList; x: 44; y: 85; width: 872; text: driver ? dashboard.racingDriver.name || "Pilota non più presente nel feed" : timing ? ((racingInfo.live || {}).meeting || "") : root.event.name || ""; color: dashboard.ink; font.pixelSize: 29; elide: Text.ElideRight }
    Text { visible: eventList; x: 44; y: 88; text: dashboard.racingView === "RISULTATI" ? "GP CONCLUSI · 5 RISULTATI DELLE SESSIONI" : "TUTTI I GP · 5 APRI IL WEEKEND"; color: dashboard.muted; font.pixelSize: 23 }
    Repeater {
        model: root.tabs
        delegate: Rectangle {
            required property string modelData
            required property int index
            readonly property bool selected: index === (root.table ? dashboard.racingStandingTab : root.programme ? dashboard.racingEventPage : root.driver ? dashboard.racingDriverPage : root.timing ? dashboard.racingTimingPage : dashboard.racingDetailPage)
            x: 44 + index * (884 / root.tabs.length); y: root.table ? 83 : 133; width: 884 / root.tabs.length - 12; height: 43; radius: 7; color: selected ? "#28403f" : dashboard.panel; border.color: selected ? dashboard.accent : dashboard.edge
            Text { anchors.centerIn: parent; text: modelData; color: selected ? dashboard.accent : dashboard.muted; font.pixelSize: root.tabs.length > 2 ? 22 : 24; font.bold: selected }
        }
    }
    Text { visible: table && dashboard.familyId !== "f1"; x: 44; y: 90; text: "PILOTI · " + (racingInfo.standingsLabel ? "DOPO " + racingInfo.standingsLabel : "CLASSIFICA DELLA STAGIONE"); color: dashboard.muted; font.pixelSize: 24 }
    Repeater {
        model: !root.settings && !root.detail && !root.infoPage ? root.rows.slice(root.pageStart, root.pageStart + 3) : []
        delegate: Rectangle {
            required property var modelData
            required property int index
            readonly property bool selected: root.pageStart + index === dashboard.racingIndex
            x: 44; y: (root.programme || root.timing ? 195 : 148) + index * (root.programme || root.timing ? 97 : 111); width: 872; height: root.programme || root.timing ? 85 : 96; radius: 9
            color: selected ? "#28403f" : dashboard.panel; border.color: selected ? dashboard.accent : dashboard.edge; border.width: selected ? 3 : 1
            Text { x: 18; y: 12; width: root.table || root.timing ? 670 : 827; text: root.table || root.timing ? (modelData.position || "—") + ".  " + modelData.name : modelData.name || ""; color: dashboard.ink; font.pixelSize: 29; font.bold: true; elide: Text.ElideRight }
            Text { x: 18; y: 57; width: 827; text: root.table || root.timing ? modelData.team || "" : root.programme ? (modelData.when || "") + " · " + (modelData.statusText || "") : (modelData.when || "") + " · " + (modelData.circuit || ""); color: dashboard.muted; font.pixelSize: 22; elide: Text.ElideRight }
            Text { visible: root.table || root.timing; x: 688; y: 29; width: 167; horizontalAlignment: Text.AlignRight; text: modelData.value || "—"; color: dashboard.accent; font.pixelSize: 29; font.bold: true; elide: Text.ElideRight }
        }
    }
    Text { visible: !settings && !detail && !infoPage && !root.rows.length; x: 44; y: 210; width: 872; text: root.programme ? "Programma non ancora pubblicato.\nAggiorna da Impostazioni › Dati e aggiornamenti." : "Dati non disponibili"; color: dashboard.muted; font.pixelSize: 29; wrapMode: Text.WordWrap }
    Text { visible: !settings && !detail && !infoPage; x: 44; y: 502; width: 872; text: root.rows.length ? (dashboard.racingIndex + 1) + "/" + root.rows.length + " · 2/8 SCORRI" + (root.eventList || root.programme || root.timing ? " · 5 APRI" : root.table && dashboard.familyId === "f1" ? " · 4/6 PILOTI / COSTRUTTORI" : "") : ""; color: dashboard.muted; font.pixelSize: 23 }
    Item {
        visible: root.detail; x: 44; y: 195; width: 872; height: 332
        readonly property int resultStart: Math.floor(dashboard.racingResultIndex / 3) * 3
        Repeater {
            model: dashboard.racingDetailPage === 0 ? (root.session.results || []).slice(parent.resultStart, parent.resultStart + 3) : []
            delegate: Rectangle {
                required property var modelData
                required property int index
                x: 0; y: index * 97; width: 872; height: 85; radius: 8; color: dashboard.panel; border.color: parent.resultStart + index === dashboard.racingResultIndex ? dashboard.accent : dashboard.edge; border.width: 2
                Text { x: 18; y: 10; width: 644; text: (modelData.position || "—") + ".  " + modelData.name; color: dashboard.ink; font.pixelSize: 29; font.bold: true; elide: Text.ElideRight }
                Text { x: 18; y: 51; width: 642; text: (modelData.team || "") + (modelData.laps !== null && modelData.laps !== undefined ? " · " + modelData.laps + " giri" : ""); color: dashboard.muted; font.pixelSize: 21; elide: Text.ElideRight }
                Text { x: 668; y: 28; width: 186; horizontalAlignment: Text.AlignRight; text: modelData.value || "—"; color: dashboard.accent; font.pixelSize: 28; elide: Text.ElideRight }
            }
        }
        Text {
            objectName: "racingEmptyResult"; visible: dashboard.racingDetailPage === 0 && !(root.session.results || []).length
            x: 0; y: 43; width: 872; color: dashboard.muted; font.pixelSize: 29; wrapMode: Text.WordWrap
            text: root.racingInfo.detailLoading ? "Caricamento risultati…" : root.session.start && root.session.start > Date.now() / 1000 ? "La sessione deve ancora iniziare.\nI risultati compariranno dopo la pubblicazione." : root.session.extraError || (dashboard.familyId === "f1" && ["RAC", "Q", "SPR"].indexOf(root.session.kind) < 0 ? "Risultati OpenF1 disponibili dopo la sessione\ne dopo la chiusura della finestra live." : "Risultati non ancora disponibili dalla fonte.")
        }
        Text { visible: dashboard.racingDetailPage === 0 && (root.session.results || []).length; y: 307; width: 872; text: (dashboard.racingResultIndex + 1) + "/" + (root.session.results || []).length + " · 2/8 SCORRI · 5 DETTAGLI PILOTA"; color: dashboard.muted; font.pixelSize: 22 }
    }
    Item {
        visible: root.infoPage; x: 44; y: 195; width: 872; height: 340
        readonly property int start: Math.floor(root.infoIndex / 3) * 3
        Repeater {
            model: root.infoPage ? root.infoRows.slice(parent.start, parent.start + 3) : []
            delegate: Rectangle {
                required property var modelData
                required property int index
                x: 0; y: index * 97; width: 872; height: 85; radius: 8; color: dashboard.panel; border.color: parent.start + index === root.infoIndex ? dashboard.accent : dashboard.edge
                Text { x: 18; y: 7; width: 835; text: modelData.label; color: dashboard.muted; font.pixelSize: 20; elide: Text.ElideRight }
                Text { x: 18; y: 32; width: 835; height: 49; text: modelData.value; color: dashboard.ink; font.pixelSize: root.timing && dashboard.racingTimingPage === 2 ? 22 : 26; wrapMode: root.timing && dashboard.racingTimingPage === 2 ? Text.WordWrap : Text.NoWrap; maximumLineCount: 2; elide: Text.ElideRight }
            }
        }
        Text { objectName: "racingDetailEmpty"; visible: !root.infoRows.length; x: 0; y: 42; width: 872; text: racingInfo.detailLoading ? "Caricamento…" : root.driver && dashboard.racingDriverPane === "SOSTE" && dashboard.racingDriver.pitStops !== undefined ? "Nessuna sosta pubblicata per questo pilota." : root.programme && dashboard.racingEventPage === 2 ? "Il riepilogo comparirà dopo la pubblicazione\ndei risultati delle sessioni." : "Informazioni non disponibili dalla fonte."; color: dashboard.muted; font.pixelSize: 29; wrapMode: Text.WordWrap }
        Text { y: 307; width: 872; text: root.infoRows.length ? (root.infoIndex + 1) + "/" + root.infoRows.length + " · 2/8 SCORRI" + (root.driver && dashboard.racingDriverPane === "GIRI" && dashboard.racingDriver.lapTimesPartial ? " · ELENCO PARZIALE" : "") : ""; color: dashboard.muted; font.pixelSize: 22 }
    }
    Repeater {
        model: root.settings ? ["Stagione", "Prossima gara in Home", "Dati e aggiornamenti"] : []
        delegate: Rectangle {
            required property string modelData
            required property int index
            x: 44; y: 136 + index * 88; width: 872; height: 75; radius: 9; color: index === dashboard.racingSettingsIndex ? "#28403f" : dashboard.panel; border.color: index === dashboard.racingSettingsIndex ? dashboard.accent : dashboard.edge; border.width: 2
            Text { x: 18; anchors.verticalCenter: parent.verticalCenter; text: modelData; color: dashboard.ink; font.pixelSize: 29 }
            Text { x: 580; width: 274; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignRight; text: root.settingValue(index); color: dashboard.accent; font.pixelSize: 28 }
        }
    }
    Text { visible: settings; x: 44; y: 427; width: 872; text: dashboard.racingSettingsIndex === 2 ? "5 APRI DATI E AGGIORNAMENTI\nUn unico menu per aggiornare tutte le fonti." : "2/8 SELEZIONA · 4/6 REGOLA · 5 CAMBIA\nCalendario, risultati e classifiche salvati sul dispositivo."; color: dashboard.muted; font.pixelSize: 23; lineHeight: 1.4 }
    Text { objectName: "racingFooter"; visible: !settings; x: 44; y: 551; width: 872; text: root.sourceFooter(); color: dashboard.muted; font.pixelSize: 21; elide: Text.ElideRight }
    Text { x: 44; y: 592; text: (root.tabs.length > 1 ? "4/6 SCHEDE · " : "") + (root.driver && !dashboard.racingDriverLive || root.detail && dashboard.racingDetailPage === 1 || root.programme && dashboard.racingEventPage > 0 ? "5 AGGIORNA · " : "") + "1 INDIETRO · 7 HOME"; color: dashboard.accent; font.pixelSize: 23 }
}
