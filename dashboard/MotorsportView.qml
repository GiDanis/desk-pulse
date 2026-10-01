import QtQuick

Item {
    id: root
    required property var dashboard
    readonly property var moduleInfo: dashboard.racing
    readonly property var racingInfo: dashboard.racingData
    readonly property string view: dashboard.racingView
    readonly property var event: view === "RISULTATI" ? racingInfo.lastEvent || ({}) : racingInfo.nextEvent || ({})
    readonly property var sessions: racingInfo.nextSessions || []
    readonly property var lastRace: (event.sessions || []).find(s => s.kind === "RAC") || ({})
    readonly property var rows: view === "CLASSIFICA" ? (racingInfo.standings || []).slice(0, 3) : view === "IN CORSO" ? ((racingInfo.live || {}).rows || []).slice(0, 3) : view === "RISULTATI" ? (lastRace.results || []).slice(0, 3) : sessions.slice(0, 3)
    function stamp(seconds) { return seconds ? new Date(seconds * 1000).toLocaleString(Qt.locale("it_IT"), "dd/MM hh:mm") : "—" }
    function status() {
        if (view === "IN CORSO") return (racingInfo.live || {}).active ? "TEMPI " + stamp((racingInfo.live || {}).dataAt || (racingInfo.live || {}).fetchedAt) : "TEMPI PRECEDENTI"
        if (moduleInfo.status === "offline") return "OFFLINE · DATI SALVATI"
        if (moduleInfo.status === "stale") return "DATI PRECEDENTI"
        if (moduleInfo.status === "error") return "DATI NON DISPONIBILI"
        if (moduleInfo.status === "updating") return "AGGIORNAMENTO"
        if (moduleInfo.status === "unavailable") return "CARICAMENTO"
        return "VERIFICATO " + stamp(moduleInfo.updatedAt)
    }
    Rectangle { width: 872; height: 76; radius: 9; color: dashboard.panel; border.color: dashboard.edge }
    Text { x: 18; y: 9; text: (dashboard.familyId === "f1" ? "FORMULA 1" : "MOTOGP") + " · " + (racingInfo.selectedYear || racingInfo.year || ""); color: dashboard.ink; font.pixelSize: 27; font.bold: true }
    Text { objectName: "racingSourceText"; x: 18; y: 43; width: 370; text: "Fonte: " + (view === "IN CORSO" ? (racingInfo.live || {}).source || moduleInfo.source : moduleInfo.source); color: dashboard.muted; font.pixelSize: 21 }
    Text { x: 397; y: 15; width: 455; horizontalAlignment: Text.AlignRight; text: root.status(); color: view === "IN CORSO" ? ((racingInfo.live || {}).active ? dashboard.accent : "#efbd75") : (moduleInfo.status === "active" || moduleInfo.status === "updating" ? dashboard.accent : "#efbd75"); font.pixelSize: 21; font.bold: true }
    Text { x: 397; y: 45; width: 455; horizontalAlignment: Text.AlignRight; text: racingInfo.cacheError || "Orari italiani · Europe/Rome"; color: dashboard.muted; font.pixelSize: 19 }
    Text {
        x: 0; y: 93; width: 872; elide: Text.ElideRight
        text: view === "CLASSIFICA" ? "CLASSIFICA PILOTI" : view === "IN CORSO" ? (racingInfo.live || {}).meeting || "SESSIONE IN CORSO" : event.name || (view === "RISULTATI" ? "Nessun risultato disponibile" : "Nessun prossimo GP disponibile")
        color: dashboard.accent; font.pixelSize: 31; font.bold: true
    }
    Text {
        x: 0; y: 135; width: 872; color: dashboard.muted; font.pixelSize: 23; elide: Text.ElideRight
        text: view === "CLASSIFICA" ? (racingInfo.standingsRound ? "Dopo il GP " + racingInfo.standingsRound : racingInfo.standingsLabel ? "Ultima classifica: " + racingInfo.standingsLabel : "Classifica della stagione") :
              view === "IN CORSO" ? (racingInfo.live || {}).name + " · " + ((racingInfo.live || {}).isLive ? "LIVE" : "feed da collaudare") : event.circuit || ""
    }
    Repeater {
        model: root.rows
        delegate: Rectangle {
            required property var modelData
            required property int index
            x: 0; y: 181 + index * 70; width: 872; height: 60; radius: 8; color: dashboard.panel; border.color: dashboard.edge
            Text { x: 16; y: 7; width: 639; text: root.view === "PROGRAMMA" ? modelData.name : (modelData.position || "—") + ".  " + modelData.name; color: dashboard.ink; font.pixelSize: 27; font.bold: true; elide: Text.ElideRight }
            Text { x: 16; y: 38; width: 635; text: root.view === "PROGRAMMA" ? modelData.when : modelData.team || ""; color: dashboard.muted; font.pixelSize: 18; elide: Text.ElideRight }
            Text { x: 663; y: 15; width: 190; horizontalAlignment: Text.AlignRight; text: root.view === "PROGRAMMA" ? "" : modelData.value || "—"; color: dashboard.accent; font.pixelSize: 29; font.bold: true; elide: Text.ElideRight }
        }
    }
    Text {
        visible: !root.rows.length; x: 0; y: 191; width: 872; height: 136; color: dashboard.ink; font.pixelSize: 29; wrapMode: Text.WordWrap
        text: moduleInfo.error || (view === "PROGRAMMA" ? (event.id ? "Weekend " + event.when + "\nProgramma delle sessioni non ancora pubblicato." : "Calendario in aggiornamento") : view === "IN CORSO" ? "La sessione è terminata o il feed non è più aggiornato." : "Apri il GP per consultare i risultati delle sessioni.")
    }
    Text {
        x: 0; y: 409; width: 872; color: dashboard.muted; font.pixelSize: 22; elide: Text.ElideRight
        text: view === "CLASSIFICA" ? (dashboard.familyId === "f1" ? "5 PILOTI / COSTRUTTORI" : "5 TUTTI I PILOTI") : view === "IN CORSO" ? "5 TUTTI I TEMPI · " + (((racingInfo.live || {}).lap || "—") + "/" + ((racingInfo.live || {}).totalLaps || "—") + " giri") : view === "PROGRAMMA" ? (root.lastRace.start ? "Gara · " + root.lastRace.when : "Weekend · " + (event.when || "Da confermare")) + " · 5 WEEKEND" : "5 GARA, QUALIFICHE E SPRINT"
    }
}
