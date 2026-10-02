import QtQuick
import "themes"
import "components"

Item {
    id: root
    property StyleFacade style: Theme
    required property var dashboard
    readonly property var moduleInfo: dashboard.racing
    readonly property var racingInfo: dashboard.racingData
    readonly property string view: dashboard.racingView
    readonly property var event: view === "RISULTATI" ? racingInfo.lastEvent || ({}) : racingInfo.nextEvent || ({})
    readonly property var sessions: racingInfo.nextSessions || []
    readonly property var lastRace: (event.sessions || []).find(s => s.kind === "RAC") || ({})
    readonly property var rows: view === "CLASSIFICA" ? (racingInfo.standings || []).slice(0, root.style.overviewRows) : view === "IN CORSO" ? ((racingInfo.live || {}).rows || []).slice(0, root.style.overviewRows) : view === "RISULTATI" ? (lastRace.results || []).slice(0, root.style.overviewRows) : sessions.slice(0, root.style.overviewRows)
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
    Rectangle { width: 872; height: 76; radius: root.style.radiusRow; color: root.style.surface; border.color: root.style.border }
    AppText { style: root.style; x: 18; y: 9; text: (dashboard.familyId === "f1" ? "FORMULA 1" : "MOTOGP") + " · " + (racingInfo.selectedYear || racingInfo.year || ""); color: root.style.textPrimary; font.pixelSize: root.style.font27; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
    AppText { style: root.style; objectName: "racingSourceText"; x: 18; y: 43; width: 370; text: "Fonte: " + (view === "IN CORSO" ? (racingInfo.live || {}).source || moduleInfo.source : moduleInfo.source); color: root.style.textSecondary; font.pixelSize: root.style.font21 }
    AppText { style: root.style; x: 397; y: 15; width: 455; horizontalAlignment: Text.AlignRight; text: root.status(); color: view === "IN CORSO" ? ((racingInfo.live || {}).active ? root.style.accent : SemanticStyle.warning) : (moduleInfo.status === "active" || moduleInfo.status === "updating" ? root.style.accent : SemanticStyle.warning); font.pixelSize: root.style.font21; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
    AppText { style: root.style; x: 397; y: 45; width: 455; horizontalAlignment: Text.AlignRight; text: racingInfo.cacheError || "Orari italiani · Europe/Rome"; color: root.style.textSecondary; font.pixelSize: root.style.font19 }
    AppText { style: root.style;
        x: 0; y: 93; width: 872; elide: Text.ElideRight
        text: view === "CLASSIFICA" ? "CLASSIFICA PILOTI" : view === "IN CORSO" ? (racingInfo.live || {}).meeting || "SESSIONE IN CORSO" : event.name || (view === "RISULTATI" ? "Nessun risultato disponibile" : "Nessun prossimo GP disponibile")
        color: root.style.accent; font.pixelSize: root.style.font31; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight
    }
    AppText { style: root.style;
        x: 0; y: 135; width: 872; color: root.style.textSecondary; font.pixelSize: root.style.font23; elide: Text.ElideRight
        text: view === "CLASSIFICA" ? (racingInfo.standingsRound ? "Dopo il GP " + racingInfo.standingsRound : racingInfo.standingsLabel ? "Ultima classifica: " + racingInfo.standingsLabel : "Classifica della stagione") :
              view === "IN CORSO" ? (racingInfo.live || {}).name + " · " + ((racingInfo.live || {}).isLive ? "LIVE" : "feed da collaudare") : event.circuit || ""
    }
    Repeater {
        model: root.rows
        delegate: Rectangle {
            required property var modelData
            required property int index
            x: 0; y: 181 + index * 70; width: 872; height: 60; radius: root.style.radiusBadge; color: root.style.surface; border.color: root.style.border
            AppText { style: root.style; x: 16; y: 7; width: 639; text: root.view === "PROGRAMMA" ? modelData.name : (modelData.position || "—") + ".  " + modelData.name; color: root.style.textPrimary; font.pixelSize: root.style.font27; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; elide: Text.ElideRight }
            AppText { style: root.style; x: 16; y: 38; width: 635; text: root.view === "PROGRAMMA" ? modelData.when : modelData.team || ""; color: root.style.textSecondary; font.pixelSize: root.style.font18; elide: Text.ElideRight }
            AppText { style: root.style; x: 663; y: 15; width: 190; horizontalAlignment: Text.AlignRight; text: root.view === "PROGRAMMA" ? "" : modelData.value || "—"; color: root.style.accent; font.pixelSize: root.style.font29; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; elide: Text.ElideRight }
        }
    }
    AppText { style: root.style;
        visible: !root.rows.length; x: 0; y: 191; width: 872; height: 136; color: root.style.textPrimary; font.pixelSize: root.style.font29; wrapMode: Text.WordWrap
        text: moduleInfo.error || (view === "PROGRAMMA" ? (event.id ? "Weekend " + event.when + "\nProgramma delle sessioni non ancora pubblicato." : "Calendario in aggiornamento") : view === "IN CORSO" ? "La sessione è terminata o il feed non è più aggiornato." : "Apri il GP per consultare i risultati delle sessioni.")
    }
    AppText { style: root.style;
        x: 0; y: 409; width: 872; color: root.style.textSecondary; font.pixelSize: root.style.font22; elide: Text.ElideRight
        text: view === "CLASSIFICA" ? (dashboard.familyId === "f1" ? "5 PILOTI / COSTRUTTORI" : "5 TUTTI I PILOTI") : view === "IN CORSO" ? "5 TUTTI I TEMPI · " + (((racingInfo.live || {}).lap || "—") + "/" + ((racingInfo.live || {}).totalLaps || "—") + " giri") : view === "PROGRAMMA" ? (root.lastRace.start ? "Gara · " + root.lastRace.when : "Weekend · " + (event.when || "Da confermare")) + " · 5 WEEKEND" : "5 GARA, QUALIFICHE E SPRINT"
    }
}
