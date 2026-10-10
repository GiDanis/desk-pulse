import "components/PublicSettingsRows.js" as PublicSettingsRows
import QtQuick
import "themes"
import "components"

Item {
    id: root
    objectName: "settingsPanel"
    property StyleFacade style: Theme
    required property var dashboard
    readonly property var entries: [
        {title:"Schermo",detail:dashboard.systemValue(1)+" · Testo "+Math.round(root.style.textScale*100)+"%",target:"system"},
        {title:"Aspetto",detail:themeService ? (themeService.themes.find(t=>t.id===themeService.savedThemeId) || {}).name || "Tema corrente" : "Tema corrente",target:"appearance"},
        {title:"Moduli e Home",detail:dashboard.families.length+" argomenti visibili · riepiloghi Home",target:"modules"},
        {title:"Avvisi",detail:backend && backend.quietHoursEnabled ? "Silenzio "+quietRange : "Fascia silenzio disattivata",target:"notifications"},
        {title:"Servizi collegati",detail:"Account "+sourceDetail(dashboard.account),target:"services"},
        {title:"Dati e aggiornamenti",detail:"Meteo "+sourceDetail(dashboard.weather),target:"sources"}
    ]
    readonly property var serviceEntries: [
        {id:"service.account",title:"Account ChatGPT",detail:"Dati ricevuti dal PC · stato e rilettura",target:"sources",source:"account"},
        {id:"service.casa",title:"Casa / Smart Life",detail:dashboard.casaData.configured ? "Preferiti e raccolta" : "Non configurato · opzioni disponibili",target:"casaSettings"},
        {id:"service.network",title:"Rete / iliadbox",detail:dashboard.networkData.configured ? "Preferiti, alias e raccolta" : "Non configurato · opzioni disponibili",target:"networkSettings"}
    ]
    readonly property var moduleEntries: dashboard.allFamilies.map(row=>({id:"module."+row.id,moduleId:row.id,title:row.name,
        detail:row.id==="oggi" ? "Sempre raggiungibile" : row.id==="sports" ? "Nasconde l'area senza cambiare le discipline" : "Nel carosello degli argomenti",
        value:row.id==="oggi" ? "SEMPRE ATTIVO" : backend && backend.moduleVisibility[row.id] ? "ATTIVO" : "DISATTIVO",enabled:row.id!=="oggi"}))
        .concat([{id:"modules.sports",title:"Sport e riepiloghi Home",detail:"Discipline, squadra e stagioni",target:"sportModules"}])
    readonly property var sportModuleEntries: [
        {id:"module.sport",moduleId:"sport",title:"Calcio",detail:"Serie A e la tua squadra",enabled:!!backend && backend.sportAvailable},
        {id:"module.f1",moduleId:"f1",title:"Formula 1",detail:"Programma e classifiche",enabled:!!backend && backend.racingAvailable.indexOf("f1")>=0},
        {id:"module.motogp",moduleId:"motogp",title:"MotoGP",detail:"Programma e classifiche",enabled:!!backend && backend.racingAvailable.indexOf("motogp")>=0}
    ].map(row=>Object.assign({},row,{value:backend && backend.moduleVisibility[row.moduleId] ? "ATTIVO" : "DISATTIVO",detail:row.enabled ? row.detail : "Provider non disponibile"}))
        .concat(sportEntries.map(row=>Object.assign({},row,{id:PublicSettingsRows.integrationTargets[row.target]})))
    readonly property var managementRows: themeService ? [
        {id:"appearance.revision",title:"Versione del tema",value:Theme.appearance.themeVersion,detail:"Revisioni installate · anteprima",enabled:catalogTheme.retention!=="latest"},
        {id:"appearance.import",title:"Importa tema",value:"IMPORTA",detail:"Pacchetto ricevuto dal PC"},
        {id:"appearance.export",title:"Esporta tema",value:"ESPORTA",detail:"Condivide il pacchetto corrente"},
        {id:"appearance.reload",title:"Rileggi catalogo",value:"CONTROLLA",detail:"Temi presenti sul dispositivo"}
    ] : []
    readonly property var targets: ["settings", "services", "sportModules", "themeManagement", "appearance", "appearanceNotifications", "system", "modules", "notifications", "notificationQuiet", "notificationCategories", "accountSettings", "integrations", "sources"]
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
    ]
        .concat(backend && backend.sportAvailable ? [{title: "Serie A", detail: sourceDetail(dashboard.sport), target: "sport", value: "AGGIORNA"}] : [])
        .concat(backend && backend.racingAvailable.indexOf("f1") >= 0 ? [{title: "Formula 1", detail: sourceDetail(dashboard.racingStates.f1), target: "f1", value: "AGGIORNA"}] : [])
        .concat(backend && backend.racingAvailable.indexOf("motogp") >= 0 ? [{title: "MotoGP", detail: sourceDetail(dashboard.racingStates.motogp), target: "motogp", value: "AGGIORNA"}] : [])
        .concat(backend ? [{title:"Casa / Smart Life",detail:sourceDetail(dashboard.casa)+" · "+(dashboard.casaData.modeText || "Da configurare"),target:"casa",value:"AGGIORNA",enabled:!!dashboard.casaData.configured && !dashboard.casaData.busy}] : [])
        .concat(backend ? [{title:"Rete locale",detail:sourceDetail(dashboard.network)+" · "+(dashboard.networkData.modeText || "Da configurare"),target:"network",value:"AGGIORNA",enabled:!!dashboard.networkData.configured && !dashboard.networkData.busy}] : [])
        .map(row => {
            const operation = backend ? backend.sourceRefreshStates[row.target] : null
            return operation ? Object.assign({}, row, {detail: operation.message + " · " + row.detail}) : row
        }) : []
    function sourceDetail(value) {
        if (!value) return "Non disponibile"
        const names = {active: "Aggiornato", updating: "Aggiornamento…", offline: "Offline · dati salvati", stale: "Dati salvati", error: "Errore", unavailable: "Non disponibile"}
        const cacheError = value.data && value.data.cacheError
        return (cacheError ? "Dati acquisiti · cache non salvata" : names[value.status] || "In attesa") + (value.updatedAt ? " · " + dashboard.eventStamp(value.updatedAt) : "")
    }
    readonly property bool quietActive: backend && backend.quietHoursEnabled &&
        (backend.quietStartMinute < backend.quietEndMinute
         ? currentMinute >= backend.quietStartMinute && currentMinute < backend.quietEndMinute
         : currentMinute >= backend.quietStartMinute || currentMinute < backend.quietEndMinute)
    readonly property int currentMinute: dashboard.now.getHours() * 60 + dashboard.now.getMinutes()
    readonly property string quietRange: backend ? dashboard.quietTime(backend.quietStartMinute) + " – " + dashboard.quietTime(backend.quietEndMinute) : "—"
    readonly property var notificationEntries: [
        {title: "Fascia silenzio", detail: backend && backend.quietHoursEnabled ? quietRange + " · " + (quietActive ? "silenzio in corso" : "fuori fascia") : "Disattivata · nessuna pausa oraria dei banner", target: "notificationQuiet"},
        {title: "Avvisi sullo schermo", detail: "Scegli quali categorie possono interrompere la vista", target: "notificationCategories"},
        {title:"Soglie Account",detail:"Utilizzo e livello critico",target:"accountSettings"}
    ]
    readonly property var rows: !active ? [] : section === "settings" ? entries : section === "integrations" ? sportEntries : section === "sources" ? sourceEntries : section === "services" ? serviceEntries : section === "sportModules" ? sportModuleEntries : section === "themeManagement" ? managementRows : section === "modules" ? moduleEntries : section === "appearance" ? appearanceRows
 : section === "appearanceNotifications" ? notificationAppearanceRows : section === "system" ? [
        {title: "Modalità", value: dashboard.systemValue(1), detail: "Automatico segue la fascia giorno / notte"},
        {title: "Livello manuale", value: dashboard.systemValue(2), detail: "Usato in modalità manuale", enabled: backend && backend.brightnessMode === "manual"},
        {title: "Livello giorno", value: dashboard.systemValue(3), detail: "Usato in modalità automatica", enabled: backend && backend.brightnessMode === "auto"},
        {title: "Livello notte", value: dashboard.systemValue(4), detail: "Usato in modalità automatica", enabled: backend && backend.brightnessMode === "auto"},
        {title: "Giorno dalle", value: dashboard.systemValue(5), detail: "Orario condiviso con il tema automatico"},
        {title: "Notte dalle", value: dashboard.systemValue(6), detail: "Orario condiviso con il tema automatico"},
        {id:"appearance.textScale",title:"Dimensione testo",value:Math.round(root.style.textScale*100)+"%",detail:supportsAdjustment("textScale") ? "Anteprima · salva oppure annulla" : "Dimensione gestita dal tema",enabled:supportsAdjustment("textScale")},
        {id:"appearance.apply",title:"Salva testo",value:"SALVA",detail:"Conserva la dimensione al riavvio",enabled:!!themeService && themeService.dirty && themeService.readyToApply},
        {id:"appearance.cancel",title:"Annulla anteprima",value:"ANNULLA",detail:"Torna alla dimensione salvata",enabled:!!themeService && themeService.dirty}
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
    readonly property var catalogTheme: themeService ? themeService.selectedTheme : ({})
    function supportsAdjustment(name) { return !themeService || (catalogTheme.adjustments || []).indexOf(name) >= 0 }
    readonly property var homePresentations: Object.keys(Theme.appearance.presentationRegistry).filter(id => (Theme.appearance.presentationRegistry[id].contentIds || []).indexOf("home.now") >= 0)
    readonly property var navigationRecipes: Object.keys(Theme.appearance.motionRegistry).filter(id => (Theme.appearance.motionRegistry[id].events || []).indexOf("navigate.family") >= 0)
    function presentationName(id) { return (Theme.appearance.presentationRegistry[id] || {}).name || id }
    function recipeName(id) { return (Theme.appearance.motionRegistry[id] || {}).name || id }
    property bool advancedAppearance: false
    readonly property var appearanceRows: advancedAppearance ? advancedAppearanceRows : simpleAppearanceRows
    readonly property var simpleAppearanceRows: themeService ? [
        {title:"Palette", value:({auto:"AUTOMATICA",day:"GIORNO",night:"NOTTE"})[themeService.draft.paletteMode || "auto"],detail:supportsAdjustment("paletteMode") ? "Automatico segue gli orari del dispositivo" : "Palette gestita dal tema",enabled:supportsAdjustment("paletteMode")},
        {title:"Movimento", value:({normal:"NORMALE",reduced:"RIDOTTO",off:"DISATTIVO"})[themeService.draft.motionMode],detail:"Animazioni del tema e della scena"},
        {title:"Tema",value:(themeService.themes.find(t => t.id === themeService.draft.themeId) || {}).name || themeService.draft.themeId,detail:catalogTheme.coverageSummary || "Scegli dalla lista · attivazione e salvataggio",target:"themeChooser"},
        {title:"Dimensione testo",value:Math.round(root.style.textScale*100)+"%",detail:supportsAdjustment("textScale") ? "Piccolo adattamento della leggibilità" : "Dimensione definita dal tema",enabled:supportsAdjustment("textScale")},
        {title:"Versione del tema",value:Theme.appearance.themeVersion,detail:"4/6 sceglie una revisione installata"},
        {title:"Applica e salva",value:themeService.status === "saving" ? "SALVATAGGIO…" : "SALVA",detail:"Conserva il tema al prossimo avvio",enabled:themeService.dirty && themeService.readyToApply},
        {title:"Annulla anteprima",value:"RIPRISTINA",detail:"Torna al tema salvato",enabled:themeService.dirty && themeService.status !== "saving"},
        {title:"Importa temi",value:"IMPORTA",detail:"Pacchetti locali ricevuti dal PC"},
        {title:"Esporta tema",value:"ESPORTA",detail:"Pacchetto completo per un altro dispositivo"},
        {title:"Personalizzazione avanzata",value:"APRI",detail:"Editor di compatibilità · la composizione si crea nel tema"}
    ].map((row,index) => Object.assign({},row,{id:PublicSettingsRows.simpleAppearanceIds[index]})).filter(row => ["appearance.textScale","appearance.revision","appearance.import","appearance.export"].indexOf(row.id)<0).concat([{id:"appearance.management",title:"Gestione temi",detail:"Importa, esporta e revisioni",target:"themeManagement"}]) : []
    readonly property var advancedAppearanceRows: themeService ? [
        {title: "Palette", value: ({auto:"AUTOMATICA",day:"GIORNO",night:"NOTTE"})[themeService.draft.paletteMode || "auto"], detail: supportsAdjustment("paletteMode") ? "Bozza · segue gli orari di Luminosità in automatico" : "Palette gestita dal tema",enabled:supportsAdjustment("paletteMode")},
        {title: "Movimento", value: ({normal:"NORMALE",reduced:"RIDOTTO",off:"DISATTIVO"})[themeService.draft.motionMode], detail: "Transizioni e scena rispettano la stessa policy"},
        {title: "Tema", value: (themeService.themes.find(t => t.id === themeService.draft.themeId) || {}).name || themeService.draft.themeId, detail:catalogTheme.coverageSummary || "Preset e pacchetti personali nel catalogo"},
        {title: "Composizione Home", value: presentationName(Theme.presentations["home.now"]), detail: "Stessi dati · disposizione a sinistra o centrata"},
        {title: "Dimensione testo", value: Math.round(root.style.textScale * 100) + "%", detail:supportsAdjustment("textScale") ? "Da 85 a 110% · ogni stile conserva i propri ruoli" : "Dimensione definita dal tema",enabled:supportsAdjustment("textScale")},
        {title: "Densità", value: root.style.listRows === 4 ? "REGOLARE" : "AMPIA", detail: "Paginazione coerente anche in Sport e Motorsport"},
        {title: "Angoli delle schede", value: root.style.radiusCard + " px", detail: "Da 0 a 24 · passi di 2 pixel"},
        {title: "Colore accento", value: root.style.accent.toString(), detail: "I colori degli avvisi ufficiali restano riconoscibili"},
        {title: "Carattere interfaccia", value: root.style.uiFamily || "PREDEFINITO", detail: "Famiglie disponibili nel sistema · caricate su richiesta"},
        {title: "Carattere numeri", value: root.style.numbersFamily || "PREDEFINITO", detail: "Orologi e dati numerici · indipendente dall'interfaccia"},
        {title: "Transizioni", value: recipeName((Theme.motion["navigate.family"] || {}).recipe) || "—", detail: "Scorrimento, dissolvenza o cambio immediato"},
        {title: "Scena di prova", value: Theme.appearance && Theme.appearance.scene.enabled ? "ATTIVA" : "DISATTIVA", detail: "Attore geometrico persistente · si sospende con avvisi e notte"},
        {title: "Applica e salva", value: themeService.status === "saving" ? "SALVATAGGIO…" : "SALVA", detail: "La bozza diventa la preferenza al prossimo avvio", enabled: themeService.dirty && themeService.readyToApply},
        {title: "Annulla bozza", value: "RIPRISTINA", detail: "Torna all'ultimo aspetto salvato", enabled: themeService.dirty && themeService.status !== "saving"},
        {title: "Ripristina Base", value: "BOZZA", detail: "Azzera solo la personalizzazione dell'aspetto"},
        {title: "Rileggi catalogo", value: "AGGIORNA", detail: "Pacchetti importati · errori visibili, Base sempre disponibile"},
        {title: "Carattere orologio", value: root.style.displayFamily || "PREDEFINITO", detail: "Famiglia del display grande · indipendente da testo e numeri"},
        {title: "Importa pacchetti", value: "IMPORTA", detail: "Cartella theme-imports · contenuti locali validati"},
        {title: "Esporta personalizzazione", value: "ESPORTA", detail: "Cartella theme-exports · include font e risorse del pacchetto"},
        {title: "Avvisi", detail: "Composizioni, testo, forme e animazioni · anteprima isolata", target: "appearanceNotifications"},
        {title:"Personalizzazione rapida",value:"TORNA",detail:"Tema, palette, testo e movimento"}
    ].map((row,index)=>Object.assign({},row,{id:index===20 ? "appearance.simple" : PublicSettingsRows.canonicalSections["settings.appearance"][index]}))
        .filter(row=>["appearance.textScale","appearance.import","appearance.export","appearance.reload","appearance.palette","appearance.motion","appearance.theme"].indexOf(row.id)<0)
        .concat([{id:"appearance.management",title:"Gestione temi",detail:"Importa, esporta e revisioni",target:"themeManagement"}]) : []
    readonly property var notificationModes: ["small","large","urgent","badge","inbox","detail"]
    readonly property var notificationLabels: ["PICCOLO","GRANDE","URGENTE","BADGE","ELENCO","DETTAGLIO"]
    readonly property string notificationMode: notificationModes[dashboard.notificationAppearanceMode]
    readonly property string notificationPrefix: "notifications."+notificationMode+"."
    readonly property NotificationStyle notificationMetrics: NotificationStyle { appearance: Theme.appearance; mode: root.notificationMode }
    function notificationContent(mode) { return mode === "small" || mode === "large" ? "alerts.banner."+mode : "alerts."+mode }
    function notificationPresentations(mode) { return Object.keys(Theme.appearance.presentationRegistry).filter(id => (Theme.appearance.presentationRegistry[id].contentIds || []).indexOf(notificationContent(mode)) >= 0) }
    readonly property string notificationMotionPrefix: notificationMode === "small" || notificationMode === "large" ? "banner."+notificationMode : "alerts."+notificationMode
    readonly property var notificationAppearanceRows: themeService ? [
        {title:"Superficie da regolare",value:notificationLabels[dashboard.notificationAppearanceMode],detail:"Ruoli indipendenti · 4/6 cambia modalità"}
    ].concat(notificationModes.map((mode,index) => ({title:"Composizione · "+notificationLabels[index],value:presentationName(Theme.presentations[notificationContent(mode)]),detail:"Template compatibili dal catalogo"}))).concat([
        {title:"Mostra anteprima",value:"PROVA",detail:"Eventi simulati · nessuna consegna o lettura reale"},
        {title:"Spazio interno",value:notificationMetrics.padding+" px",detail:"Solo la superficie selezionata"},
        {title:"Dimensione titolo",value:notificationMetrics.titleSize+" px",detail:"Indipendente da Home e Sport"},
        {title:"Dimensione corpo",value:notificationMetrics.bodySize+" px",detail:"Dettaglio completo scorrevole"},
        {title:"Dimensione fonte",value:notificationMetrics.sourceSize+" px",detail:"Fonte e validità dell'avviso"},
        {title:"Angoli",value:notificationMetrics.noticeRadius+" px",detail:"Raggio della superficie selezionata"},
        {title:"Ancoraggio",value:({top:"ALTO",bottom:"BASSO",center:"CENTRO"})[notificationMetrics.anchor],detail:"La geometria deve restare nel display"},
        {title:"Righe elenco",value:Theme.appearance.tokens["notifications.inbox.rows"]+"",detail:"Numero massimo · la selezione rimane visibile"},
        {title:"Font titolo",value:notificationMetrics.titleFamily,detail:"Famiglia separata dal resto della dashboard"},
        {title:"Font corpo",value:notificationMetrics.bodyFamily,detail:"Famiglie disponibili nel catalogo"},
        {title:"Font fonte",value:notificationMetrics.sourceFamily,detail:"Fonte e validità"},
        {title:"Icona",value:notificationMetrics.showIcon?"VISIBILE":"NASCOSTA",detail:"Il renderer decide il proprio uso delle icone"},
        {title:"Fonte sintetica",value:notificationMetrics.showSource?"VISIBILE":"NASCOSTA",detail:"Nel dettaglio può essere regolata separatamente"},
        {title:"Animazione entrata",value:notificationMode === "urgent"?"IMMEDIATA":recipeName((Theme.motion[notificationMotionPrefix+".enter"] || {}).recipe),detail:"Rispetta Normale / Ridotto / Disattivo",enabled:notificationMode !== "urgent"},
        {title:"Animazione uscita",value:notificationMode === "urgent"?"IMMEDIATA":recipeName((Theme.motion[notificationMotionPrefix+".exit"] || {}).recipe),detail:"Testo e stile restano coerenti durante l'uscita",enabled:notificationMode !== "urgent"},
        {title:"Applica e salva",value:"SALVA",detail:"Salva tutta la bozza Aspetto",enabled:themeService.dirty && themeService.readyToApply},
        {title:"Ripristina avvisi del tema",value:"BOZZA",detail:"Rimuove soltanto gli override delle notifiche"},
        {title:"Torna ad Aspetto",value:"APRI",detail:"Conserva la bozza · 7 torna"}
    ]) : []
    function editNotifications(direction) {
        const service = themeService
        if (!service || service.status === "saving" || service.status === "working") return
        if (!service.editing) service.beginEdit()
        const prefix = notificationPrefix, metrics = notificationMetrics
        if (selected === 0) dashboard.notificationAppearanceMode = (dashboard.notificationAppearanceMode+direction+6)%6
        else if (selected >= 1 && selected <= 6) {
            const mode = notificationModes[selected-1], content = notificationContent(mode)
            const overrides = Object.assign({},service.draft.overrides.presentations || {})
            overrides[content] = cycle(notificationPresentations(mode),Theme.presentations[content],direction)
            service.setSection("presentations",overrides)
        } else if (selected === 7) dashboard.notificationPreviewMode = notificationMode
        else if (selected === 8) service.setToken(prefix+"padding",Math.max(0,Math.min(64,metrics.padding+direction*2)))
        else if (selected >= 9 && selected <= 11) {
            const name = ["titleSize","bodySize","sourceSize"][selected-9]
            const maximum = [72,44,32][selected-9]
            service.setToken(prefix+name,Math.max(selected === 9 ? 18 : 16,Math.min(maximum,Theme.appearance.tokens[prefix+name]+direction*2)))
        } else if (selected === 12) service.setToken(prefix+"radius",Math.max(0,Math.min(40,metrics.noticeRadius+direction*2)))
        else if (selected === 13) service.setTokens({[prefix+"anchor"]:cycle(["top","bottom","center"],metrics.anchor,direction),[prefix+"insetY"]:0})
        else if (selected === 14) service.setToken("notifications.inbox.rows",Math.max(1,Math.min(5,Theme.appearance.tokens["notifications.inbox.rows"]+direction)))
        else if (selected >= 15 && selected <= 17) {
            const name = ["titleFamily","bodyFamily","sourceFamily"][selected-15]
            service.setToken(prefix+name,cycle(service.fontFamilies,metrics[name],direction))
        } else if (selected === 18 || selected === 19) service.setToken(prefix+(selected === 18 ? "showIcon" : "showSource"),!(selected === 18 ? metrics.showIcon : metrics.showSource))
        else if (selected === 20 || selected === 21) {
            const event = notificationMotionPrefix+(selected === 20 ? ".enter" : ".exit")
            const legacyEvent = (notificationMode === "small" || notificationMode === "large" ? "banner." : "panel.")+(selected === 20 ? "enter" : "exit")
            const choices = Object.keys(Theme.appearance.motionRegistry).filter(id => {
                const events = Theme.appearance.motionRegistry[id].events
                return !events || events.indexOf(event) >= 0 || events.indexOf(legacyEvent) >= 0
            })
            const overrides = Object.assign({},service.draft.overrides.motion || {})
            overrides[event] = {recipe:cycle(choices,(Theme.motion[event] || {}).recipe,direction),durationMs:120,distancePx:20,easing:"outCubic"}
            service.setSection("motion",overrides)
        } else if (selected === 22) service.apply()
        else if (selected === 23) service.resetNotifications()
        else if (selected === 24) dashboard.popOverlay()
        feedback = service.lastError || "Bozza Avvisi · Applica e salva per conservarla"
    }
    function cycle(values, current, direction) {
        return values[(Math.max(0, values.indexOf(current)) + direction + values.length) % values.length]
    }
    function editSimpleAppearance(direction) {
        const service=themeService
        if (!service || service.status === "saving" || service.status === "working") return
        if (!service.editing) service.beginEdit()
        let accepted=true
        const actionIndex=PublicSettingsRows.simpleAppearanceIds.indexOf((simpleAppearanceRows[selected] || {}).id)
        if (actionIndex === 0) accepted=service.setSection("paletteMode",cycle(["auto","day","night"],service.draft.paletteMode || "auto",direction))
        else if (actionIndex === 1) accepted=service.setSection("motionMode",cycle(["normal","reduced","off"],service.draft.motionMode,direction))
        else if (actionIndex === 2) accepted=dashboard.openThemeChooser()
        else if (actionIndex === 3) accepted=service.setToken("typography.textScale",Math.max(.85,Math.min(1.1,Math.round((root.style.textScale+direction*.05)*100)/100)))
        else if (actionIndex === 4) accepted=service.stepRevision(direction)
        else if (actionIndex === 5) accepted=service.apply()
        else if (actionIndex === 6) service.cancel()
        else if (actionIndex === 7 || actionIndex === 8) accepted=service.transferPack(actionIndex === 7 ? "import" : "export")
        else if (actionIndex === 9) { advancedAppearance=true; dashboard.optionIndex=0 }
        feedback=service.lastError || (!accepted ? "Operazione non disponibile" : actionIndex === 5 ? "Salvataggio in corso…" : "Anteprima · Applica e salva per conservarla")
    }
    function editAppearance(direction) {
        const actionIndex=(rows[selected] || {}).id==="appearance.simple" ? 20 : PublicSettingsRows.canonicalSections["settings.appearance"].indexOf((rows[selected] || {}).id)
        const service = themeService
        if (!service || (service.status === "saving" || service.status === "working")) return
        if (!service.editing && actionIndex !== 15) service.beginEdit()
        if (actionIndex === 0) service.setSection("paletteMode",cycle(["auto","day","night"],service.draft.paletteMode || "auto",direction))
        else if (actionIndex === 1) service.setSection("motionMode",cycle(["normal","reduced","off"],service.draft.motionMode,direction))
        else if (actionIndex === 2) dashboard.openThemeChooser()
        else if (actionIndex === 3) service.setSection("presentations",Object.assign({},service.draft.overrides.presentations || {},{"home.now":cycle(homePresentations,Theme.presentations["home.now"],direction)}))
        else if (actionIndex === 4) service.setToken("typography.textScale",Math.max(.85,Math.min(1.1,Math.round((root.style.textScale + direction * .05)*100)/100)))
        else if (actionIndex === 5) {
            const wide = root.style.listRows === 4
            service.setTokens({"metrics.listRows":wide?3:4,"metrics.compactRows":wide?2:3,"metrics.overviewRows":wide?2:3,"metrics.fantasyRows":wide?4:5})
        } else if (actionIndex === 6) service.setToken("shape.radiusCard",Math.max(0,Math.min(24,root.style.radiusCard + direction * 2)))
        else if (actionIndex === 7) service.setToken("colors.accent",cycle(["#6de0be","#e6c880","#b5d3ff","#efc3e6"],root.style.accent.toString(),direction))
        else if (actionIndex === 8 || actionIndex === 9 || actionIndex === 16) service.setToken(actionIndex===8?"typography.uiFamily":actionIndex===9?"typography.numbersFamily":"typography.displayFamily",cycle(service.fontFamilies,actionIndex===8?root.style.uiFamily:actionIndex===9?root.style.numbersFamily:root.style.displayFamily,direction))
        else if (actionIndex === 10) {
            const recipe = cycle(navigationRecipes,Theme.motion["navigate.family"].recipe,direction)
            service.setSection("motion",Object.assign({},service.draft.overrides.motion || {},{"navigate.family":{recipe:recipe,durationMs:160,distancePx:20,easing:"outCubic"},"navigate.view":{recipe:recipe,durationMs:160,distancePx:20,easing:"outCubic"}}))
        } else if (actionIndex === 11) service.setSection("scene",{enabled:!Theme.appearance.scene.enabled})
        else if (actionIndex === 12) service.apply()
        else if (actionIndex === 13) service.cancel()
        else if (actionIndex === 14) service.resetDraft()
        else if (actionIndex === 15) service.reloadCatalog()
        else if (actionIndex === 20) { advancedAppearance=false; dashboard.optionIndex=0 }
        else if (actionIndex === 17 || actionIndex === 18) service.transferPack(actionIndex === 17 ? "import" : "export")
        feedback = service.lastError || (actionIndex === 12 ? "Salvataggio in corso…" : "Anteprima · Applica e salva per conservarla")
    }
    Connections {
        target: root.themeService
        function onSaveFinished(ok) { root.feedback = ok ? "Aspetto salvato" : root.themeService.lastError }
    }
    readonly property int selected: section === "settings" ? dashboard.settingsIndex : section === "modules" ? dashboard.modulesIndex : section === "system" ? dashboard.systemIndex : section === "notifications" ? dashboard.notificationIndex : section === "notificationQuiet" ? dashboard.quietIndex : section === "notificationCategories" ? dashboard.categoryIndex : section === "sources" ? dashboard.sourceIndex : dashboard.optionIndex
    readonly property int visibleRowCount: 3
    readonly property int pageStart: Math.floor(selected / visibleRowCount) * visibleRowCount
    readonly property string heading: ({settings: "IMPOSTAZIONI", appearance: "ASPETTO", appearanceNotifications: "ASPETTO / AVVISI", system: "SCHERMO", modules: "MODULI E HOME", notifications: "AVVISI", services:"SERVIZI COLLEGATI", sportModules:"SPORT E HOME", themeManagement:"GESTIONE TEMI", notificationQuiet: "NOTIFICHE / FASCIA SILENZIO", notificationCategories: "NOTIFICHE / AVVISI A SCHERMO", accountSettings: "ACCOUNT CHATGPT", integrations: "SPORT", sources: "DATI E AGGIORNAMENTI"})[section] || ""
    readonly property string description: section === "settings" ? "Scegli un gruppo" : section === "themeManagement" ? "Trasferimenti e revisioni dei temi" : section === "services" ? "Stato e opzioni dei collegamenti" : section === "sportModules" ? "Discipline visibili e riepiloghi Home" : section === "system" ? themeService && themeService.dirty ? "Luminosità salvata · dimensione testo da salvare" : "Luminosità salvata automaticamente · dimensione testo" : section === "sources" ? "Aggiornamento manuale · attesa minima 30 secondi tra richieste" : section === "notifications" ? "Categorie, fascia silenzio e soglie Account" : section === "notificationQuiet" ? "Gli urgenti restano visibili per le categorie abilitate" : section === "notificationCategories" ? "Disattivare una categoria non cancella l'elenco Avvisi" : section === "accountSettings" ? "Preferenze salvate · soglie separate dall'acquisto di crediti" : (section === "appearance" || section === "appearanceNotifications") ? themeService && themeService.dirty ? "Regolazioni in anteprima · salva oppure annulla" : "Aspetto salvato · scegli il tema dalla lista" : "Preferenze salvate automaticamente"
    readonly property string explanation: section === "notifications" ? "Gli avvisi ricevuti restano consultabili da 3 AVVISI.\nLe soglie si regolano qui da Soglie Account." : section === "notificationQuiet" ? (backend && backend.quietHoursEnabled ? quietRange + " · " + (quietActive ? "silenzio in corso" : "fuori fascia") : "Fascia disattivata · nessuna pausa oraria") + "\nLe categorie disattivate restano nascoste anche fuori fascia." : section === "notificationCategories" ? "Meteo/Account consentiti: banner fuori fascia, urgenti sempre.\nMeteo/Account nascosti: restano nell'elenco 3 AVVISI." : ""
    property string feedback: ""
    property string feedbackSource: ""
    Connections {
        target: root.backend
        function onSettingsChanged() {
            if (root.section === "sources" && root.feedbackSource) {
                const operation = root.backend.sourceRefreshStates[root.feedbackSource]
                if (operation) root.feedback = operation.message
            }
        }
    }
    onSectionChanged: { feedback = ""; feedbackSource = ""; if (["appearance","appearanceNotifications","themeManagement"].indexOf(section)<0) advancedAppearance=false }

    property var selectedIdentities: ({})
    function rowIdentity(row,index) {
        return row.id || PublicSettingsRows.identity(dashboard.publicRoutes[section] || "",row,index,{families:dashboard.allFamilies,advancedAppearance:advancedAppearance}) || row.target || row.title
    }
    function rememberSelectedRow() {
        if (!active || !rows[selected]) return
        const saved=Object.assign({},selectedIdentities);saved[section]=rowIdentity(rows[selected],selected);selectedIdentities=saved
    }
    function restoreSelectedRow() {
        if (!active || !rows.length) return
        const id=selectedIdentities[section]
        const index=id ? rows.findIndex((row,i)=>rowIdentity(row,i)===id) : -1
        setSelected(index>=0 ? index : Math.max(0,Math.min(rows.length-1,selected)))
    }
    property string lastRowsRoute: ""
    property string lastRowIds: ""
    onRowsChanged: {
        const ids=rows.map((row,i)=>rowIdentity(row,i)).join("|")
        const restore=section===lastRowsRoute && ids!==lastRowIds && !!lastRowIds
        lastRowsRoute=section;lastRowIds=ids
        if (restore) restoreSelectedRow()
    }
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
        feedbackSource = ""
        rememberSelectedRow()
    }
    function activate(direction) {
        if (!backend || !rows.length) return
        const row = rows[selected]
        if (!row || row.enabled === false) return
        if (section === "settings" || section === "services") {
            dashboard.systemIndex = 0; dashboard.notificationIndex = 0
            dashboard.quietIndex = 0; dashboard.categoryIndex = 0; dashboard.sourceIndex = 0
            dashboard.modulesIndex = dashboard.allFamilies.length > 1 ? 1 : 0
            dashboard.pushOverlay(row.target)
            if (row.source) dashboard.sourceIndex=Math.max(0,sourceEntries.findIndex(entry=>entry.target===row.source))
        } else if (section === "integrations" || section === "sportModules" && !row.moduleId) {
            if (row.target === "sportSettings") { dashboard.sportSettingsIndex = 0; dashboard.pushOverlay("sportSettings") }
            else { dashboard.racingSettingsKind = row.target; dashboard.racingSettingsIndex = 0; dashboard.pushOverlay("racingSettings") }
        } else if (section === "notifications") dashboard.pushOverlay(row.target)
        else if (section === "sportModules") backend.toggleModuleVisibility(row.moduleId)
        else if (section === "themeManagement") dashboard.publicAppearanceSetting("settings.appearance.management",{id:row.id,control:row.id==="appearance.revision" ? "choice" : "transfer",options:[]},direction)
        else if (section === "notificationCategories" && row.sportSetting !== undefined) backend.adjustSportSetting(row.sportSetting, direction)
        else if (section === "sources") {
            feedbackSource = row.target
            const sent = backend.refreshSource(row.target)
            const operation = backend.sourceRefreshStates[row.target]
            feedback = operation ? operation.message : backend.demo ? "Demo · nessuna richiesta esterna" : sent ? "Richiesta inviata · in attesa dell'esito" : "Richiesta non accettata"
        } else if (section === "appearance") {
            if (row.target) { dashboard.pushOverlay(row.target) }
            else if (advancedAppearance) editAppearance(direction)
            else editSimpleAppearance(direction)
        } else if (section === "appearanceNotifications") {
            editNotifications(direction)
        } else if (section === "system") {
            if (selected<6) backend.adjustDisplaySetting(selected+1,direction)
            else if (row.id==="appearance.apply") themeService.apply()
            else if (row.id==="appearance.cancel") themeService.cancel()
            else { if (!themeService.editing) themeService.beginEdit();themeService.setToken("typography.textScale",Math.max(.85,Math.min(1.1,Math.round((root.style.textScale+direction*.05)*100)/100))) }
        } else if (section === "modules") {
            if (row.target) {dashboard.pushOverlay(row.target)}
            else backend.toggleModuleVisibility(row.moduleId)
        }
        else if (section === "notificationQuiet" || section === "notificationCategories") backend.adjustNotificationSetting(row.setting, direction)
        else if (section === "accountSettings") backend.adjustAccountSetting(selected, direction)
    }
    function handleKey(position) {
        if (!active) return false
        const minimum = section === "modules" && rows.length > 1 ? 1 : 0
        if (position === 2) setSelected(Math.max(minimum, selected - 1))
        else if (position === 8) setSelected(Math.min(rows.length - 1, selected + 1))
        else if (position === 5 || (position === 4 || position === 6) && ["settings", "services", "integrations", "notifications", "sources"].indexOf(section) < 0 && !rows[selected].target) activate(position === 4 ? -1 : 1)
        return true
    }
    readonly property string visibleFeedback: ((section === "appearance" || section === "appearanceNotifications" || section === "system") && themeService ? themeService.lastError : "") || feedback
    function iconFor(target) {
        return ({system:"system.display",appearance:"system.display",modules:"system.modules",notifications:"system.alerts",services:"system.services",sources:"system.refresh"})[target] || "system.settings"
    }
    Rectangle { anchors.fill:parent; color:root.style.background }
    Rectangle { anchors.fill:parent; color:root.style.backgroundOverlay }
    AppText {style:root.style;x:24;y:13;text:"Impostazioni";font.pixelSize:root.style.font31;color:root.style.textPrimary}
    AppIcon {style:root.style;x:894;y:13;iconId:"system.settings";opticalSize:30}
    Rectangle {x:24;y:55;width:912;height:1;color:root.style.border}
    AppText {style:root.style;x:24;y:76;width:912;visible:root.section!=="settings";text:root.heading;font.pixelSize:root.style.font37;color:root.style.textPrimary;font.weight:root.style.headingWeight;elide:Text.ElideRight}
    AppText {style:root.style;x:24;y:122;width:912;visible:root.section!=="settings";text:root.description;font.pixelSize:root.style.font22;color:root.style.textSecondary;elide:Text.ElideRight}
    Item {
        x:24;y:72;width:912;height:552;visible:root.section==="settings"
        Repeater {model:root.section==="settings" ? root.rows : []
            delegate:SelectableRow {
                required property var modelData
                required property int index
                style:root.style;selectedState:index===root.selected
                objectName:"settingsRow"+index
                x:(index%2)*462;y:Math.floor(index/2)*188;width:450;height:176;radius:root.style.radiusCard
                color:selectedState ? root.style.surfaceFocused : root.style.surface
                border.color:selectedState ? root.style.focusIndicator : root.style.border
                border.width:selectedState ? root.style.focusWidth : root.style.hairlineWidth
                AppIcon {style:root.style;x:20;y:20;iconId:root.iconFor(modelData.target);opticalSize:32}
                AppText {style:root.style;x:66;y:17;width:366;text:modelData.title;font.pixelSize:root.style.font31;color:root.style.textPrimary;font.weight:root.style.headingWeight;elide:Text.ElideRight}
                AppText {style:root.style;x:20;y:70;width:410;height:90;text:modelData.detail;font.pixelSize:root.style.font22;color:root.style.textSecondary;wrapMode:Text.WordWrap;maximumLineCount:3;elide:Text.ElideRight}
                MouseArea {anchors.fill:parent;onClicked:{root.setSelected(parent.index);root.activate(1)}}
            }
        }
    }
    ListView {
        id:settingsList
        objectName:"settingsList"
        x:24;y:164;width:912
        height:460-(root.visibleFeedback ? 36 : 0)-(root.explanation ? 64 : 0)
        visible:root.section!=="settings";clip:true;spacing:12;boundsBehavior:Flickable.StopAtBounds
        model:visible ? root.rows : []
        currentIndex:root.selected
        onCurrentIndexChanged:Qt.callLater(function(){settingsList.positionViewAtIndex(settingsList.currentIndex,ListView.Contain)})
        onCountChanged:Qt.callLater(function(){settingsList.positionViewAtIndex(settingsList.currentIndex,ListView.Contain)})
        readonly property real rowStep:Math.max(112*root.style.textScale,(height+12)/Math.min(4,Math.max(1,count)))
        delegate:SelectableRow {
            required property var modelData
            required property int index
            style:root.style;selectedState:index===root.selected
            objectName:root.section+"Row"+index
            width:settingsList.width-(settingsList.contentHeight>settingsList.height ? 10 : 0);height:settingsList.rowStep-12;radius:root.style.radiusRow
            color:selectedState ? root.style.surfaceFocused : root.style.surface
            border.color:selectedState ? root.style.focusIndicator : root.style.border
            border.width:selectedState ? root.style.focusWidth : root.style.hairlineWidth
            AppText {style:root.style;x:18;y:10;width:parent.width-358;text:modelData.title;font.pixelSize:root.style.font31;color:modelData.enabled===false ? root.style.textSecondary : root.style.textPrimary;font.weight:selectedState ? root.style.headingWeight : root.style.bodyWeight;elide:Text.ElideRight}
            AppText {style:root.style;x:parent.width-324;y:13;width:306;horizontalAlignment:Text.AlignRight;text:modelData.value || "›";font.pixelSize:root.style.font26;color:modelData.enabled===false ? root.style.textSecondary : root.style.textPrimary;elide:Text.ElideRight}
            AppText {style:root.style;x:18;y:parent.height-50;width:parent.width-36;height:44;text:modelData.detail || "";font.pixelSize:root.style.font21;color:root.style.textSecondary;wrapMode:Text.WordWrap;maximumLineCount:2;elide:Text.ElideRight}
            MouseArea {anchors.fill:parent;enabled:modelData.enabled!==false;onClicked:{root.setSelected(parent.index);root.activate(1)}}
        }
        Rectangle {anchors.right:parent.right;width:4;y:settingsList.visibleArea.yPosition*settingsList.height;height:Math.max(18,settingsList.visibleArea.heightRatio*settingsList.height);radius:2;color:root.style.accent;visible:settingsList.contentHeight>settingsList.height;opacity:0.65}
    }
    AppText {style:root.style;x:24;y:settingsList.y+settingsList.height+8;width:912;height:56;visible:!!root.explanation && root.section!=="settings";text:root.explanation;font.pixelSize:root.style.font20;color:root.style.textSecondary;wrapMode:Text.WordWrap;maximumLineCount:2;elide:Text.ElideRight}
    AppText {style:root.style;x:24;y:592;width:912;height:32;visible:!!root.visibleFeedback && root.section!=="settings";text:root.visibleFeedback;font.pixelSize:root.style.font22;color:root.style.textSecondary;elide:Text.ElideRight}
}
