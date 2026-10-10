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
    Rectangle {anchors.fill:parent;color:root.style.background}
    Rectangle {anchors.fill:parent;color:root.style.backgroundOverlay}
    AppText {style:root.style;x:24;y:13;text:"Informazioni";color:root.style.textPrimary;font.pixelSize:root.style.font31}
    AppText {style:root.style;x:606;y:18;width:330;horizontalAlignment:Text.AlignRight;text:dashboard.eventStamp(snapshot.updatedAt);color:root.style.textSecondary;font.pixelSize:root.style.font20}
    Rectangle {x:24;y:55;width:912;height:1;color:root.style.border}
    Repeater {model:root.tabs
        delegate:SelectableRow {
            required property string modelData
            required property int index
            style:root.style;selectedState:dashboard.infoPage===index
            x:24+index*231;y:72;width:219;height:44;radius:root.style.radiusPill
            color:selectedState ? root.style.surfaceFocused : root.style.surface
            border.color:selectedState ? root.style.focusIndicator : root.style.border
            AppText {style:root.style;anchors.centerIn:parent;text:modelData;color:root.style.textPrimary;font.pixelSize:root.style.font21;font.weight:root.style.headingWeight}
            MouseArea {anchors.fill:parent;onClicked:root.changeTab(parent.index)}
        }
    }
    GridView {
        id:infoGrid
        objectName:"infoGrid"
        x:24;y:132;width:924;height:492;clip:true;boundsBehavior:Flickable.StopAtBounds
        model:root.rows;currentIndex:dashboard.infoIndex
        cellWidth:462;cellHeight:Math.max(168,Math.round(160*root.style.textScale))
        onCurrentIndexChanged:Qt.callLater(function(){infoGrid.positionViewAtIndex(infoGrid.currentIndex,GridView.Contain)})
        onCountChanged:Qt.callLater(function(){infoGrid.positionViewAtIndex(infoGrid.currentIndex,GridView.Contain)})
        delegate:SelectableRow {
            required property var modelData
            required property int index
            style:root.style;selectedState:index===dashboard.infoIndex
            objectName:"infoRow"+index
            width:450;height:infoGrid.cellHeight-12;radius:root.style.radiusCard
            color:selectedState ? root.style.surfaceFocused : root.style.surface
            border.color:selectedState ? root.style.focusIndicator : root.style.border
            border.width:selectedState ? root.style.focusWidth : root.style.hairlineWidth
            AppText {style:root.style;x:18;y:9;width:414;text:modelData.title;color:root.style.textSecondary;font.pixelSize:root.style.font24;elide:Text.ElideRight}
            AppText {style:root.style;x:18;y:43;width:414;height:66;text:modelData.value;color:root.style.textPrimary;font.pixelSize:dashboard.infoPage===1 ? root.style.font32 : root.style.font26;font.weight:root.style.headingWeight;wrapMode:Text.WordWrap;maximumLineCount:2;elide:Text.ElideRight}
            AppText {style:root.style;x:18;y:parent.height-45;width:414;height:40;text:modelData.detail;color:root.style.textSecondary;font.pixelSize:root.style.font19;wrapMode:Text.WordWrap;maximumLineCount:2;elide:Text.ElideRight}
            MouseArea {anchors.fill:parent;onClicked:dashboard.infoIndex=parent.index}
        }
        Rectangle {x:908;width:4;y:infoGrid.visibleArea.yPosition*infoGrid.height;height:Math.max(18,infoGrid.visibleArea.heightRatio*infoGrid.height);radius:2;color:root.style.accent;visible:infoGrid.contentHeight>infoGrid.height;opacity:0.65}
    }
}
