.pragma library

// Private ID templates from theme-api/actions.json settingRows.sections.
// Renderers consume the resulting SettingRowModel, never the legacy indexes.
var canonicalSections = {
    "settings.index": [
        "appearance",
        "display",
        "modules",
        "notifications",
        "account",
        "integrations",
        "sources",
        "casa",
        "network"
    ],
    "settings.display": [
        "display.mode",
        "display.manualBrightness",
        "display.dayBrightness",
        "display.nightBrightness",
        "display.dayStart",
        "display.nightStart"
    ],
    "settings.appearance": [
        "appearance.palette",
        "appearance.motion",
        "appearance.theme",
        "appearance.homeComposition",
        "appearance.textScale",
        "appearance.density",
        "appearance.cardRadius",
        "appearance.accent",
        "appearance.uiFont",
        "appearance.numbersFont",
        "appearance.transitions",
        "appearance.scene",
        "appearance.apply",
        "appearance.cancel",
        "appearance.reset",
        "appearance.reload",
        "appearance.clockFont",
        "appearance.import",
        "appearance.export",
        "appearance.notifications"
    ],
    "settings.appearance.notifications": [
        "notifications.visual.mode",
        "notifications.visual.composition.small",
        "notifications.visual.composition.large",
        "notifications.visual.composition.urgent",
        "notifications.visual.composition.badge",
        "notifications.visual.composition.inbox",
        "notifications.visual.composition.detail",
        "notifications.visual.preview",
        "notifications.visual.padding",
        "notifications.visual.titleSize",
        "notifications.visual.bodySize",
        "notifications.visual.sourceSize",
        "notifications.visual.radius",
        "notifications.visual.anchor",
        "notifications.visual.inboxRows",
        "notifications.visual.titleFont",
        "notifications.visual.bodyFont",
        "notifications.visual.sourceFont",
        "notifications.visual.icon",
        "notifications.visual.source",
        "notifications.visual.enter",
        "notifications.visual.exit",
        "appearance.apply",
        "notifications.visual.reset",
        "appearance.back"
    ],
    "settings.modules": [
        "module.oggi",
        "module.meteo",
        "module.account",
        "module.sport",
        "module.f1",
        "module.motogp",
        "module.casa",
        "module.network"
    ],
    "settings.notifications": [
        "notifications.quiet",
        "notifications.categories"
    ],
    "settings.notifications.quiet": [
        "notifications.quiet.enabled",
        "notifications.quiet.start",
        "notifications.quiet.end"
    ],
    "settings.notifications.categories": [
        "notifications.weatherInterruptions",
        "notifications.accountInterruptions",
        "notifications.sportGoals"
    ],
    "settings.account": [
        "account.warningThreshold",
        "account.criticalThreshold"
    ],
    "settings.integrations": [
        "integration.sport",
        "integration.f1",
        "integration.motogp"
    ],
    "settings.sources": [
        "source.weather",
        "source.alerts",
        "source.account",
        "source.sport",
        "source.f1",
        "source.motogp",
        "source.casa",
        "source.network"
    ],
    "settings.sport": [
        "sport.favouriteTeam",
        "sport.showOnHome",
        "sport.notifications",
        "sport.season",
        "sport.source"
    ],
    "settings.racing": [
        "racing.season",
        "racing.showOnHome",
        "racing.source"
    ]
}

var simpleAppearanceIds = ["appearance.palette","appearance.motion","appearance.theme","appearance.textScale",
    "appearance.revision","appearance.apply","appearance.cancel","appearance.import","appearance.export","appearance.advanced"]
var indexTargets = {appearance:"appearance",system:"display",modules:"modules",notifications:"notifications",
    accountSettings:"account",integrations:"integrations",sources:"sources",casaSettings:"casa",networkSettings:"network"}
var integrationTargets = {sportSettings:"integration.sport",f1:"integration.f1",motogp:"integration.motogp"}
var sourceTargets = {meteo:"source.weather",weather:"source.weather",alerts:"source.alerts",account:"source.account",
    sport:"source.sport",f1:"source.f1",motogp:"source.motogp",casa:"source.casa",network:"source.network"}
var notificationTargets = {notificationQuiet:"notifications.quiet",notificationCategories:"notifications.categories"}
var notificationModes = ["small","large","urgent","badge","inbox","detail"]

function choices(values, labels) {
    return values.map(function(value,index) { return {id:String(value),label:labels ? labels[index] : String(value),value:value} })
}
function setNumber(row,minimum,maximum,step,value) {
    row.control="number";row.minimum=minimum;row.maximum=maximum;row.step=step
    if (value !== undefined) row.value={available:true,value:value,displayText:String(row.value === undefined ? value : row.value)}
}
function setChoice(row,options,value) {
    row.control="choice";row.options=options
    if (value !== undefined) row.value={available:true,value:value,displayText:String(row.value === undefined ? value : row.value)}
}
function setToggle(row,value) {
    row.control="toggle"
    if (value !== undefined) row.value={available:true,value:!!value,displayText:String(row.value === undefined ? value : row.value)}
}
function identity(surface,row,index,options) {
    if (surface === "settings.index") return indexTargets[row.target] || ""
    if (surface === "settings.modules") return options.families[index] ? "module."+options.families[index].id : ""
    if (surface === "settings.integrations") return integrationTargets[row.target] || ""
    if (surface === "settings.sources") return sourceTargets[row.target] || ""
    if (surface === "settings.notifications") return notificationTargets[row.target] || ""
    if (surface === "settings.appearance" && !options.advancedAppearance) return row.id || simpleAppearanceIds[index] || ""
    if (surface === "settings.appearance" && index === 20) return "appearance.simple"
    if (surface === "settings.racing") {
        var suffix=["season","showOnHome","source"][index]
        return suffix ? "racing."+options.racingKind+"."+suffix : ""
    }
    return (canonicalSections[surface] || [])[index] || ""
}
function presentationChoices(appearance,contentId) {
    var registry=appearance.presentationRegistry || {}
    return Object.keys(registry).filter(function(id) { return (registry[id].contentIds || []).indexOf(contentId) >= 0 })
        .map(function(id) { return {id:id,label:registry[id].name || id,value:id} })
}
function recipeChoices(appearance,event,legacyEvent) {
    var registry=appearance.motionRegistry || {}
    return Object.keys(registry).filter(function(id) {
        var events=registry[id].events
        return !events || events.indexOf(event) >= 0 || legacyEvent && events.indexOf(legacyEvent) >= 0
    }).map(function(id) { return {id:id,label:registry[id].name || id,value:id} })
}
function canonicalize(surface,rows,options) {
    if (surface.indexOf("settings.") !== 0) return rows
    options=options || {};options.families=options.families || []
    var backend=options.backend || {},appearance=options.appearance || {},tokens=appearance.tokens || {}
    var busy=options.status === "saving" || options.status === "working"
    var selectedCatalogTheme=(options.themes || []).filter(function(theme) { return theme.id === (options.draft || {}).themeId })[0]
    var adjustments=selectedCatalogTheme && selectedCatalogTheme.adjustments !== undefined ? selectedCatalogTheme.adjustments : appearance.adjustments
    return rows.map(function(raw,index) {
        var row=Object.assign({},raw),id=identity(surface,row,index,options)
        row.id=id || String(row.id || surface+":"+index)
        row.enabled=row.enabled !== false
        row.control="action";row.actionId="settings.activate";row.targetId=row.id
        row.reason=row.enabled ? "" : row.detail || "Operazione non disponibile nello stato corrente"
        var editable=surface !== "settings.index" && surface !== "settings.integrations" && surface !== "settings.notifications" && surface !== "settings.sources"
        if (editable) row.actionId="settings.adjust"
        if (id.indexOf("module.") === 0) setToggle(row,id === "module.oggi" || (options.visibleModules || []).indexOf(id.slice(7)) >= 0)
        if (surface === "settings.sources") { row.actionId="sources.refresh";row.targetId=row.target }
        if (id === "display.mode") setChoice(row,choices(["auto","manual"],["Automatico","Manuale"]),backend.brightnessMode)
        else if (id === "display.manualBrightness") setNumber(row,20,100,5,backend.manualBrightness)
        else if (id === "display.dayBrightness") setNumber(row,20,100,5,backend.dayBrightness)
        else if (id === "display.nightBrightness") setNumber(row,20,100,5,backend.nightBrightness)
        else if (id === "display.dayStart") setNumber(row,0,23,1,backend.dayStartHour)
        else if (id === "display.nightStart") setNumber(row,0,23,1,backend.nightStartHour)
        else if (id === "notifications.quiet.enabled") setToggle(row,backend.quietHoursEnabled)
        else if (id === "notifications.quiet.start") setNumber(row,0,1439,15,backend.quietStartMinute)
        else if (id === "notifications.quiet.end") setNumber(row,0,1439,15,backend.quietEndMinute)
        else if (id === "notifications.weatherInterruptions") setToggle(row,backend.weatherInterruptions)
        else if (id === "notifications.accountInterruptions") setToggle(row,backend.accountInterruptions)
        else if (id === "notifications.sportGoals") setToggle(row,options.sport && options.sport.goalsEnabled)
        else if (id === "sport.notifications") { row.control="action";row.actionId="settings.activate" }
        else if (id === "sport.showOnHome") setToggle(row,options.sport && options.sport.showOnHome)
        else if (id === "sport.season") setChoice(row,choices((options.sport || {}).availableSeasons || []),(options.sport || {}).selectedSeason || (options.sport || {}).season)
        else if (/^racing\.(f1|motogp)\.season$/.test(id)) setChoice(row,choices((options.racing || {}).availableYears || []),(options.racing || {}).selectedYear || (options.racing || {}).year)
        else if (/^racing\.(f1|motogp)\.showOnHome$/.test(id)) setToggle(row,options.racing && options.racing.showOnHome)
        else if (id === "sport.source" || /^racing\.(f1|motogp)\.source$/.test(id) || id === "sport.favouriteTeam") row.actionId="settings.activate"
        else if (id === "account.warningThreshold") setNumber(row,1,backend.accountCriticalPercent-1,5,backend.accountWarningPercent)
        else if (id === "account.criticalThreshold") setNumber(row,backend.accountWarningPercent+1,100,5,backend.accountCriticalPercent)
        if (id === "sport.season" && options.sportUpdating || /^racing\.(f1|motogp)\.season$/.test(id) && (options.racingUpdating || (options.racing || {}).detailLoading)) {
            row.enabled=false;row.reason="Attendere il completamento dell'aggiornamento"
        }
        if (surface === "settings.appearance" || surface === "settings.appearance.notifications") {
            if (busy) { row.enabled=false;row.reason="Attendere il completamento dell'operazione" }
            if (["appearance.apply","appearance.cancel","appearance.reset","appearance.reload","appearance.import","appearance.export"].indexOf(id) >= 0) {
                row.control=id === "appearance.import" || id === "appearance.export" ? "transfer" : "action"
                row.actionId=id;row.targetId=""
            } else if (["appearance.advanced","appearance.simple","appearance.notifications","appearance.back","notifications.visual.reset"].indexOf(id) >= 0) row.actionId="settings.activate"
            else if (id === "appearance.palette") setChoice(row,choices(["auto","day","night"],["Automatica","Giorno","Notte"]),(options.draft || {}).paletteMode || "auto")
            else if (id === "appearance.motion") setChoice(row,choices(["normal","reduced","off"],["Normale","Ridotto","Disattivo"]),(options.draft || {}).motionMode || "off")
            else if (id === "appearance.theme") { setChoice(row,(options.themes || []).map(function(theme) { return {id:theme.id,label:theme.name,value:theme.id} }),(options.draft || {}).themeId);row.control="theme"
                if (selectedCatalogTheme && selectedCatalogTheme.coverageSummary) { row.detail=selectedCatalogTheme.coverageSummary;row.description=selectedCatalogTheme.coverageSummary }
            }
            else if (id === "appearance.textScale") setNumber(row,.85,1.1,.05,tokens["typography.textScale"])
            else if (id === "appearance.cardRadius") setNumber(row,0,24,2,tokens["shape.radiusCard"])
            else if (id === "appearance.density") setChoice(row,choices(["regular","wide"],["Regolare","Ampia"]),tokens["metrics.listRows"] === 4 ? "regular" : "wide")
            else if (id === "appearance.scene") setToggle(row,appearance.scene && appearance.scene.enabled)
            else if (id === "appearance.homeComposition") setChoice(row,presentationChoices(appearance,"home.now"),(appearance.presentations || {})["home.now"])
            else if (id === "appearance.accent") setChoice(row,choices(["#6de0be","#e6c880","#b5d3ff","#efc3e6"]),tokens["colors.accent"])
            else if (["appearance.uiFont","appearance.numbersFont","appearance.clockFont"].indexOf(id) >= 0 || /^notifications\.visual\.(title|body|source)Font$/.test(id)) setChoice(row,choices(options.fontFamilies || []))
            else if (id === "appearance.transitions") setChoice(row,recipeChoices(appearance,"navigate.family",""),((appearance.motion || {})["navigate.family"] || {}).recipe)
            else if (id === "appearance.revision") {
                setChoice(row,(options.revisions || []).map(function(revision) { return {id:revision.digest,label:revision.version,value:revision.digest} }),((options.draft || {}).bundleRevision || {}).digest)
                if (row.options.length < 2) { row.enabled=false;row.reason="Nessun'altra revisione installata per questo tema" }
            }
            else if (id === "notifications.visual.mode") setChoice(row,choices(notificationModes),options.notificationMode || "small")
            else if (id.indexOf("notifications.visual.composition.") === 0) {
                var mode=id.split(".").pop(),content=mode === "small" || mode === "large" ? "alerts.banner."+mode : "alerts."+mode
                setChoice(row,presentationChoices(appearance,content),(appearance.presentations || {})[content])
            } else if (id === "notifications.visual.preview") { row.actionId="appearance.notificationPreview";row.control="action";row.targetId="";row.value={available:true,value:options.notificationMode || "small",displayText:String(row.value)} }
            else if (id === "notifications.visual.padding") setNumber(row,0,64,2,tokens["notifications."+(options.notificationMode || "small")+".padding"])
            else if (id === "notifications.visual.titleSize") setNumber(row,18,72,2,tokens["notifications."+(options.notificationMode || "small")+".titleSize"])
            else if (id === "notifications.visual.bodySize") setNumber(row,16,44,2,tokens["notifications."+(options.notificationMode || "small")+".bodySize"])
            else if (id === "notifications.visual.sourceSize") setNumber(row,16,32,2,tokens["notifications."+(options.notificationMode || "small")+".sourceSize"])
            else if (id === "notifications.visual.radius") setNumber(row,0,40,2,tokens["notifications."+(options.notificationMode || "small")+".radius"])
            else if (id === "notifications.visual.anchor") setChoice(row,choices(["top","bottom","center"],["Alto","Basso","Centro"]),tokens["notifications."+(options.notificationMode || "small")+".anchor"])
            else if (id === "notifications.visual.inboxRows") setNumber(row,1,5,1,tokens["notifications.inbox.rows"])
            else if (id === "notifications.visual.icon" || id === "notifications.visual.source") setToggle(row,tokens["notifications."+(options.notificationMode || "small")+"."+(id === "notifications.visual.icon" ? "showIcon" : "showSource")])
            else if (id === "notifications.visual.enter" || id === "notifications.visual.exit") {
                var exit=id === "notifications.visual.exit",selectedMode=options.notificationMode || "small"
                var prefix=selectedMode === "small" || selectedMode === "large" ? "banner."+selectedMode : "alerts."+selectedMode
                var legacyPrefix=selectedMode === "small" || selectedMode === "large" ? "banner" : "panel"
                setChoice(row,recipeChoices(appearance,prefix+(exit ? ".exit" : ".enter"),legacyPrefix+(exit ? ".exit" : ".enter")))
            }
        }
        if ((id === "appearance.palette" || id === "appearance.textScale") && adjustments !== undefined) {
            var adjustment=id === "appearance.palette" ? "paletteMode" : "textScale"
            if (adjustments.indexOf(adjustment) < 0) {
                row.enabled=false;row.reason=id === "appearance.palette" ? "Palette gestita dal tema" : "Dimensione definita dal tema"
            }
        }
        return row
    })
}
