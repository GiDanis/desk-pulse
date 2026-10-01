import QtQuick

Item {
    id: root
    required property var dashboard
    readonly property var entries: [
        {title: "Aspetto", detail: "Tema e animazioni", target: "appearance"},
        {title: "Luminosità", detail: "Livello manuale e fasce giorno / notte", target: "system"},
        {title: "Moduli visibili", detail: "Scegli gli argomenti del carosello", target: "modules"},
        {title: "Notifiche", detail: "Fascia silenzio e avvisi sullo schermo", target: "notifications"},
        {title: "Account ChatGPT", detail: "Soglie di utilizzo e avvisi", target: "accountSettings"},
        {title: "Sport", detail: "Squadra, stagioni e riepiloghi Home", target: "integrations"},
        {title: "Dati e aggiornamenti", detail: "Stato delle fonti e aggiornamento manuale", target: "sources"}
    ].filter(row => row.target !== "integrations" || dashboard.dashboardState &&
        (dashboard.dashboardState.sportAvailable || dashboard.dashboardState.racingAvailable.length))
    readonly property var targets: ["settings", "appearance", "system", "modules", "notifications", "notificationQuiet", "notificationCategories", "accountSettings", "integrations", "sources"]
    readonly property bool active: targets.indexOf(dashboard.overlay) >= 0
    readonly property var backend: dashboard.dashboardState
    readonly property string section: dashboard.overlay
    readonly property var sportEntries: (backend && backend.sportAvailable ? [{title: "Serie A e Fantacalcio", detail: "Squadra preferita, stagione, Home e gol", target: "sportSettings"}] : [])
        .concat(backend && backend.racingAvailable.indexOf("f1") >= 0 ? [{title: "Formula 1", detail: "Stagione e riepilogo Home", target: "f1"}] : [])
        .concat(backend && backend.racingAvailable.indexOf("motogp") >= 0 ? [{title: "MotoGP", detail: "Stagione e riepilogo Home", target: "motogp"}] : [])
    readonly property var sourceEntries: section === "sources" ? [
        {title: "Meteo", detail: sourceDetail(dashboard.weather), target: "meteo", value: "AGGIORNA"},
        {title: "Protezione Civile", detail: dashboard.events.sourceStatus || "In attesa", target: "alerts", value: "CONTROLLA"},
        {title: "Account ChatGPT", detail: "Sincronizzato dal PC · " + sourceDetail(dashboard.account), target: "account", value: "RILEGGI CACHE"}
    ].concat(backend && backend.sportAvailable ? [{title: "Serie A", detail: sourceDetail(dashboard.sport), target: "sport", value: "AGGIORNA"}] : [])
        .concat(backend && backend.racingAvailable.indexOf("f1") >= 0 ? [{title: "Formula 1", detail: sourceDetail(dashboard.racingStates.f1), target: "f1", value: "AGGIORNA"}] : [])
        .concat(backend && backend.racingAvailable.indexOf("motogp") >= 0 ? [{title: "MotoGP", detail: sourceDetail(dashboard.racingStates.motogp), target: "motogp", value: "AGGIORNA"}] : []) : []
    function sourceDetail(value) {
        if (!value) return "Non disponibile"
        const names = {active: "Aggiornato", updating: "Aggiornamento…", offline: "Offline · dati salvati", stale: "Dati salvati", error: "Errore", unavailable: "Non disponibile"}
        return (names[value.status] || "In attesa") + (value.updatedAt ? " · " + dashboard.eventStamp(value.updatedAt) : "")
    }
    readonly property bool quietActive: backend && backend.quietHoursEnabled &&
        (backend.quietStartMinute < backend.quietEndMinute
         ? currentMinute >= backend.quietStartMinute && currentMinute < backend.quietEndMinute
         : currentMinute >= backend.quietStartMinute || currentMinute < backend.quietEndMinute)
    readonly property int currentMinute: dashboard.now.getHours() * 60 + dashboard.now.getMinutes()
    readonly property string quietRange: backend ? dashboard.quietTime(backend.quietStartMinute) + " – " + dashboard.quietTime(backend.quietEndMinute) : "—"
    readonly property var notificationEntries: [
        {title: "Fascia silenzio", detail: backend && backend.quietHoursEnabled ? quietRange + " · " + (quietActive ? "silenzio in corso" : "fuori fascia") : "Disattivata · nessuna pausa oraria dei banner", target: "notificationQuiet"},
        {title: "Avvisi sullo schermo", detail: "Scegli quali categorie possono interrompere la vista", target: "notificationCategories"}
    ]
    readonly property var rows: !active ? [] : section === "settings" ? entries : section === "integrations" ? sportEntries : section === "sources" ? sourceEntries : section === "modules" ? dashboard.allFamilies.map(row => ({title: row.name, detail: row.id === "oggi" ? "La Home resta sempre disponibile" : "Nel carosello orizzontale", value: row.id === "oggi" ? "SEMPRE VISIBILE" : dashboard.visibleModules.indexOf(row.id) >= 0 ? "VISIBILE" : "NASCOSTO", enabled: row.id !== "oggi"})) : section === "appearance" ? [
        {title: "Tema", value: backend ? ({auto: "AUTOMATICO", day: "GIORNO", night: "NOTTE"})[backend.nightMode] : "—", detail: "Automatico segue gli orari di Luminosità"},
        {title: "Animazioni", value: backend && backend.animationsEnabled ? "ATTIVE" : "DISATTIVE", detail: "Transizioni tra argomenti e viste"}
    ] : section === "system" ? [
        {title: "Modalità", value: dashboard.systemValue(1), detail: "Automatico segue la fascia giorno / notte"},
        {title: "Livello manuale", value: dashboard.systemValue(2), detail: "Usato in modalità manuale", enabled: backend && backend.brightnessMode === "manual"},
        {title: "Livello giorno", value: dashboard.systemValue(3), detail: "Usato in modalità automatica", enabled: backend && backend.brightnessMode === "auto"},
        {title: "Livello notte", value: dashboard.systemValue(4), detail: "Usato in modalità automatica", enabled: backend && backend.brightnessMode === "auto"},
        {title: "Giorno dalle", value: dashboard.systemValue(5), detail: "Orario condiviso con il tema automatico"},
        {title: "Notte dalle", value: dashboard.systemValue(6), detail: "Orario condiviso con il tema automatico"}
    ] : section === "notifications" ? notificationEntries : section === "notificationQuiet" ? [
        {title: "Silenzio programmato", value: backend && backend.quietHoursEnabled ? "ATTIVO" : "DISATTIVO", detail: "Durante la fascia, i banner non compaiono", setting: 0},
        {title: "Dalle", value: dashboard.notificationValue(1), detail: "Inizio incluso · passi di 15 minuti", setting: 1, enabled: backend && backend.quietHoursEnabled},
        {title: "Alle", value: dashboard.notificationValue(2), detail: "Fine esclusa · passi di 15 minuti", setting: 2, enabled: backend && backend.quietHoursEnabled}
    ] : section === "notificationCategories" ? [
        {title: "Avvisi Meteo", value: backend && backend.weatherInterruptions ? "CONSENTITI" : "NASCOSTI", detail: "Banner e urgenti · scelta valida a qualsiasi ora", setting: 3},
        {title: "Avvisi Account", value: backend && backend.accountInterruptions ? "CONSENTITI" : "NASCOSTI", detail: "Banner e urgenti · scelta valida a qualsiasi ora", setting: 4}
    ].concat(backend && backend.sportAvailable ? [{title: "Notifiche gol", value: dashboard.sportData.liveVerified ? (dashboard.sportData.goalsEnabled ? "ATTIVE" : "DISATTIVE") : "DA COLLAUDARE", detail: dashboard.sportData.liveVerified ? "Banner della squadra preferita · rispettano la fascia silenzio" : "Disponibili dopo il collaudo durante una partita", sportSetting: 2, enabled: !!dashboard.sportData.liveVerified}] : []) : section === "accountSettings" ? [
        {title: "Avviso di utilizzo", value: dashboard.accountWarningPercent + "%", detail: "Prima soglia · voce nell'elenco Avvisi"},
        {title: "Utilizzo critico", value: dashboard.accountCriticalPercent + "%", detail: "Soglia superiore · banner secondo le Notifiche"}
    ] : []
    readonly property int selected: section === "settings" ? dashboard.settingsIndex : section === "modules" ? dashboard.modulesIndex : section === "system" ? dashboard.systemIndex : section === "notifications" ? dashboard.notificationIndex : section === "notificationQuiet" ? dashboard.quietIndex : section === "notificationCategories" ? dashboard.categoryIndex : section === "sources" ? dashboard.sourceIndex : dashboard.optionIndex
    readonly property int pageStart: Math.floor(selected / 4) * 4
    readonly property string heading: ({settings: "IMPOSTAZIONI", appearance: "ASPETTO", system: "LUMINOSITÀ", modules: "MODULI VISIBILI", notifications: "NOTIFICHE", notificationQuiet: "NOTIFICHE / FASCIA SILENZIO", notificationCategories: "NOTIFICHE / AVVISI A SCHERMO", accountSettings: "ACCOUNT CHATGPT", integrations: "SPORT", sources: "DATI E AGGIORNAMENTI"})[section] || ""
    readonly property string description: section === "system" ? "Regola l'immagine · livelli dal 20 al 100%, passi di 5%" : section === "sources" ? "Aggiornamento manuale · attesa minima 30 secondi tra richieste" : section === "notifications" ? "Due regole separate: quando interrompere e quali categorie" : section === "notificationQuiet" ? "Gli urgenti restano visibili per le categorie abilitate" : section === "notificationCategories" ? "Disattivare una categoria non cancella l'elenco Avvisi" : section === "accountSettings" ? "Preferenze salvate · soglie separate dall'acquisto di crediti" : "Preferenze salvate automaticamente"
    readonly property string explanation: section === "notifications" ? "Gli avvisi ricevuti restano consultabili da 3 AVVISI.\nLe soglie di utilizzo si regolano in Account ChatGPT." : section === "notificationQuiet" ? (backend && backend.quietHoursEnabled ? quietRange + " · " + (quietActive ? "silenzio in corso" : "fuori fascia") : "Fascia disattivata · nessuna pausa oraria") + "\nLe categorie disattivate restano nascoste anche fuori fascia." : section === "notificationCategories" ? "Meteo/Account consentiti: banner fuori fascia, urgenti sempre.\nMeteo/Account nascosti: restano nell'elenco 3 AVVISI." : ""
    property string feedback: ""
    onSectionChanged: feedback = ""

    function setSelected(index) {
        if (section === "settings") dashboard.settingsIndex = index
        else if (section === "modules") dashboard.modulesIndex = index
        else if (section === "system") dashboard.systemIndex = index
        else if (section === "notifications") dashboard.notificationIndex = index
        else if (section === "notificationQuiet") dashboard.quietIndex = index
        else if (section === "notificationCategories") dashboard.categoryIndex = index
        else if (section === "sources") dashboard.sourceIndex = index
        else dashboard.optionIndex = index
        feedback = ""
    }
    function activate(direction) {
        if (!backend || !rows.length) return
        const row = rows[selected]
        if (!row || row.enabled === false) return
        if (section === "settings") {
            dashboard.optionIndex = 0; dashboard.systemIndex = 0; dashboard.notificationIndex = 0
            dashboard.quietIndex = 0; dashboard.categoryIndex = 0; dashboard.sourceIndex = 0
            dashboard.modulesIndex = dashboard.allFamilies.length > 1 ? 1 : 0
            dashboard.pushOverlay(row.target)
        } else if (section === "integrations") {
            if (row.target === "sportSettings") { dashboard.sportSettingsIndex = 0; dashboard.pushOverlay("sportSettings") }
            else { dashboard.racingSettingsKind = row.target; dashboard.racingSettingsIndex = 0; dashboard.pushOverlay("racingSettings") }
        } else if (section === "notifications") dashboard.pushOverlay(row.target)
        else if (section === "notificationCategories" && row.sportSetting !== undefined) backend.adjustSportSetting(row.sportSetting, direction)
        else if (section === "sources") {
            const sent = backend.refreshSource(row.target)
            feedback = backend.demo ? "Demo · nessuna richiesta esterna" : !sent ? "Attendi 30 secondi prima di riprovare" : row.target === "account" ? "Cache riletta · gli aggiornamenti arrivano dal PC" : "Richiesta inviata · lo stato viene aggiornato dalla fonte"
        } else if (section === "appearance") {
            if (selected === 0) backend.adjustDisplaySetting(0, direction)
            else backend.toggleAnimations()
        } else if (section === "system") backend.adjustDisplaySetting(selected + 1, direction)
        else if (section === "modules") dashboard.toggleModule(selected)
        else if (section === "notificationQuiet" || section === "notificationCategories") backend.adjustNotificationSetting(row.setting, direction)
        else if (section === "accountSettings") backend.adjustAccountSetting(selected, direction)
    }
    function handleKey(position) {
        if (!active) return false
        const minimum = section === "modules" && rows.length > 1 ? 1 : 0
        if (position === 2) setSelected(Math.max(minimum, selected - 1))
        else if (position === 8) setSelected(Math.min(rows.length - 1, selected + 1))
        else if (position === 5 || (position === 4 || position === 6) && ["settings", "integrations", "notifications", "sources"].indexOf(section) < 0 && !rows[selected].target) activate(position === 4 ? -1 : 1)
        return true
    }
    Rectangle { anchors.fill: parent; color: "#0b1219" }
    Text { x: 44; y: root.rows.length <= 2 ? 334 : 410; width: 872; height: 66; visible: root.explanation !== ""; text: root.explanation; color: dashboard.muted; font.pixelSize: 22; lineHeight: 1.35 }
    Text { x: 44; y: 30; width: 872; text: root.heading; color: dashboard.accent; font.pixelSize: 37; font.bold: true }
    Text { x: 44; y: 84; width: 872; text: root.description; color: dashboard.muted; font.pixelSize: 22; elide: Text.ElideRight }
    Repeater {
        model: root.rows.slice(root.pageStart, root.pageStart + 4)
        delegate: Rectangle {
            required property var modelData
            required property int index
            readonly property int rowIndex: root.pageStart + index
            readonly property bool selectedRow: rowIndex === root.selected
            objectName: root.section + "Row" + rowIndex
            x: 44; y: 132 + index * 87; width: 872; height: 77; radius: 9
            color: selectedRow ? "#28403f" : dashboard.panel
            border.color: selectedRow ? dashboard.accent : dashboard.edge; border.width: selectedRow ? 3 : 1
            Text { x: 20; y: 10; width: 485; text: modelData.title; color: modelData.enabled === false ? dashboard.muted : dashboard.ink; font.pixelSize: 28; font.bold: selectedRow; elide: Text.ElideRight }
            Text { x: 20; y: 47; width: 825; text: modelData.detail || ""; color: dashboard.muted; font.pixelSize: 20; elide: Text.ElideRight }
            Text { x: 515; y: 13; width: 334; horizontalAlignment: Text.AlignRight; text: modelData.value || "›"; color: modelData.enabled === false ? dashboard.muted : selectedRow ? dashboard.accent : dashboard.ink; font.pixelSize: 25; font.bold: true; elide: Text.ElideRight }
            MouseArea { anchors.fill: parent; onClicked: { root.setSelected(parent.rowIndex); root.activate(1) } }
        }
    }
    Text { x: 44; y: 499; width: 872; text: root.feedback || (root.rows.length ? (root.selected + 1) + "/" + root.rows.length + " · " : "") + (root.section === "settings" || root.section === "integrations" || root.section === "notifications" || root.rows[root.selected] && root.rows[root.selected].target && root.section !== "sources" ? "2/8 SELEZIONA · 5 APRI" : root.section === "sources" ? "2/8 SELEZIONA · 5 AGGIORNA" : "2/8 SELEZIONA · 4/6 REGOLA · 5 CAMBIA"); color: dashboard.muted; font.pixelSize: 21; elide: Text.ElideRight }
    Rectangle { x: 44; y: 548; width: 872; height: 1; color: dashboard.edge }
    Text { x: 44; y: 571; text: "1 INDIETRO     7 HOME"; color: dashboard.accent; font.pixelSize: 25 }
}
