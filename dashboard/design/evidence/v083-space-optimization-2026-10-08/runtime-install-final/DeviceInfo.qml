import QtQuick
import "themes"
import "components"

Item {
    id: root
    property StyleFacade style: Theme
    required property var dashboard
    readonly property var backend: dashboard.dashboardState
    readonly property var snapshot: backend ? backend.systemState : ({data: {}})
    readonly property var infoData: snapshot.data || ({})
    readonly property var tabs: ["DISPOSITIVO", "RISORSE", "RETE", "DATI"]
    function row(title, value, detail, source) { return {title: title, value: value || "N/D", detail: detail || "", source: source || ""} }
    function provider(title, value, source) {
        const labels = {active: "Aggiornato", updating: "Aggiornamento…", offline: "Offline · dati salvati", stale: "Dati salvati", error: "Errore", unavailable: "Non disponibile"}
        return row(title, value ? labels[value.status] || "In attesa" : "Non disponibile", value ? value.source + (value.updatedAt ? " · " + dashboard.eventStamp(value.updatedAt) : " · nessun dato acquisito") : "", source)
    }
    readonly property var rows: dashboard.overlay !== "info" ? [] : dashboard.infoPage === 0 ? [
        row("Software", infoData.version, "Qt " + (infoData.qt || "—") + " · Python " + (infoData.python || "—")),
        row("Dispositivo", infoData.model, "Host " + (infoData.hostname || "—")),
        row("Sistema operativo", infoData.os, "Kernel " + (infoData.kernel || "—")),
        row("Display", infoData.display, infoData.graphics),
        row("Tastierino USB", dashboard.keypad && dashboard.keypad.connected ? "Collegato" : "Non collegato", "3 × 3 · riconnessione automatica"),
        row("Fuso orario", infoData.timezone, "Orari locali della dashboard")
    ] : dashboard.infoPage === 1 ? [
        row("Temperature", "CPU " + (infoData.cpuTemperature || "N/D") + " · GPU " + (infoData.gpuTemperature || "N/D"), "Misure attuali, non massimi storici"),
        row("CPU dashboard", infoData.appCpu, (infoData.cores || "—") + " core · carico 1/5/15 min: " + (infoData.load || "—")),
        row("RAM sistema", infoData.memoryUsage, infoData.memoryDetail),
        row("RAM dashboard", infoData.appMemory, "Picco " + (infoData.appMemoryPeak || "—") + " · swap sistema " + (infoData.swap || "—")),
        row("Archiviazione", infoData.storage, "Filesystem di sistema"),
        row("Continuità", "Dispositivo " + (infoData.uptime || "—"), "Processo " + (infoData.appUptime || "—") + " · PID " + (infoData.pid || "—"))
    ] : dashboard.infoPage === 2 ? [
        row("Connessione", infoData.network, "La rete locale non certifica l'accesso a Internet"),
        row("Indirizzo IP", infoData.ip, "Interfaccia " + (infoData.interface || "—")),
        row("Segnale Wi-Fi", infoData.wifiSignal, infoData.wifiSignalDetail),
        row("Account dal PC", root.backend ? "Sincronizzazione esterna" : "Non disponibile", "Ultimo dato " + dashboard.eventStamp(dashboard.account.updatedAt))
    ] : [
        provider("Meteo", dashboard.weather, "meteo"),
        row("Protezione Civile", dashboard.events.sourceStatus || "In attesa", "Controllo " + dashboard.eventStamp(dashboard.events.sourceCheckedAt), "alerts"),
        provider("Account ChatGPT", dashboard.account, "account"),
        provider("Casa / Smart Life", dashboard.casa, "casa"),
        provider("Rete / iliadbox", dashboard.network, "network")
    ].concat(backend && backend.sportAvailable ? [provider("Serie A", dashboard.sport, "sport")] : [])
        .concat(backend && backend.racingAvailable.indexOf("f1") >= 0 ? [provider("Formula 1", dashboard.racingStates.f1, "f1")] : [])
        .concat(backend && backend.racingAvailable.indexOf("motogp") >= 0 ? [provider("MotoGP", dashboard.racingStates.motogp, "motogp")] : [])
    readonly property int pageStart: Math.floor(dashboard.infoIndex / root.style.listRows) * root.style.listRows
    function changeTab(index) { dashboard.infoPage = index; dashboard.infoIndex = 0 }
    function handleKey(position) {
        if (dashboard.overlay !== "info") return false
        if (position === 4 || position === 6) changeTab(Math.max(0, Math.min(tabs.length - 1, dashboard.infoPage + (position === 4 ? -1 : 1))))
        else if (position === 2) dashboard.infoIndex = Math.max(0, dashboard.infoIndex - 1)
        else if (position === 8) dashboard.infoIndex = Math.min(rows.length - 1, dashboard.infoIndex + 1)
        return true
    }
    Rectangle { anchors.fill: parent; color: root.style.backgroundOverlay }
    AppText { style: root.style; renderType: Text.NativeRendering; x: 44; y: 30; text: "INFORMAZIONI"; color: root.style.accentTextOnOverlay; font.pixelSize: root.style.font37; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
    AppText { style: root.style; renderType: Text.NativeRendering; x: 605; y: 43; width: 310; horizontalAlignment: Text.AlignRight; text: "AGG. " + dashboard.eventStamp(snapshot.updatedAt); color: root.style.textSecondary; font.pixelSize: root.style.font20 }
    Repeater {
        model: root.tabs
        delegate: SelectableRow { style: root.style; selectedState: dashboard.infoPage === index;
            required property string modelData
            required property int index
            x: 44 + index * 221; y: 93; width: 209; height: 43; radius: root.style.radiusPill
            color: dashboard.infoPage === index ? root.style.surfaceFocused : root.style.surface
            border.color: dashboard.infoPage === index ? root.style.focusIndicator : root.style.border
            AppText { style: root.style; renderType: Text.NativeRendering; anchors.centerIn: parent; text: modelData; color: dashboard.infoPage === index ? root.style.accentTextOnFocused : root.style.textSecondary; font.pixelSize: root.style.font21; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
            MouseArea { anchors.fill: parent; onClicked: root.changeTab(index) }
        }
    }
    Repeater {
        model: root.rows.slice(root.pageStart, root.pageStart + root.style.listRows)
        delegate: SelectableRow { style: root.style; selectedState: rowIndex === dashboard.infoIndex;
            required property var modelData
            required property int index
            readonly property int rowIndex: root.pageStart + index
            objectName: "infoRow" + rowIndex
            x: 44; y: 153 + index * (332 / root.style.listRows); width: 872; height: 332 / root.style.listRows - 9; radius: root.style.radiusBadge
            color: rowIndex === dashboard.infoIndex ? root.style.surfaceFocused : root.style.surface
            border.color: rowIndex === dashboard.infoIndex ? root.style.focusIndicator : root.style.border
            AppText { style: root.style; renderType: Text.NativeRendering; x: 18; y: 9; width: 283; text: modelData.title; color: root.style.textSecondary; font.pixelSize: root.style.font24; elide: Text.ElideRight }
            AppText { style: root.style; renderType: Text.NativeRendering; x: 310; y: 9; width: 541; horizontalAlignment: Text.AlignRight; text: modelData.value; color: root.style.textPrimary; font.pixelSize: root.style.font26; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; elide: Text.ElideRight }
            AppText { style: root.style; renderType: Text.NativeRendering; x: 18; y: parent.height - 29; width: 832; text: modelData.detail; color: root.style.textSecondary; font.pixelSize: root.style.font19; elide: Text.ElideRight }
            MouseArea { anchors.fill: parent; onClicked: dashboard.infoIndex = parent.rowIndex }
        }
    }
    AppText { style: root.style; renderType: Text.NativeRendering; x: 44; y: 492; width: 872; text: dashboard.infoPage === 3 ? "Aggiornamenti manuali in Impostazioni › Dati e aggiornamenti" : "Misure automatiche ogni 5 s · qualità Wi-Fi ogni 30 s"; color: root.style.textSecondary; font.pixelSize: root.style.font20; elide: Text.ElideRight }
    AppText { style: root.style; renderType: Text.NativeRendering; x: 44; y: 521; width: 872; text: (dashboard.infoIndex + 1) + "/" + root.rows.length + " · 4/6 SCHEDA · 2/8 SCORRI"; color: root.style.textSecondary; font.pixelSize: root.style.font21 }
    Rectangle { x: 44; y: 548; width: 872; height: 1; color: root.style.border }
    KeyGuide { style: root.style; renderType: Text.NativeRendering; x: 44; y: 571; color: root.style.accentTextOnOverlay; font.pixelSize: root.style.font25 }
}
