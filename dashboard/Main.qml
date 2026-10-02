import QtQuick
import "themes"
import "components"

Window {
    id: app
    property StyleFacade style: Theme
    width: 960; height: 640
    minimumWidth: 960; minimumHeight: 640
    maximumWidth: 960; maximumHeight: 640
    visible: true
    visibility: Window.FullScreen
    title: "SmartPC"
    color: app.style.background

    property var keypad: null
    property var dashboardState: null
    readonly property string activeContentId: familyId === "oggi" ? (viewIndex[0] === 0 ? "home.now" : "home.day") : familyId === "meteo" ? (viewIndex[1] === 0 ? "weather.now" : "weather.forecast") : familyId === "account" ? "account.usage" : familyId === "sport" ? (sportView === "LA MIA SQUADRA" ? "sport.team" : "sport.overview") : "racing.overview"
    onActiveContentIdChanged: if (themeService) themeService.setActiveContent(activeContentId)
    readonly property var themeService: dashboardState ? dashboardState.appearance : null
    Binding { target: Theme; property: "service"; value: app.themeService }
    Binding { target: Theme; property: "fallbackNight"; value: app.night }
    onNightChanged: Qt.callLater(function() { if (app.themeService) app.themeService.setVariant(app.night ? "night" : "day") })
    Timer { interval: 0; running: true; onTriggered: if (app.themeService) app.themeService.setVariant(app.night ? "night" : "day") }
    property date now: new Date()
    // Add a family only when its provider and screens are ready.
    readonly property var allFamilies: [
        { id: "oggi", slot: 0, name: "OGGI", views: ["ORA", "GIORNATA"] },
        { id: "meteo", slot: 1, name: "METEO", views: ["ADESSO", "PREVISIONI"] },
        { id: "account", slot: 2, name: "ACCOUNT CHATGPT", views: ["UTILIZZO"] },
        { id: "sport", slot: 3, name: "SPORT · SERIE A", views: app.sportViews },
        { id: "f1", slot: 4, name: "SPORT · F1", views: app.racingViews("f1") },
        { id: "motogp", slot: 5, name: "SPORT · MOTOGP", views: app.racingViews("motogp") }
    ].filter(item => item.id === "sport" ? dashboardState && dashboardState.sportAvailable :
        item.id === "f1" || item.id === "motogp" ? dashboardState && (dashboardState.racingAvailable || []).indexOf(item.id) >= 0 : true)
    readonly property var visibleModules: dashboardState ? dashboardState.visibleModules : ["oggi", "meteo", "account"]
    onVisibleModulesChanged: if (visibleModules.indexOf(familyId) === -1) home()
    readonly property var families: allFamilies.filter(item => visibleModules.indexOf(item.id) !== -1)
    property string familyId: "oggi"
    readonly property int family: Math.max(0, families.findIndex(item => item.id === familyId))
    readonly property var currentFamily: families[family] || allFamilies[0]
    property var viewIndex: [0, 0, 0, 0, 0, 0]
    property string sportView: "PROSSIME"
    property bool sportTeamDetail: false
    property int teamTab: 0
    property int teamIndex: 0
    property int teamPickerIndex: 0
    property bool teamSerieAOnly: false
    property string teamFocusedId: ""
    readonly property var teamState: sportData.favouriteTeam || ({status: "unavailable", source: "FotMob", data: {}})
    readonly property var teamData: teamState.data || ({})
    readonly property var teamPickerRows: [{id: "", name: "Nessuna preferita"}].concat(sportData.teams || [])
    readonly property var teamInfoRows: [
        {title: "Squadra preferita", value: teamData.name || "Nessuna", action: "5 CAMBIA"},
        {title: "Dati della squadra", value: teamState.status === "updating" ? "Aggiornamento…" : "Fonte " + teamState.source, action: "5 AGGIORNA"},
        {title: "Allenatore", value: teamData.coach || "Non disponibile"},
        {title: "Stadio", value: teamData.stadium || "Non disponibile"},
        {title: "Città / capienza", value: (teamData.city || "—") + " · " + (teamData.capacity == null ? "—" : teamData.capacity + " posti")},
        {title: "Serie A · " + (teamData.season || ""), value: teamStandingText()},
        {title: "Bilancio Serie A", value: teamRecordText()},
        {title: "Ultime 5 · tutte le competizioni", value: teamData.form || "Non disponibile"}
    ]
    function teamNumber(v) { return v == null ? "—" : v }
    function teamStandingText() {
        const r = teamData.standing || {}
        return r.position == null ? "Non disponibile" : r.position + "° · " + teamNumber(r.points) + " PT · " + teamNumber(r.played) + " partite"
    }
    function teamRecordText() {
        const r = teamData.standing || {}
        return r.wins == null ? "Non disponibile" : "V " + teamNumber(r.wins) + " · N " + teamNumber(r.draws) + " · P " + teamNumber(r.losses) + " · Gol " + teamNumber(r.goalsFor) + "–" + teamNumber(r.goalsAgainst)
    }
    readonly property var teamRows: teamTab === 2 ? teamInfoRows : teamTab === 3 ? (teamData.squad || []) :
        (teamTab === 1 ? (teamData.results || []) : (teamData.active || []).concat(teamData.upcoming || [])).filter(m => !teamSerieAOnly || m.providerLeagueId === 55)
    onTeamRowsChanged: {
        const retained = teamRows.findIndex(m => (m.canonicalMatchId || m.id || m.title) === teamFocusedId)
        teamIndex = retained >= 0 ? retained : Math.min(teamIndex, Math.max(0, teamRows.length - 1))
    }
    onTeamIndexChanged: {
        const row = teamRows[teamIndex]
        teamFocusedId = row ? (row.canonicalMatchId || row.id || row.title) : ""
    }
    function openTeamPicker() {
        teamPickerIndex = Math.max(0, teamPickerRows.findIndex(t => t.id === sportData.favourite))
        pushOverlay("sportTeamPicker")
    }
    function openTeam() {
        teamTab = 0; teamIndex = 0; teamFocusedId = ""
        if (!sportData.favourite) openTeamPicker()
        else pushOverlay("sportTeam")
    }
    property string sportMatchId: ""
    property int sportIndex: 0
    property string sportFocusedId: ""
    property int sportSettingsIndex: 0
    property string sportRound: ""
    readonly property bool sportIsSerieA: sportMatch.competitionId === "serie_a" || sportMatch.competitionId === "football:55" && sportMatch.providerLeagueId === 55
    readonly property var sportDetailTabs: ["RIEPILOGO", "STATISTICHE", "FORMAZIONI"].concat(sportIsSerieA ? ["FANTACALCIO"] : [])
    readonly property var fantasyState: sportData.fantacalcio || ({status: "unavailable", source: "Redazione Fantacalcio", data: {}})
    readonly property var fantasyData: fantasyState.data && fantasyState.data.selectedMatchId === sportMatch.canonicalMatchId ? fantasyState.data : ({})
    property int fantasyTeamIndex: 0
    property int fantasyPlayerIndex: 0
    property string fantasyFocusedId: ""
    readonly property var fantasyRows: ((fantasyData.teams || [])[fantasyTeamIndex] || {}).players || []
    onFantasyRowsChanged: {
        const retained = fantasyRows.findIndex(p => p.id === fantasyFocusedId)
        fantasyPlayerIndex = retained >= 0 ? retained : Math.min(fantasyPlayerIndex, Math.max(0, fantasyRows.length - 1))
    }
    onFantasyPlayerIndexChanged: fantasyFocusedId = fantasyRows[fantasyPlayerIndex] ? fantasyRows[fantasyPlayerIndex].id : ""
    onSportDetailTabsChanged: Qt.callLater(function() { if (sportDetailPage >= sportDetailTabs.length) sportDetailPage = 0 })
    onSportDetailPageChanged: {
        fantasyTeamIndex = 0; fantasyPlayerIndex = 0; fantasyFocusedId = ""
        Qt.callLater(animateTab)
        Qt.callLater(function() {
            if (!dashboardState) return
            if (overlay === "sportDetail" && sportDetailPage === 3 && sportIsSerieA) dashboardState.selectFantacalcio(sportMatchId)
            else dashboardState.clearFantacalcio()
        })
    }
    property int sportDetailPage: 0
    property int sportDetailOffset: 0
    property int sportListIndex: 0
    property int sportTableIndex: 0
    property int sportOverviewPage: 0
    readonly property var sportRounds: [...new Set(sportFixtures.map(m => m.round).filter(r => !!r))].sort((a,b) => Number(a)-Number(b))
    function openSportList() {
        const source = sportView === "RISULTATI" ? sportData.lastFinished : sportView === "IN CORSO" ? sportOverviewMatches : sportData.upcoming
        sportRound = source && source.length ? source[0].round : ""
        sportFocusedId = ""; sportIndex = 0; sportListIndex = 0; sportTableIndex = 0
        pushOverlay("sportList")
        const first = source && source.length ? sportRows.findIndex(m => m.canonicalMatchId === source[0].canonicalMatchId) : 0
        sportIndex = Math.max(0, first)
    }
    function openSportTable() {
        if (!sportRound) sportRound = (sportData.upcoming || []).length ? sportData.upcoming[0].round : sportData.resultsRound || ""
        sportIndex = Math.min(sportTableIndex, Math.max(0, (sportData.standings || []).length - 1))
        sportFocusedId = ""
        pushOverlay("sportTable")
    }
    function changeSportRound(direction) {
        const current = sportRounds.indexOf(sportRound)
        const next = Math.max(0, Math.min(sportRounds.length - 1, current + direction))
        sportRound = sportRounds[next] || ""
        sportFocusedId = ""; sportIndex = -1
    }
    function switchSportTab() {
        if (overlay === "sportList") sportListIndex = sportIndex
        else sportTableIndex = sportIndex
        sportFocusedId = ""
        overlay = overlay === "sportTable" ? "sportList" : "sportTable"
        sportIndex = overlay === "sportTable" ? sportTableIndex : sportListIndex
    }
    readonly property var sport: dashboardState ? dashboardState.sportState : ({status: "unavailable", source: "FotMob / ESPN", data: {}})
    readonly property var sportData: sport.data || ({})
    readonly property var sportViews: ["PROSSIME"].concat(sportData.hasLiveView || sportView === "IN CORSO" ? ["IN CORSO"] : []).concat(["RISULTATI", "CLASSIFICA", "LA MIA SQUADRA"])
    readonly property var sportFixtures: sportData.fixtures || []
    readonly property var sportOverviewMatches: sportView === "IN CORSO" ? ((sportData.activeMatches || []).length ? sportData.activeMatches : sportMatch.status === "finished" ? [sportMatch] : []) :
        (sportData.upcoming || []).filter(m => !sportData.upcoming[0].round || m.round === sportData.upcoming[0].round)
    readonly property int sportOverviewPages: Math.max(1, Math.ceil(sportOverviewMatches.length / app.style.overviewRows))
    onSportOverviewPagesChanged: sportOverviewPage = Math.min(sportOverviewPage, sportOverviewPages - 1)
    onSportViewChanged: sportOverviewPage = 0
    Timer {
        objectName: "sportOverviewTimer"
        interval: 8000; repeat: true
        running: app.familyId === "sport" && app.overlay === "" && (app.sportView === "PROSSIME" || app.sportView === "IN CORSO") && app.sportOverviewPages > 1
        onTriggered: app.sportOverviewPage = (app.sportOverviewPage + 1) % app.sportOverviewPages
    }
    readonly property var sportMatch: sportTeamDetail ? ((teamData.fixtures || []).find(m => m.canonicalMatchId === sportMatchId) || ({})) : ((overlay === "sportDetail" || overlayStack.indexOf("sportDetail") >= 0 || sportView === "IN CORSO") ? sportFixtures.find(m => m.canonicalMatchId === sportMatchId) : null) ||
        (sportView === "IN CORSO" ? (sportData.activeMatches || [])[0] : (sportData.upcoming || [])[0]) || ({})
    readonly property var sportRows: (overlay === "sportTable" || overlayStack.indexOf("sportTable") >= 0) ? (sportData.standings || []) :
        sportView === "IN CORSO" ? sportOverviewMatches :
        sportRound ? sportFixtures.filter(m => m.round === sportRound) :
        sportView === "RISULTATI" ? (sportData.lastFinished || []) : (sportData.upcoming || [])
    onSportRowsChanged: {
        const retained = sportRows.findIndex(row => (row.canonicalMatchId || row.teamId) === sportFocusedId)
        sportIndex = retained >= 0 ? retained : Math.min(sportIndex, Math.max(0, sportRows.length - 1))
    }
    onSportIndexChanged: {
        const row = sportRows[sportIndex]
        sportFocusedId = row ? (row.canonicalMatchId || row.teamId) : ""
    }
    readonly property bool isRacing: familyId === "f1" || familyId === "motogp"
    readonly property var racingStates: dashboardState ? dashboardState.racingStates : ({})
    readonly property var racing: racingStates[familyId] || ({status: "unavailable", source: "", data: {}})
    readonly property var racingData: racing.data || ({})
    property var racingViewNames: ({f1: "PROGRAMMA", motogp: "PROGRAMMA"})
    readonly property string racingView: racingViewNames[familyId] || "PROGRAMMA"
    function racingViews(kind) {
        const data = (racingStates[kind] || {}).data || ({})
        return ["PROGRAMMA"].concat((data.live || {}).active || racingViewNames[kind] === "IN CORSO" ? ["IN CORSO"] : []).concat(["RISULTATI", "CLASSIFICA"])
    }
    property string racingEventId: ""
    property string racingSessionId: ""
    property int racingIndex: 0
    property string racingFocusedId: ""
    property int racingDetailPage: 0
    property int racingEventPage: 0
    property int racingInfoIndex: 0
    property string racingDriverId: ""
    property bool racingDriverLive: false
    property int racingDriverPage: 0
    property int racingDriverIndex: 0
    property int racingTimingPage: 0
    property int racingResultIndex: 0
    property int racingStandingTab: 0
    property int racingSettingsIndex: 0
    property string racingSettingsKind: "f1"
    readonly property var racingEvent: (racingData.events || []).find(e => e.id === racingEventId) || ({})
    readonly property var racingSession: (racingEvent.sessions || []).find(s => s.id === racingSessionId) || ({})
    readonly property var racingDriver: (racingDriverLive ? (racingData.live || {}).rows || [] : racingSession.results || []).find(r => r.id === racingDriverId) || ({})
    readonly property var racingDriverTabs: racingDriverLive ? ["TEMPI"] : familyId === "f1" ? ["DETTAGLI"].concat(racingSession.kind === "RAC" ? ["SOSTE", "GIRI"] : []).concat(["GOMME"]) : ["DETTAGLI"]
    readonly property string racingDriverPane: racingDriverTabs[racingDriverPage] || "DETTAGLI"
    readonly property var racingDriverRows: racingDriverPane === "SOSTE" ? racingDriver.pitStops || [] : racingDriverPane === "GIRI" ? racingDriver.lapTimes || [] : racingDriverPane === "GOMME" ? racingDriver.stints || [] : racingDriver.detailRows || []
    readonly property var racingInfoRows: overlay === "racingEvent" ? racingEventPage === 1 ? racingEvent.infoRows || [] : racingEvent.summaryRows || [] : overlay === "racingTiming" ? racingTimingPage === 2 ? ((racingData.live || {}).messages || []).map(m => ({label: "Direzione gara", value: m})) : (racingData.live || {}).infoRows || [] : racingSession.infoRows || []
    readonly property var racingRows: overlay === "racingTable" || overlayStack.indexOf("racingTable") >= 0 ?
        (racingStandingTab === 1 && familyId === "f1" ? racingData.constructors || [] : racingData.standings || []) :
        overlay === "racingEvent" || overlayStack.indexOf("racingEvent") >= 0 || overlay === "racingSession" ? racingEvent.sessions || [] :
        racingView === "RISULTATI" ? racingData.past || [] : racingView === "IN CORSO" ? (racingData.live || {}).rows || [] : racingData.events || []
    onRacingRowsChanged: {
        const retained = racingRows.findIndex(row => row.id === racingFocusedId)
        racingIndex = retained >= 0 ? retained : Math.min(racingIndex, Math.max(0, racingRows.length - 1))
    }
    onRacingIndexChanged: racingFocusedId = racingRows[racingIndex] ? racingRows[racingIndex].id : ""
    function openRacing() {
        racingStandingTab = 0; racingIndex = 0; racingFocusedId = ""
        if (racingView === "CLASSIFICA") pushOverlay("racingTable")
        else if (racingView === "IN CORSO") { racingTimingPage = 0; racingInfoIndex = 0; pushOverlay("racingTiming") }
        else {
            pushOverlay("racingList")
            const initial = racingView === "RISULTATI" ? racingData.lastEvent : racingData.nextEvent
            if (initial) racingIndex = Math.max(0, racingRows.findIndex(e => e.id === initial.id))
        }
    }
    property string overlay: ""
    property var overlayStack: []
    property int menuIndex: 0
    property int settingsIndex: 0
    property int optionIndex: 0
    property int infoPage: 0
    property int infoIndex: 0
    property int modulesIndex: 0
    property int systemIndex: 0
    property int notificationIndex: 0
    property int quietIndex: 0
    property int categoryIndex: 0
    property int sourceIndex: 0
    property int alertIndex: 0
    property var selectedAlert: ({})
    property int accountIndex: 0
    property bool diagnostics: false
    property int frames: 0
    property real firstFrame: 0
    property real lastFrame: 0
    property real measuredFps: 0
    property real p95Ms: 0
    property var frameIntervals: []

    readonly property color ink: app.style.textPrimary
    readonly property color muted: app.style.textSecondary
    readonly property color accent: app.style.accent
    readonly property color panel: app.style.surface
    readonly property color edge: app.style.border
    readonly property var weekdays: ["domenica", "lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato"]
    readonly property var months: ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
    readonly property var weather: dashboardState ? dashboardState.weatherState : ({version: 1, status: "unavailable", source: "Open-Meteo", updatedAt: 0, data: {}, error: ""})
    readonly property var weatherData: weather.data || ({})
    readonly property var account: dashboardState ? dashboardState.accountState : ({version: 1, status: "unavailable", source: "Codex App Server", updatedAt: 0, data: {}, error: ""})
    readonly property var accountData: account.data || ({})
    readonly property var accountWindows: accountData.windows || []
    onAccountWindowsChanged: accountIndex = Math.min(accountIndex, Math.max(0, accountWindows.length - 2))
    readonly property int accountWarningPercent: dashboardState ? dashboardState.accountWarningPercent : 80
    readonly property int accountCriticalPercent: dashboardState ? dashboardState.accountCriticalPercent : 95
    readonly property var nextEvent: dashboardState ? dashboardState.nextRelevantEvent : ({})
    readonly property bool hasEvent: !!nextEvent.title
    readonly property var events: dashboardState ? dashboardState.eventsState : ({inbox: [], urgent: {}, visibleBanner: {}})
    readonly property var alertItems: events.inbox || []
    readonly property int unreadAlertCount: events.unreadCount || 0
    readonly property var urgentEvent: events.urgent || ({})
    readonly property var bannerEvent: events.visibleBanner || ({})
    onAlertItemsChanged: alertIndex = Math.min(alertIndex, Math.max(0, alertItems.length - 1))
    readonly property int dayStartHour: dashboardState ? dashboardState.dayStartHour : 7
    readonly property int nightStartHour: dashboardState ? dashboardState.nightStartHour : 21
    readonly property bool daytime: dayStartHour < nightStartHour
                                    ? now.getHours() >= dayStartHour && now.getHours() < nightStartHour
                                    : now.getHours() >= dayStartHour || now.getHours() < nightStartHour
    readonly property bool night: dashboardState && dashboardState.nightMode === "night"
                                  || (!dashboardState || dashboardState.nightMode === "auto") && !daytime
    readonly property int minuteOfDay: now.getHours()*60+now.getMinutes()
    readonly property bool quietActive: dashboardState && dashboardState.quietHoursEnabled &&
        (dashboardState.quietStartMinute < dashboardState.quietEndMinute
        ? minuteOfDay >= dashboardState.quietStartMinute && minuteOfDay < dashboardState.quietEndMinute
        : minuteOfDay >= dashboardState.quietStartMinute || minuteOfDay < dashboardState.quietEndMinute)
    readonly property int brightnessPercent: dashboardState
        ? (dashboardState.brightnessMode === "manual" ? dashboardState.manualBrightness
           : (daytime ? dashboardState.dayBrightness : dashboardState.nightBrightness))
        : 100
    readonly property var menuItems: ["Comandi", "Impostazioni", "Informazioni", "Diagnostica"]
    readonly property var settingsItems: settingsPanel.entries.map(row => row.title)

    function two(value) { return (value < 10 ? "0" : "") + value }
    function timeText() { return two(now.getHours()) + ":" + two(now.getMinutes()) }
    function dateText() { return weekdays[now.getDay()] + " " + now.getDate() + " " + months[now.getMonth()] + " " + now.getFullYear() }
    function quietTime(value) { return two(Math.floor(value / 60)) + ":" + two(value % 60) }
    function eventStamp(value) {
        if (!value) return "—"
        const d = new Date(value * 1000)
        return two(d.getDate()) + "/" + two(d.getMonth() + 1) + " " + two(d.getHours()) + ":" + two(d.getMinutes())
    }
    function eventWhen(value) {
        if (!value || !value.startsAt) return ""
        const start = new Date(value.startsAt * 1000)
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
        const tomorrow = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1)
        if (start >= tomorrow && start < new Date(today.getFullYear(), today.getMonth(), today.getDate() + 2)) return "DOMANI"
        if (start >= today && start < tomorrow) return "OGGI"
        return two(start.getDate()) + "/" + two(start.getMonth() + 1)
    }
    function notificationValue(index) {
        if (!dashboardState) return "—"
        if (index === 0) return dashboardState.quietHoursEnabled ? "ATTIVA" : "DISATTIVA"
        if (index === 1) return quietTime(dashboardState.quietStartMinute)
        if (index === 2) return quietTime(dashboardState.quietEndMinute)
        if (index === 3) return dashboardState.weatherInterruptions ? "ATTIVE" : "DISATTIVE"
        return dashboardState.accountInterruptions ? "ATTIVE" : "DISATTIVE"
    }
    function updatedText() {
        if (!weather.updatedAt) return "DATO ASSENTE"
        const d = new Date(weather.updatedAt * 1000)
        return "AGG. " + two(d.getDate()) + "/" + two(d.getMonth() + 1) + " " + two(d.getHours()) + ":" + two(d.getMinutes())
    }
    function weatherStatus() {
        if (weather.status === "offline") return "OFFLINE · " + updatedText()
        if (weather.status === "error") return "ERRORE · NESSUN DATO"
        if (weather.status === "updating") return "AGGIORNAMENTO · " + updatedText()
        if (weather.status === "stale") return "CACHE · " + updatedText()
        if (weather.status === "active") return updatedText()
        return "IN ATTESA"
    }
    function viewName() {
        return isRacing ? racingView : familyId === "sport" ? sportView : currentFamily.views[viewIndex[currentFamily.slot] || 0]
    }
    function systemValue(index) {
        if (!dashboardState) return "—"
        if (index === 0) return dashboardState.nightMode.toUpperCase()
        if (index === 1) return dashboardState.brightnessMode === "auto" ? "AUTO" : "MANUALE"
        if (index === 2) return dashboardState.manualBrightness + "%"
        if (index === 3) return dashboardState.dayBrightness + "%"
        if (index === 4) return dashboardState.nightBrightness + "%"
        if (index === 5) return two(dashboardState.dayStartHour) + ":00"
        if (index === 6) return two(dashboardState.nightStartHour) + ":00"
        return ""
    }
    function animateMove(direction, vertical) {
        navigationMotion.play(contentLayer, vertical ? "navigate.view" : "navigate.family", direction, vertical)
    }

    function navigateFamily(direction) {
        familyId = families[(family + direction + families.length) % families.length].id
        animateMove(direction)
    }
    function navigateView(direction) {
        const indices = viewIndex.slice()
        const slot = currentFamily.slot
        const count = currentFamily.views.length
        const current = isRacing ? currentFamily.views.indexOf(racingView) : familyId === "sport" ? currentFamily.views.indexOf(sportView) : (indices[slot] || 0)
        indices[slot] = (current + direction + count) % count
        viewIndex = indices
        if (isRacing) {
            const names = Object.assign({}, racingViewNames)
            names[familyId] = currentFamily.views[indices[slot]]; racingViewNames = names
        }
        if (familyId === "sport") { sportView = currentFamily.views[indices[slot]]; sportMatchId = sportView === "IN CORSO" && (sportData.activeMatches || []).length ? sportData.activeMatches[0].canonicalMatchId : "" }
        animateMove(direction, true)
    }
    function home() {
        if (themeService && themeService.editing) themeService.cancel()
        if (dashboardState) { dashboardState.clearSportTeamSelection(); dashboardState.clearFantacalcio() }
        sportTeamDetail = false
        if (isRacing && dashboardState) dashboardState.clearRacingSelection(familyId)
        overlay = ""
        overlayStack = []
        familyId = "oggi"
        const indices = viewIndex.slice()
        indices[0] = 0
        viewIndex = indices
        animateMove(-1)
    }
    function pushOverlay(target) {
        const stack = overlayStack.slice()
        stack.push(overlay)
        overlayStack = stack
        overlay = target
        if (target === "appearance" && themeService) themeService.beginEdit()
    }
    function popOverlay() {
        if ((overlay === "racingEvent" || overlay === "racingTiming") && dashboardState) dashboardState.clearRacingSelection(familyId)
        if (overlay === "sportDetail" && dashboardState) dashboardState.clearFantacalcio()
        if (overlay === "sportDetail" && sportTeamDetail && dashboardState) dashboardState.clearSportTeamSelection()
        if (overlay === "sportTable") sportTableIndex = sportIndex
        if (overlay === "commands" && dashboardState) dashboardState.markCommandsSeen()
        if (overlay === "appearance" && themeService && themeService.editing) themeService.cancel()
        const previous = overlay
        const stack = overlayStack.slice()
        overlay = stack.length ? stack.pop() : ""
        overlayStack = stack
        if (previous === "racingDriver" && !racingDriverLive && dashboardState) dashboardState.selectRacing(familyId, racingEventId, racingSessionId)
        if (previous === "sportDetail") sportTeamDetail = false
        if (previous === "racingEvent" && overlay === "racingList") {
            racingFocusedId = racingEventId
            racingIndex = Math.max(0, racingRows.findIndex(e => e.id === racingEventId))
        }
        if (previous === "racingSession" && overlay === "racingEvent") {
            racingFocusedId = racingSessionId
            racingIndex = Math.max(0, racingRows.findIndex(s => s.id === racingSessionId))
        }
    }
    function back() {
        if (overlay !== "") popOverlay()
        else home()
    }
    function selectMenu() {
        if (menuIndex === 0) pushOverlay("commands")
        else if (menuIndex === 1) { settingsIndex = 0; pushOverlay("settings") }
        else if (menuIndex === 2) { infoPage = 0; infoIndex = 0; pushOverlay("info") }
        else if (menuIndex === 3) { toggleDiagnostics(); overlay = ""; overlayStack = [] }
    }
    function selectSettings() { settingsPanel.activate(1) }
    function openSourceSettings(source) {
        pushOverlay("sources")
        sourceIndex = Math.max(0, settingsPanel.sourceEntries.findIndex(row => row.target === source))
    }
    function openSelectedAlert() {
        if (!alertItems.length) return
        selectedAlert = alertItems[alertIndex]
        if (dashboardState) dashboardState.markEventSeen(selectedAlert.id)
        pushOverlay("alertDetail")
    }
    function toggleModule(index) {
        const moduleId = allFamilies[index].id
        if (moduleId === "oggi" || !dashboardState) return
        if (familyId === moduleId && visibleModules.indexOf(moduleId) !== -1) familyId = "oggi"
        dashboardState.toggleModuleVisibility(moduleId)
    }
    function toggleDiagnostics() {
        diagnostics = !diagnostics
        frames = 0; firstFrame = 0; lastFrame = 0; frameIntervals = []
        measuredFps = 0; p95Ms = 0
    }
    function activateKey(position) {
        if (urgentEvent.id) {
            if (position === 7) { dashboardState.dismissEvent(urgentEvent.id); return }
            if (position === 1) { dashboardState.dismissEvent(urgentEvent.id); home(); return }
            if (position === 5) {
                selectedAlert = urgentEvent
                dashboardState.dismissEvent(urgentEvent.id)
                pushOverlay("alertDetail")
            }
            return
        }
        if (position === 1) { home(); return }
        if (position === 7) { back(); return }
        if (position === 3) {
            if (overlay === "alerts") popOverlay()
            else pushOverlay("alerts")
            return
        }
        if (position === 9) {
            if (overlay === "menu") popOverlay()
            else pushOverlay("menu")
            return
        }
        if (overlay === "menu") {
            if (position === 2) menuIndex = Math.max(0, menuIndex - 1)
            else if (position === 8) menuIndex = Math.min(menuItems.length - 1, menuIndex + 1)
            else if (position === 5) selectMenu()
            return
        }
        if (settingsPanel.handleKey(position) || deviceInfo.handleKey(position)) return
        if (overlay === "alerts") {
            if (alertItems.length) {
                if (position === 2) alertIndex = Math.max(0, alertIndex - 1)
                else if (position === 8) alertIndex = Math.min(alertItems.length - 1, alertIndex + 1)
                else if (position === 5) openSelectedAlert()
            }
            return
        }
        if (overlay === "racingSettings") {
            if (position === 2) racingSettingsIndex = Math.max(0, racingSettingsIndex - 1)
            else if (position === 8) racingSettingsIndex = Math.min(2, racingSettingsIndex + 1)
            else if (position === 5 && racingSettingsIndex === 2) openSourceSettings(racingSettingsKind)
            else if ((position === 4 || position === 5 || position === 6) && racingSettingsIndex < 2) dashboardState.adjustRacingSetting(racingSettingsKind, racingSettingsIndex, position === 4 ? -1 : 1)
            return
        }
        if (overlay === "racingSession") {
            if (position === 4 || position === 6) { racingDetailPage = 1 - racingDetailPage; racingInfoIndex = 0 }
            else if (position === 2) { if (racingDetailPage === 0) racingResultIndex = Math.max(0, racingResultIndex - 1); else racingInfoIndex = Math.max(0, racingInfoIndex - 1) }
            else if (position === 8) { if (racingDetailPage === 0) racingResultIndex = Math.min(Math.max(0, (racingSession.results || []).length - 1), racingResultIndex + 1); else racingInfoIndex = Math.min(Math.max(0, racingInfoRows.length - 1), racingInfoIndex + 1) }
            else if (position === 5 && racingDetailPage === 0 && (racingSession.results || []).length) {
                racingDriverId = racingSession.results[racingResultIndex].id; racingDriverLive = false; racingDriverPage = 0; racingDriverIndex = 0
                dashboardState.selectRacingDriver(familyId, racingEventId, racingSessionId, racingDriverId)
                pushOverlay("racingDriver")
            } else if (position === 5) dashboardState.refreshRacingDetails(familyId)
            return
        }
        if (overlay === "racingDriver") {
            if (position === 4 || position === 6) { racingDriverPage = (racingDriverPage + (position === 4 ? racingDriverTabs.length - 1 : 1)) % racingDriverTabs.length; racingDriverIndex = 0 }
            else if (position === 2) racingDriverIndex = Math.max(0, racingDriverIndex - 1)
            else if (position === 8) racingDriverIndex = Math.min(Math.max(0, racingDriverRows.length - 1), racingDriverIndex + 1)
            else if (position === 5 && !racingDriverLive) dashboardState.refreshRacingDetails(familyId)
            return
        }
        if (overlay === "racingList" || overlay === "racingEvent" || overlay === "racingTable" || overlay === "racingTiming") {
            if (overlay === "racingTiming" && (position === 4 || position === 6)) { racingTimingPage = (racingTimingPage + (position === 4 ? 2 : 1)) % 3; racingInfoIndex = 0; return }
            if (overlay === "racingTiming" && racingTimingPage !== 0) {
                if (position === 2) racingInfoIndex = Math.max(0, racingInfoIndex - 1)
                else if (position === 8) racingInfoIndex = Math.min(Math.max(0, racingInfoRows.length - 1), racingInfoIndex + 1)
                return
            }
            if (overlay === "racingEvent" && (position === 4 || position === 6)) { racingEventPage = (racingEventPage + (position === 4 ? 2 : 1)) % 3; racingInfoIndex = 0; return }
            if (overlay === "racingEvent" && racingEventPage !== 0) {
                if (position === 2) racingInfoIndex = Math.max(0, racingInfoIndex - 1)
                else if (position === 8) racingInfoIndex = Math.min(Math.max(0, racingInfoRows.length - 1), racingInfoIndex + 1)
                else if (position === 5) dashboardState.refreshRacingDetails(familyId)
                return
            }
            if (position === 2) racingIndex = Math.max(0, racingIndex - 1)
            else if (position === 8) racingIndex = Math.min(Math.max(0, racingRows.length - 1), racingIndex + 1)
            else if (overlay === "racingTable" && familyId === "f1" && (position === 4 || position === 6)) { racingFocusedId = ""; racingStandingTab = 1 - racingStandingTab; racingIndex = 0 }
            else if (position === 5 && racingRows.length) {
                if (overlay === "racingList") {
                    racingEventId = racingRows[racingIndex].id; racingSessionId = ""; racingFocusedId = ""; racingIndex = 0; racingEventPage = 0; racingInfoIndex = 0
                    dashboardState.selectRacing(familyId, racingEventId, "")
                    pushOverlay("racingEvent")
                } else if (overlay === "racingEvent") {
                    racingSessionId = racingRows[racingIndex].id; racingDetailPage = 0; racingResultIndex = 0; racingInfoIndex = 0
                    dashboardState.selectRacing(familyId, racingEventId, racingSessionId)
                    pushOverlay("racingSession")
                } else if (overlay === "racingTiming") {
                    racingDriverId = racingRows[racingIndex].id; racingDriverLive = true; racingDriverPage = 0; racingDriverIndex = 0
                    pushOverlay("racingDriver")
                }
            }
            return
        }
        if (overlay === "sportTeamPicker") {
            if (position === 2) teamPickerIndex = Math.max(0, teamPickerIndex - 1)
            else if (position === 8) teamPickerIndex = Math.min(teamPickerRows.length - 1, teamPickerIndex + 1)
            else if (position === 5 && teamPickerRows.length) {
                dashboardState.setSportFavourite(teamPickerRows[teamPickerIndex].id)
                popOverlay()
                teamIndex = 0; teamFocusedId = ""
                if (overlay === "" && sportData.favourite) pushOverlay("sportTeam")
            }
            return
        }
        if (overlay === "sportTeam") {
            if (!sportData.favourite) { if (position === 5) openTeamPicker(); return }
            if (position === 2) teamIndex = Math.max(teamTab < 2 ? -1 : 0, teamIndex - 1)
            else if (position === 8) teamIndex = Math.min(Math.max(0, teamRows.length - 1), teamIndex + 1)
            else if (position === 4 || position === 6) {
                if (teamIndex === -1 && teamTab < 2) { teamSerieAOnly = !teamSerieAOnly; teamFocusedId = "" }
                else { teamTab = (teamTab + (position === 4 ? 3 : 1)) % 4; teamIndex = 0; teamFocusedId = "" }
            } else if (position === 5) {
                if (teamIndex === -1 && teamTab < 2) { teamSerieAOnly = !teamSerieAOnly; teamFocusedId = "" }
                else if (teamTab === 2 && teamIndex === 0) openTeamPicker()
                else if (teamTab === 2 && teamIndex === 1) dashboardState.refreshSportTeam()
                else if (teamTab < 2 && teamRows[teamIndex]) {
                    sportMatchId = teamRows[teamIndex].canonicalMatchId; sportTeamDetail = true
                    sportDetailPage = 0; sportDetailOffset = 0
                    dashboardState.selectTeamMatch(sportMatchId); pushOverlay("sportDetail")
                }
            }
            return
        }
        if (overlay === "sportSettings") {
            if (position === 2) sportSettingsIndex = Math.max(0, sportSettingsIndex - 1)
            else if (position === 8) sportSettingsIndex = Math.min(4, sportSettingsIndex + 1)
            else if (position === 5 && sportSettingsIndex === 0) openTeamPicker()
            else if (position === 5 && sportSettingsIndex === 2) { pushOverlay("notificationCategories"); categoryIndex = 2 }
            else if (position === 5 && sportSettingsIndex === 4) openSourceSettings("sport")
            else if ((position === 4 || position === 5 || position === 6) && sportSettingsIndex < 4 && sportSettingsIndex !== 2) dashboardState.adjustSportSetting(sportSettingsIndex, position === 4 ? -1 : 1)
            return
        }
        if (overlay === "sportList" || overlay === "sportTable") {
            if (position === 2) sportIndex = Math.max(overlay === "sportList" && sportView !== "IN CORSO" && sportRounds.length ? -1 : 0, sportIndex - 1)
            else if (position === 8) sportIndex = Math.min(Math.max(0, sportRows.length - 1), sportIndex + 1)
            else if (position === 4 || position === 6) {
                if (overlay === "sportList" && sportIndex === -1) changeSportRound(position === 4 ? -1 : 1)
                else switchSportTab()
            }
            else if (position === 5 && overlay === "sportList" && sportIndex === -1) sportIndex = 0
            else if (position === 5 && overlay === "sportList" && sportRows.length) {
                sportTeamDetail = false
                sportMatchId = sportRows[sportIndex].canonicalMatchId
                sportDetailPage = 0; sportDetailOffset = 0
                dashboardState.selectSportMatch(sportMatchId)
                pushOverlay("sportDetail")
            }
            return
        }
        if (overlay === "sportDetail") {
            if (sportDetailPage === 3 && position !== 4 && position !== 6) {
                if (position === 2) fantasyPlayerIndex = Math.max(-1, fantasyPlayerIndex - 1)
                else if (position === 8) fantasyPlayerIndex = Math.min(Math.max(0, fantasyRows.length - 1), fantasyPlayerIndex + 1)
                else if (position === 5) {
                    if (fantasyPlayerIndex === -1) dashboardState.refreshFantacalcio()
                    else { fantasyTeamIndex = 1 - fantasyTeamIndex; fantasyPlayerIndex = 0; fantasyFocusedId = "" }
                }
                return
            }
            if (position === 4 || position === 6) {
                sportDetailPage = (sportDetailPage + (position === 4 ? sportDetailTabs.length - 1 : 1)) % sportDetailTabs.length
                sportDetailOffset = 0
            } else if (position === 2) sportDetailOffset = Math.max(0, sportDetailOffset - 1)
            else if (position === 8) {
                const count = sportDetailPage === 0 ? (sportMatch.events || []).length : 0
                sportDetailOffset = Math.min(Math.max(0, count - 4), sportDetailOffset + 1)
            } else if (position === 5) { if (sportTeamDetail) dashboardState.selectTeamMatch(sportMatchId); else dashboardState.selectSportMatch(sportMatchId) }
            return
        }
        if (overlay !== "") return
        if (position === 4) navigateFamily(-1)
        else if (position === 6) navigateFamily(1)
        else if (currentFamily.id === "account") {
            if (position === 2) accountIndex = Math.max(0, accountIndex - 1)
            else if (position === 8) accountIndex = Math.min(Math.max(0, accountWindows.length - 2), accountIndex + 1)
        }
        else if (position === 2) navigateView(-1)
        else if (position === 8) navigateView(1)
        else if (position === 5) {
            if (isRacing) openRacing()
            else if (familyId === "sport") { if (sportView === "LA MIA SQUADRA") openTeam(); else if (sportView === "CLASSIFICA") openSportTable(); else openSportList() }
            else pushOverlay("detail")
        }
    }

    Connections {
        target: app.keypad
        function onKeyPressed(position) { app.activateKey(position) }
    }
    Component.onCompleted: {
        if (themeService) themeService.setActiveContent(activeContentId)
        if (dashboardState && dashboardState.firstRun) pushOverlay("commands")
        if (dashboardState) dashboardState.setBannerAvailable(overlay === "")
    }
    onOverlayChanged: if (dashboardState) {
        dashboardState.setBannerAvailable(overlay === "")
        dashboardState.setSystemInfoVisible(overlay === "info")
    }
    function syncClock() {
        const d = new Date()
        if (d.getMinutes() !== app.now.getMinutes() || d.getDate() !== app.now.getDate()) {
            app.now = d
        }
    }
    Timer { objectName: "clockTimer"; interval: 1000; repeat: true; running: true; onTriggered: app.syncClock() }
    onFrameSwapped: {
        if (!diagnostics) return
        const stamp = Date.now()
        if (firstFrame === 0) firstFrame = stamp
        if (lastFrame !== 0) frameIntervals.push(stamp - lastFrame)
        lastFrame = stamp
        frames += 1
    }
    Timer {
        interval: 5000; repeat: true; running: app.diagnostics
        onTriggered: {
            if (app.frames > 1 && app.lastFrame > app.firstFrame) {
                app.measuredFps = (app.frames - 1) * 1000 / (app.lastFrame - app.firstFrame)
                const sorted = app.frameIntervals.slice().sort((a, b) => a - b)
                app.p95Ms = sorted[Math.floor((sorted.length - 1) * 0.95)] || 0
            } else { app.measuredFps = 0; app.p95Ms = 0 }
            app.frames = 0; app.firstFrame = 0; app.lastFrame = 0; app.frameIntervals = []
        }
    }

    Item {
        anchors.fill: parent
        objectName: "inputOwner"
        focus: true
        Keys.onPressed: event => {
            if (event.key === Qt.Key_Left) app.activateKey(4)
            else if (event.key === Qt.Key_Right) app.activateKey(6)
            else if (event.key === Qt.Key_Up) app.activateKey(2)
            else if (event.key === Qt.Key_Down) app.activateKey(8)
            else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) app.activateKey(5)
            else if (event.key === Qt.Key_Escape || event.key === Qt.Key_Backspace) app.activateKey(7)
            else if (event.key >= Qt.Key_1 && event.key <= Qt.Key_9) app.activateKey(event.key - Qt.Key_1 + 1)
            else if (event.key === Qt.Key_D) app.toggleDiagnostics()
            else if (app.dashboardState && app.dashboardState.demo && event.key === Qt.Key_F12) devPanel.visible = !devPanel.visible
            else return
            event.accepted = true
        }
    }

    Rectangle { x: 0; y: 0; width: 960; height: 5; color: app.accent }
    AppText { style: app.style; x: 44; y: 26; text: app.currentFamily.name + " · " + app.viewName(); color: app.accent; font.pixelSize: app.style.font35; font.weight: (true ) ? app.style.headingWeight : app.style.bodyWeight}
    AppText { style: app.style; x: 790; y: 33; width: 125; horizontalAlignment: Text.AlignRight; text: (app.family + 1) + "/" + app.families.length + "  ·  " + ((app.isRacing ? app.currentFamily.views.indexOf(app.racingView) : app.familyId === "sport" ? app.sportViews.indexOf(app.sportView) : (app.viewIndex[app.currentFamily.slot] || 0)) + 1) + "/" + app.currentFamily.views.length; color: app.muted; font.pixelSize: app.style.font23 }

    Item {
        id: contentLayer
        objectName: "contentLayer"
        x: 0; y: 90; width: 960; height: 455
        ViewHost { objectName: "homeNow"; contentId: "home.now"; controller: app; style: app.style; active: app.familyId === "oggi" && app.viewIndex[0] === 0; interactive: active && app.overlay === "" && !app.urgentEvent.id; x: 44 }
        ViewHost { objectName: "homeDay"; contentId: "home.day"; controller: app; style: app.style; active: app.familyId === "oggi" && app.viewIndex[0] === 1; interactive: active && app.overlay === "" && !app.urgentEvent.id; x: 44 }
        ViewHost { objectName: "weatherNow"; contentId: "weather.now"; controller: app; style: app.style; active: app.familyId === "meteo" && app.viewIndex[1] === 0; interactive: active && app.overlay === "" && !app.urgentEvent.id; x: 44 }
        ViewHost { objectName: "weatherForecast"; contentId: "weather.forecast"; controller: app; style: app.style; active: app.familyId === "meteo" && app.viewIndex[1] === 1; interactive: active && app.overlay === "" && !app.urgentEvent.id; x: 44 }
        ViewHost { objectName: "racingPanel"; contentId: "racing.overview"; controller: app; style: app.style; active: app.isRacing; interactive: active && app.overlay === "" && !app.urgentEvent.id; x: 44 }
        ViewHost { objectName: "sportTeamPanel"; contentId: "sport.team"; controller: app; style: app.style; active: app.familyId === "sport" && app.sportView === "LA MIA SQUADRA"; interactive: active && app.overlay === "" && !app.urgentEvent.id; x: 44 }
        ViewHost { objectName: "sportPanel"; contentId: "sport.overview"; controller: app; style: app.style; active: app.familyId === "sport" && app.sportView !== "LA MIA SQUADRA"; interactive: active && app.overlay === "" && !app.urgentEvent.id; x: 44 }
        ViewHost { objectName: "accountPanel"; contentId: "account.usage"; controller: app; style: app.style; active: app.familyId === "account"; interactive: active && app.overlay === "" && !app.urgentEvent.id; x: 44 }
    }

    AppText { style: app.style; x: 44; y: 614; width: 872; font.pixelSize: app.style.font18; color: SemanticStyle.warning; visible: (app.dashboardState && !!app.dashboardState.themeRecoveryError || app.themeService && app.themeService.status === "recovery") && !app.urgentEvent.id; text: app.dashboardState && app.dashboardState.themeRecoveryError ? "ASPETTO DI RECUPERO · ripristinare il pacchetto software" : "ASPETTO DI RECUPERO · controllare Impostazioni → Aspetto" }
    MotionController { id: navigationMotion }
    MotionController { id: tabMotion }
    function animateTab() {
        if (!urgentEvent.id && overlay !== "") tabMotion.play(overlay === "sportTeam" ? teamOverlay : overlay.indexOf("racing") === 0 ? racingOverlay : sportOverlay,"tab.change",1,false)
    }
    onTeamTabChanged: animateTab()
    onRacingStandingTabChanged: animateTab()
    SceneHost { style: app.style; familyId: app.familyId; suspended: app.overlay !== "" || !!app.urgentEvent.id || app.night || app.quietActive }
    onUrgentEventChanged: if (urgentEvent.id) { navigationMotion.settle(); tabMotion.settle() }

    Rectangle { x: 44; y: 558; width: 872; height: 2; color: app.style.divider }
    AppText { style: app.style; x: 46; y: 578; text: "4/6  ARGOMENTO"; color: app.muted; font.pixelSize: app.style.font25 }
    AppText { style: app.style; x: 351; y: 578; text: app.familyId === "account" ? (app.accountWindows.length > 2 ? "2/8  SCORRI" : "") : "2/8  VISTA"; color: app.muted; font.pixelSize: app.style.font25 }
    AppText { style: app.style; x: 669; y: 578; text: app.familyId === "account" ? "9  MENU" : app.isRacing ? (app.racingView === "CLASSIFICA" ? "5 CLASSIFICA" : "5 APRI") : app.familyId === "sport" ? (app.sportView === "LA MIA SQUADRA" ? "5  SQUADRA" : app.sportView === "CLASSIFICA" ? "5  CLASSIFICA" : "5  PARTITE") : "5  DETTAGLI"; color: app.accent; font.pixelSize: app.style.font25 }

    UnreadAlertsBadge { style: app.style;
        dashboard: app
        visible: app.familyId === "oggi" && app.overlay === "" && app.unreadAlertCount > 0 && !app.bannerEvent.id && !app.urgentEvent.id
    }
    AnimatedLayer {
        anchors.fill: parent; active: !settingsPanel.active && app.overlay !== "info" && app.overlay !== "" && app.overlay.indexOf("sport") !== 0 && app.overlay.indexOf("racing") !== 0; preempted: !!app.urgentEvent.id
        eventPrefix: "panel"
        DashboardOverlay { style: parent.style; dashboard: app; visible: true; anchors.fill: parent }
    }
    AnimatedLayer {
        anchors.fill: parent; active: settingsPanel.active; preempted: !!app.urgentEvent.id
        eventPrefix: "panel"
        SettingsPanel { style: parent.style; id: settingsPanel; dashboard: app; visible: true; anchors.fill: parent }
    }
    AnimatedLayer {
        anchors.fill: parent; active: app.overlay === "info"; preempted: !!app.urgentEvent.id
        eventPrefix: "panel"
        DeviceInfo { style: parent.style; id: deviceInfo; dashboard: app; visible: true; anchors.fill: parent }
    }
    AnimatedLayer {
        anchors.fill: parent; active: app.overlay.indexOf("racing") === 0; preempted: !!app.urgentEvent.id
        eventPrefix: "panel"
        MotorsportOverlay { id: racingOverlay; style: parent.style; dashboard: app; visible: true; anchors.fill: parent }
    }
    AnimatedLayer {
        anchors.fill: parent; active: app.overlay.indexOf("sportTeam") === 0; preempted: !!app.urgentEvent.id
        eventPrefix: "panel"
        SportTeamOverlay { id: teamOverlay; style: parent.style; dashboard: app; visible: true; anchors.fill: parent }
    }
    AnimatedLayer {
        anchors.fill: parent; active: app.overlay.indexOf("sport") === 0 && app.overlay.indexOf("sportTeam") !== 0; preempted: !!app.urgentEvent.id
        eventPrefix: "panel"
        SportOverlay { id: sportOverlay; style: parent.style; dashboard: app; visible: true; anchors.fill: parent }
    }
    AnimatedLayer {
        anchors.fill: parent; active: !!app.bannerEvent.id && app.bannerEvent.bannerSize !== "large" && app.overlay === "" && !app.urgentEvent.id; preempted: !!app.urgentEvent.id
        eventPrefix: "banner"; exitAllowed: !app.bannerEvent.id && app.overlay === ""
        EventBanner { style: parent.style;
            dashboard: app
            visible: true
        }
    }
    AnimatedLayer {
        anchors.fill: parent; active: !!app.bannerEvent.id && app.bannerEvent.bannerSize === "large" && app.overlay === "" && !app.urgentEvent.id; preempted: !!app.urgentEvent.id
        eventPrefix: "banner"; exitAllowed: !app.bannerEvent.id && app.overlay === ""
        EventLargeBanner { style: parent.style;
            dashboard: app
            visible: true
        }
    }
    EventUrgent { style: app.style; dashboard: app; visible: !!app.urgentEvent.id; anchors.fill: parent }

    Rectangle {
        visible: app.diagnostics
        x: 618; y: 7; width: 298; height: 42; radius: app.style.radiusButton; color: app.style.debugSurface
        AppText { style: app.style; anchors.centerIn: parent; text: app.measuredFps.toFixed(1) + " fps · p95 " + app.p95Ms.toFixed(0) + " ms"; color: app.ink; font.pixelSize: app.style.font20 }
    }
    Rectangle {
        id: devPanel
        visible: false
        x: 494; y: 105; width: 420; height: 237; radius: app.style.radiusPanel
        color: app.style.demoSurface; border.color: app.accent; border.width: app.style.borderWidth
        AppText { style: app.style; x: 16; y: 12; text: "PANNELLO DEMO · F12"; color: app.accent; font.pixelSize: app.style.font23; font.weight: (true ) ? app.style.headingWeight : app.style.bodyWeight}
        AppText { style: app.style; x: 16; y: 53; text: "Meteo: " + (app.dashboardState ? app.dashboardState.demoScenario : "—"); color: app.ink; font.pixelSize: app.style.font22 }
        AppText { style: app.style; x: 16; y: 91; text: "Clic: online / offline / assente"; color: app.ink; font.pixelSize: app.style.font19
            MouseArea { anchors.fill: parent; onClicked: app.dashboardState.cycleDemoWeather() } }
        AppText { style: app.style; x: 16; y: 133; text: "Clic: prossimo evento on/off"; color: app.ink; font.pixelSize: app.style.font19
            MouseArea { anchors.fill: parent; onClicked: app.dashboardState.toggleDemoEvent() } }
        AppText { style: app.style; x: 16; y: 175; text: "Avvisi: " + (app.dashboardState ? app.dashboardState.demoAlertScenario : "—"); color: app.ink; font.pixelSize: app.style.font19
            MouseArea { anchors.fill: parent; onClicked: app.dashboardState.cycleDemoAlert() } }
    }
    Rectangle {
        id: dimmingLayer
        anchors.fill: parent; color: "black"
        readonly property real targetOpacity: 1 - app.brightnessPercent / 100
        opacity: 0
        visible: opacity > 0
        onTargetOpacityChanged: {
            const previous = opacity
            opacity = targetOpacity
            brightnessMotion.play(dimmingLayer,"brightness.change",1,false,{propertyName:"opacity",valueFrom:previous,valueTo:targetOpacity})
        }
        Component.onCompleted: opacity = targetOpacity
        MotionController { id: brightnessMotion }
    }
}
