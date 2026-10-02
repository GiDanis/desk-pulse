import QtQuick
import "themes"
import "components"

Item {
    id: root
    property StyleFacade style: Theme
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
    readonly property var rows: !active ? [] : section === "settings" ? entries : section === "integrations" ? sportEntries : section === "sources" ? sourceEntries : section === "modules" ? dashboard.allFamilies.map(row => ({title: row.name, detail: row.id === "oggi" ? "La Home resta sempre disponibile" : "Nel carosello orizzontale", value: row.id === "oggi" ? "SEMPRE VISIBILE" : dashboard.visibleModules.indexOf(row.id) >= 0 ? "VISIBILE" : "NASCOSTO", enabled: row.id !== "oggi"})) : section === "appearance" ? appearanceRows
 : section === "system" ? [
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
    readonly property var themeService: backend ? backend.appearance : null
    readonly property var homePresentations: Object.keys(Theme.appearance.presentationRegistry).filter(id => Theme.appearance.presentationRegistry[id].contentIds.indexOf("home.now") >= 0)
    readonly property var navigationRecipes: Object.keys(Theme.appearance.motionRegistry).filter(id => (Theme.appearance.motionRegistry[id].events || []).indexOf("navigate.family") >= 0)
    function presentationName(id) { return (Theme.appearance.presentationRegistry[id] || {}).name || id }
    function recipeName(id) { return (Theme.appearance.motionRegistry[id] || {}).name || id }
    readonly property var appearanceRows: themeService ? [
        {title: "Palette", value: ({auto:"AUTOMATICA",day:"GIORNO",night:"NOTTE"})[themeService.draft.paletteMode || "auto"], detail: "Bozza · segue gli orari di Luminosità in automatico"},
        {title: "Movimento", value: ({normal:"NORMALE",reduced:"RIDOTTO",off:"DISATTIVO"})[themeService.draft.motionMode], detail: "Transizioni e scena rispettano la stessa policy"},
        {title: "Tema", value: (themeService.themes.find(t => t.id === themeService.draft.themeId) || {}).name || themeService.draft.themeId, detail: "Preset e pacchetti personali nel catalogo"},
        {title: "Composizione Home", value: presentationName(Theme.presentations["home.now"]), detail: "Stessi dati · disposizione a sinistra o centrata"},
        {title: "Dimensione testo", value: Math.round(root.style.textScale * 100) + "%", detail: "Da 85 a 110% · ogni stile conserva i propri ruoli"},
        {title: "Densità", value: root.style.listRows === 4 ? "REGOLARE" : "AMPIA", detail: "Paginazione coerente anche in Sport e Motorsport"},
        {title: "Angoli delle schede", value: root.style.radiusCard + " px", detail: "Da 0 a 24 · passi di 2 pixel"},
        {title: "Colore accento", value: root.style.accent.toString(), detail: "I colori degli avvisi ufficiali restano riconoscibili"},
        {title: "Carattere interfaccia", value: root.style.uiFamily || "PREDEFINITO", detail: "Famiglie disponibili nel sistema · caricate su richiesta"},
        {title: "Carattere numeri", value: root.style.numbersFamily || "PREDEFINITO", detail: "Orologi e dati numerici · indipendente dall'interfaccia"},
        {title: "Transizioni", value: recipeName((Theme.motion["navigate.family"] || {}).recipe) || "—", detail: "Scorrimento, dissolvenza o cambio immediato"},
        {title: "Scena di prova", value: Theme.appearance && Theme.appearance.scene.enabled ? "ATTIVA" : "DISATTIVA", detail: "Attore geometrico persistente · si sospende con avvisi e notte"},
        {title: "Applica e salva", value: themeService.status === "saving" ? "SALVATAGGIO…" : "SALVA", detail: "La bozza diventa la preferenza al prossimo avvio", enabled: themeService.readyToApply},
        {title: "Annulla bozza", value: "RIPRISTINA", detail: "Torna all'ultimo aspetto salvato", enabled: themeService.status !== "saving"},
        {title: "Ripristina Base", value: "BOZZA", detail: "Azzera solo la personalizzazione dell'aspetto"},
        {title: "Rileggi catalogo", value: "AGGIORNA", detail: "Pacchetti importati · errori visibili, Base sempre disponibile"},
        {title: "Carattere orologio", value: root.style.displayFamily || "PREDEFINITO", detail: "Famiglia del display grande · indipendente da testo e numeri"},
        {title: "Importa pacchetti", value: "IMPORTA", detail: "Cartella theme-imports · contenuti locali validati"},
        {title: "Esporta personalizzazione", value: "ESPORTA", detail: "Cartella theme-exports · include font e risorse del pacchetto"}
    ] : []
    function cycle(values, current, direction) {
        return values[(Math.max(0, values.indexOf(current)) + direction + values.length) % values.length]
    }
    function editAppearance(direction) {
        const service = themeService
        if (!service || (service.status === "saving" || service.status === "working")) return
        if (!service.editing && selected !== 15) service.beginEdit()
        if (selected === 0) service.setSection("paletteMode",cycle(["auto","day","night"],service.draft.paletteMode || "auto",direction))
        else if (selected === 1) service.setSection("motionMode",cycle(["normal","reduced","off"],service.draft.motionMode,direction))
        else if (selected === 2) service.selectDraft(cycle(service.themes.map(t => t.id),service.draft.themeId,direction))
        else if (selected === 3) service.setSection("presentations",{"home.now":cycle(homePresentations,Theme.presentations["home.now"],direction)})
        else if (selected === 4) service.setToken("typography.textScale",Math.max(.85,Math.min(1.1,Math.round((root.style.textScale + direction * .05)*100)/100)))
        else if (selected === 5) {
            const wide = root.style.listRows === 4
            service.setTokens({"metrics.listRows":wide?3:4,"metrics.compactRows":wide?2:3,"metrics.overviewRows":wide?2:3,"metrics.fantasyRows":wide?4:5})
        } else if (selected === 6) service.setToken("shape.radiusCard",Math.max(0,Math.min(24,root.style.radiusCard + direction * 2)))
        else if (selected === 7) service.setToken("colors.accent",cycle(["#6de0be","#e6c880","#b5d3ff","#efc3e6"],root.style.accent.toString(),direction))
        else if (selected === 8 || selected === 9 || selected === 16) service.setToken(selected===8?"typography.uiFamily":selected===9?"typography.numbersFamily":"typography.displayFamily",cycle(service.fontFamilies,selected===8?root.style.uiFamily:selected===9?root.style.numbersFamily:root.style.displayFamily,direction))
        else if (selected === 10) {
            const recipe = cycle(navigationRecipes,Theme.motion["navigate.family"].recipe,direction)
            service.setSection("motion",{"navigate.family":{recipe:recipe,durationMs:160,distancePx:20,easing:"outCubic"},"navigate.view":{recipe:recipe,durationMs:160,distancePx:20,easing:"outCubic"}})
        } else if (selected === 11) service.setSection("scene",{enabled:!Theme.appearance.scene.enabled})
        else if (selected === 12) service.apply()
        else if (selected === 13) service.cancel()
        else if (selected === 14) service.resetDraft()
        else if (selected === 15) service.reloadCatalog()
        else if (selected === 17 || selected === 18) service.transferPack(selected === 17 ? "import" : "export")
        feedback = service.lastError || (selected === 12 ? "Salvataggio in corso…" : "Anteprima · Applica e salva per conservarla")
    }
    Connections {
        target: root.themeService
        function onSaveFinished(ok) { root.feedback = ok ? "Aspetto salvato" : root.themeService.lastError }
    }
    readonly property int selected: section === "settings" ? dashboard.settingsIndex : section === "modules" ? dashboard.modulesIndex : section === "system" ? dashboard.systemIndex : section === "notifications" ? dashboard.notificationIndex : section === "notificationQuiet" ? dashboard.quietIndex : section === "notificationCategories" ? dashboard.categoryIndex : section === "sources" ? dashboard.sourceIndex : dashboard.optionIndex
    readonly property int pageStart: Math.floor(selected / root.style.listRows) * root.style.listRows
    readonly property string heading: ({settings: "IMPOSTAZIONI", appearance: "ASPETTO", system: "LUMINOSITÀ", modules: "MODULI VISIBILI", notifications: "NOTIFICHE", notificationQuiet: "NOTIFICHE / FASCIA SILENZIO", notificationCategories: "NOTIFICHE / AVVISI A SCHERMO", accountSettings: "ACCOUNT CHATGPT", integrations: "SPORT", sources: "DATI E AGGIORNAMENTI"})[section] || ""
    readonly property string description: section === "system" ? "Regola l'immagine · livelli dal 20 al 100%, passi di 5%" : section === "sources" ? "Aggiornamento manuale · attesa minima 30 secondi tra richieste" : section === "notifications" ? "Due regole separate: quando interrompere e quali categorie" : section === "notificationQuiet" ? "Gli urgenti restano visibili per le categorie abilitate" : section === "notificationCategories" ? "Disattivare una categoria non cancella l'elenco Avvisi" : section === "accountSettings" ? "Preferenze salvate · soglie separate dall'acquisto di crediti" : section === "appearance" ? "Anteprima · Applica e salva, oppure 7 per annullare" : "Preferenze salvate automaticamente"
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
            editAppearance(direction)
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
    AppIcon { style: root.style; z: 1; x: 870; y: 29; iconId: "system.settings"; opticalSize: 32 }
    Rectangle { anchors.fill: parent; color: root.style.backgroundOverlay }
    AppText { style: root.style; x: 44; y: root.rows.length <= 2 ? 334 : 410; width: 872; height: 66; visible: root.explanation !== ""; text: root.explanation; color: root.style.textSecondary; font.pixelSize: root.style.font22; lineHeight: 1.35 }
    AppText { style: root.style; x: 44; y: 30; width: 872; text: root.heading; color: root.style.accent; font.pixelSize: root.style.font37; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
    AppText { style: root.style; x: 44; y: 84; width: 872; text: root.description; color: root.style.textSecondary; font.pixelSize: root.style.font22; elide: Text.ElideRight }
    Repeater {
        model: root.rows.slice(root.pageStart, root.pageStart + root.style.listRows)
        delegate: SelectableRow { style: root.style; selectedState: selectedRow;
            required property var modelData
            required property int index
            readonly property int rowIndex: root.pageStart + index
            readonly property bool selectedRow: rowIndex === root.selected
            objectName: root.section + "Row" + rowIndex
            x: 44; y: 132 + index * (348 / root.style.listRows); width: 872; height: 348 / root.style.listRows - 10; radius: root.style.radiusRow
            color: selectedRow ? root.style.surfaceFocused : root.style.surface
            border.color: selectedRow ? root.style.accent : root.style.border; border.width: selectedRow ? root.style.focusWidth : root.style.hairlineWidth
            AppText { style: root.style; x: 20; y: 10; width: 485; text: modelData.title; color: modelData.enabled === false ? root.style.textSecondary : root.style.textPrimary; font.pixelSize: root.style.font28; font.weight: (selectedRow) ? root.style.headingWeight : root.style.bodyWeight; elide: Text.ElideRight }
            AppText { style: root.style; x: 20; y: parent.height - 30; width: 825; text: modelData.detail || ""; color: root.style.textSecondary; font.pixelSize: root.style.font20; elide: Text.ElideRight }
            AppText { style: root.style; x: 515; y: 13; width: 334; horizontalAlignment: Text.AlignRight; text: modelData.value || "›"; color: modelData.enabled === false ? root.style.textSecondary : selectedRow ? root.style.accent : root.style.textPrimary; font.pixelSize: root.style.font25; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; elide: Text.ElideRight }
            MouseArea { anchors.fill: parent; onClicked: { root.setSelected(parent.rowIndex); root.activate(1) } }
        }
    }
    AppText { style: root.style; x: 44; y: 499; width: 872; text: (root.section === "appearance" && root.themeService ? root.themeService.lastError : "") || root.feedback || (root.rows.length ? (root.selected + 1) + "/" + root.rows.length + " · " : "") + (root.section === "settings" || root.section === "integrations" || root.section === "notifications" || root.rows[root.selected] && root.rows[root.selected].target && root.section !== "sources" ? "2/8 SELEZIONA · 5 APRI" : root.section === "sources" ? "2/8 SELEZIONA · 5 AGGIORNA" : "2/8 SELEZIONA · 4/6 REGOLA · 5 CAMBIA"); color: root.style.textSecondary; font.pixelSize: root.style.font21; elide: Text.ElideRight }
    Rectangle { x: 44; y: 548; width: 872; height: 1; color: root.style.border }
    KeyGuide { style: root.style; x: 44; y: 571; color: root.style.accent; font.pixelSize: root.style.font25 }
}
