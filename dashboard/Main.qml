import QtQuick

Window {
    id: app
    width: 960; height: 640
    minimumWidth: 960; minimumHeight: 640
    maximumWidth: 960; maximumHeight: 640
    visible: true
    visibility: Window.FullScreen
    title: "SmartPC"
    color: app.night ? "#0b1219" : "#101923"

    property var keypad: null
    property var dashboardState: null
    property date now: new Date()
    // Add a family only when its provider and screens are ready.
    readonly property var allFamilies: [
        { id: "oggi", slot: 0, name: "OGGI", views: ["ORA", "GIORNATA"] },
        { id: "meteo", slot: 1, name: "METEO", views: ["ADESSO", "PREVISIONI"] },
        { id: "account", slot: 2, name: "ACCOUNT CHATGPT", views: ["UTILIZZO"] }
    ]
    readonly property var visibleModules: dashboardState ? dashboardState.visibleModules : ["oggi", "meteo", "account"]
    readonly property var families: allFamilies.filter(item => visibleModules.indexOf(item.id) !== -1)
    property string familyId: "oggi"
    readonly property int family: Math.max(0, families.findIndex(item => item.id === familyId))
    readonly property var currentFamily: families[family] || allFamilies[0]
    property var viewIndex: [0, 0, 0]
    property string overlay: ""
    property var overlayStack: []
    property int menuIndex: 0
    property int settingsIndex: 0
    property int modulesIndex: 0
    property int systemIndex: 0
    property int notificationIndex: 0
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

    readonly property color ink: night ? "#cddbd8" : "#e9f1ef"
    readonly property color muted: night ? "#93a9ae" : "#b3c2c7"
    readonly property color accent: night ? "#69bfa8" : "#6de0be"
    readonly property color panel: night ? "#14232c" : "#1c2d38"
    readonly property color edge: night ? "#29424b" : "#35525d"
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
    readonly property int brightnessPercent: dashboardState
        ? (dashboardState.brightnessMode === "manual" ? dashboardState.manualBrightness
           : (daytime ? dashboardState.dayBrightness : dashboardState.nightBrightness))
        : 100
    readonly property var menuItems: ["Comandi", "Impostazioni", "Diagnostica"]
    readonly property var settingsItems: ["Aspetto e dispositivo", "Moduli visibili", "Notifiche"]
    readonly property var systemLabels: ["Tema", "Luminosità", "Manuale", "Giorno auto", "Notte auto", "Giorno dalle", "Notte dalle"]
    readonly property var notificationLabels: ["Fascia di silenzio", "Dalle", "Alle", "Interruzioni Meteo", "Interruzioni Account"]

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
        return currentFamily.views[viewIndex[currentFamily.slot] || 0]
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
    function adjustSystem(direction) {
        if (dashboardState) dashboardState.adjustDisplaySetting(systemIndex, direction)
    }
    function animateMove(direction) {
        moveAnimation.stop()
        contentLayer.x = direction * 20
        moveAnimation.start()
    }
    function navigateFamily(direction) {
        familyId = families[(family + direction + families.length) % families.length].id
        animateMove(direction)
    }
    function navigateView(direction) {
        const indices = viewIndex.slice()
        const slot = currentFamily.slot
        const count = currentFamily.views.length
        indices[slot] = ((indices[slot] || 0) + direction + count) % count
        viewIndex = indices
        animateMove(direction)
    }
    function home() {
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
    }
    function popOverlay() {
        if (overlay === "commands" && dashboardState) dashboardState.markCommandsSeen()
        const stack = overlayStack.slice()
        overlay = stack.length ? stack.pop() : ""
        overlayStack = stack
    }
    function back() {
        if (overlay !== "") popOverlay()
        else home()
    }
    function selectMenu() {
        if (menuIndex === 0) pushOverlay("commands")
        else if (menuIndex === 1) { settingsIndex = 0; pushOverlay("settings") }
        else if (menuIndex === 2) { toggleDiagnostics(); overlay = ""; overlayStack = [] }
    }
    function selectSettings() {
        if (settingsIndex === 0) { systemIndex = 0; pushOverlay("system") }
        else if (settingsIndex === 1) { modulesIndex = 1; pushOverlay("modules") }
        else if (settingsIndex === 2) { notificationIndex = 0; pushOverlay("notifications") }
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
            if (position === 2) menuIndex = (menuIndex + menuItems.length - 1) % menuItems.length
            else if (position === 8) menuIndex = (menuIndex + 1) % menuItems.length
            else if (position === 5) selectMenu()
            return
        }
        if (overlay === "settings") {
            if (position === 2) settingsIndex = (settingsIndex + settingsItems.length - 1) % settingsItems.length
            else if (position === 8) settingsIndex = (settingsIndex + 1) % settingsItems.length
            else if (position === 5) selectSettings()
            return
        }
        if (overlay === "modules") {
            if (position === 2) modulesIndex = modulesIndex === 1 ? allFamilies.length - 1 : modulesIndex - 1
            else if (position === 8) modulesIndex = modulesIndex === allFamilies.length - 1 ? 1 : modulesIndex + 1
            else if (position === 4 || position === 5 || position === 6) toggleModule(modulesIndex)
            return
        }
        if (overlay === "system") {
            if (position === 2) systemIndex = (systemIndex + systemLabels.length - 1) % systemLabels.length
            else if (position === 8) systemIndex = (systemIndex + 1) % systemLabels.length
            else if (position === 4) adjustSystem(-1)
            else if (position === 6 || position === 5) adjustSystem(1)
            return
        }
        if (overlay === "notifications") {
            if (position === 2) notificationIndex = (notificationIndex + notificationLabels.length - 1) % notificationLabels.length
            else if (position === 8) notificationIndex = (notificationIndex + 1) % notificationLabels.length
            else if (position === 4) dashboardState.adjustNotificationSetting(notificationIndex, -1)
            else if (position === 6 || position === 5) dashboardState.adjustNotificationSetting(notificationIndex, 1)
            return
        }
        if (overlay === "alerts") {
            if (alertItems.length) {
                if (position === 2) alertIndex = Math.max(0, alertIndex - 1)
                else if (position === 8) alertIndex = Math.min(alertItems.length - 1, alertIndex + 1)
                else if (position === 5) openSelectedAlert()
            }
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
        else if (position === 5) pushOverlay("detail")
    }

    Connections {
        target: app.keypad
        function onKeyPressed(position) { app.activateKey(position) }
    }
    Component.onCompleted: {
        if (dashboardState && dashboardState.firstRun) pushOverlay("commands")
        if (dashboardState) dashboardState.setBannerAvailable(overlay === "")
    }
    onOverlayChanged: if (dashboardState) dashboardState.setBannerAvailable(overlay === "")
    function syncClock() {
        const d = new Date()
        if (d.getMinutes() !== app.now.getMinutes() || d.getDate() !== app.now.getDate()) {
            app.now = d
        }
    }
    Timer { interval: 1000; repeat: true; running: true; onTriggered: app.syncClock() }
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
    Text { x: 44; y: 26; text: app.currentFamily.name + " · " + app.viewName(); color: app.accent; font.pixelSize: 35; font.bold: true }
    Text { x: 790; y: 33; width: 125; horizontalAlignment: Text.AlignRight; text: (app.family + 1) + "/" + app.families.length + "  ·  " + ((app.viewIndex[app.currentFamily.slot] || 0) + 1) + "/" + app.currentFamily.views.length; color: app.muted; font.pixelSize: 23 }

    Item {
        id: contentLayer
        objectName: "contentLayer"
        x: 0; y: 90; width: 960; height: 455
        NumberAnimation { id: moveAnimation; target: contentLayer; property: "x"; to: 0; duration: 160; easing.type: Easing.OutCubic }

        HomeNow { objectName: "homeNow"; dashboard: app; visible: app.familyId === "oggi" && app.viewIndex[0] === 0; x: 44 }
        HomeDay { objectName: "homeDay"; dashboard: app; visible: app.familyId === "oggi" && app.viewIndex[0] === 1; x: 44 }
        WeatherNow { objectName: "weatherNow"; dashboard: app; visible: app.familyId === "meteo" && app.viewIndex[1] === 0; x: 44 }
        WeatherForecast { objectName: "weatherForecast"; dashboard: app; visible: app.familyId === "meteo" && app.viewIndex[1] === 1; x: 44 }
        AccountChatGPT { objectName: "accountPanel"; dashboard: app; visible: app.familyId === "account"; x: 44; width: 872; height: 430 }
    }

    Rectangle { x: 44; y: 558; width: 872; height: 2; color: "#31505b" }
    Text { x: 46; y: 578; text: "4/6  ARGOMENTO"; color: app.muted; font.pixelSize: 25 }
    Text { x: 351; y: 578; text: app.familyId === "account" ? (app.accountWindows.length > 2 ? "2/8  SCORRI" : "") : "2/8  VISTA"; color: app.muted; font.pixelSize: 25 }
    Text { x: 669; y: 578; text: app.familyId === "account" ? "9  MENU" : "5  DETTAGLI"; color: app.accent; font.pixelSize: 25 }

    UnreadAlertsBadge {
        dashboard: app
        visible: app.familyId === "oggi" && app.overlay === "" && app.unreadAlertCount > 0 && !app.bannerEvent.id && !app.urgentEvent.id
    }
    DashboardOverlay { dashboard: app; visible: app.overlay !== ""; anchors.fill: parent }
    EventBanner {
        dashboard: app
        visible: !!app.bannerEvent.id && app.bannerEvent.bannerSize !== "large" && app.overlay === "" && !app.urgentEvent.id
    }
    EventLargeBanner {
        dashboard: app
        visible: !!app.bannerEvent.id && app.bannerEvent.bannerSize === "large" && app.overlay === "" && !app.urgentEvent.id
    }
    EventUrgent { dashboard: app; visible: !!app.urgentEvent.id; anchors.fill: parent }

    Rectangle {
        visible: app.diagnostics
        x: 618; y: 7; width: 298; height: 42; radius: 6; color: "#273e48"
        Text { anchors.centerIn: parent; text: app.measuredFps.toFixed(1) + " fps · p95 " + app.p95Ms.toFixed(0) + " ms"; color: app.ink; font.pixelSize: 20 }
    }
    Rectangle {
        id: devPanel
        visible: false
        x: 494; y: 105; width: 420; height: 237; radius: 10
        color: "#304750"; border.color: app.accent; border.width: 2
        Text { x: 16; y: 12; text: "PANNELLO DEMO · F12"; color: app.accent; font.pixelSize: 23; font.bold: true }
        Text { x: 16; y: 53; text: "Meteo: " + (app.dashboardState ? app.dashboardState.demoScenario : "—"); color: app.ink; font.pixelSize: 22 }
        Text { x: 16; y: 91; text: "Clic: online / offline / assente"; color: app.ink; font.pixelSize: 19
            MouseArea { anchors.fill: parent; onClicked: app.dashboardState.cycleDemoWeather() } }
        Text { x: 16; y: 133; text: "Clic: prossimo evento on/off"; color: app.ink; font.pixelSize: 19
            MouseArea { anchors.fill: parent; onClicked: app.dashboardState.toggleDemoEvent() } }
        Text { x: 16; y: 175; text: "Avvisi: " + (app.dashboardState ? app.dashboardState.demoAlertScenario : "—"); color: app.ink; font.pixelSize: 19
            MouseArea { anchors.fill: parent; onClicked: app.dashboardState.cycleDemoAlert() } }
    }
    Rectangle {
        anchors.fill: parent
        color: "black"
        opacity: 1 - app.brightnessPercent / 100
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 180 } }
    }
}
