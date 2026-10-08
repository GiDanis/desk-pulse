import QtQuick
import "themes"
import "components"
import "components/PublicSettingsRows.js" as PublicSettingsRows

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

    // Private application diagnostics; never supplied by a theme package.
    property var traceRecorder: null
    property string traceShellInstance: ""
    function themeTracePresence(item, renderItem) {
        const point = item.mapToItem(null,0,0)
        let effective = item.opacity
        let ancestor = item.parent
        while (ancestor) { effective *= ancestor.opacity; ancestor = ancestor.parent }
        if (renderItem && renderItem !== item) {
            effective *= renderItem.opacity
            if (renderItem.item) effective *= renderItem.item.opacity
        }
        const valid = item.width > 0 && item.height > 0 && point.x < width && point.y < height && point.x+item.width > 0 && point.y+item.height > 0
        // Actual transforms supplement revision identity for terminal-motion proof.
        // Snapshot only on GUI; all values are copied before render callbacks.
        function geometry(node) {
            const a = node.mapToItem(null,0,0)
            const b = node.mapToItem(null,node.width,0)
            const c = node.mapToItem(null,0,node.height)
            const d = node.mapToItem(null,node.width,node.height)
            return {x:node.x,y:node.y,width:node.width,height:node.height,
                scale:node.scale,rotation:node.rotation,opacity:node.opacity,
                visible:node.visible,clip:node.clip,corners:[a.x,a.y,b.x,b.y,c.x,c.y,d.x,d.y]}
        }
        const observed = [geometry(item)]
        if (renderItem && renderItem !== item) {
            observed.push(geometry(renderItem))
            if (renderItem.item) observed.push(geometry(renderItem.item))
        }
        return {geometryValid:valid,opacity:effective,exposed:item.visible && valid && effective > 0,visualGeometry:observed}
    }
    function themeTraceSnapshot() {
        if (!traceRecorder) return ({})
        const revision = themeService ? themeService.revision : style.appearance.revision
        if (!traceShellInstance) traceShellInstance = traceRecorder.allocateInstance("shell.main","legacyInline")
        const participants = [{instanceId:traceShellInstance,surfaceId:"shell.main",revision:style.appearance.revision,
            frontCommitted:true,frontCommittedRevision:style.appearance.revision,frontReady:true,frontRendererIdentity:"legacyInline",frontExpectedRendererIdentity:"legacyInline",
            observedRevision:style.appearance.revision,exposed:true,mandatory:true,committed:true,ready:true,
            geometryValid:width > 0 && height > 0,opacity:1,visualGeometry:[{width:width,height:height,visible:visible}],rendererIdentity:"legacyInline",
            motionRunning:false,retainedExit:false,actionsEnabled:true}]
        let moving = navigationMotion.traceRunningNow() || tabMotion.traceRunningNow()
        for (let index=0; index<contentLayer.children.length; index++) {
            const host = contentLayer.children[index]
            if (host.traceParticipant && (host.active || host.exiting)) {
                const participant = host.traceParticipant(true)
                participants.push(participant); moving = moving || participant.motionRunning
            }
        }
        const notices = [smallBanner,largeBanner,urgentHost,badgeHost,inboxHost,detailHost]
        for (let index=0; index<notices.length; index++) {
            const host = notices[index]
            const participant = host.traceParticipant(true)
            participant.motionRunning = participant.motionRunning || host.notificationMotionRunningNow()
            if (host.renderedEvent) { participant.eventId=String(host.renderedEvent.id || ""); participant.eventRevision=String(host.renderedEvent.revision || ""); participant.rank=host.renderedEvent.notificationRank || 0 }
            participants.push(participant); moving = moving || participant.motionRunning
            if (host.urgentFallbackActive) participants.push({instanceId:participant.instanceId+":fallback",surfaceId:host.contentId,
                revision:-1,observedRevision:-1,exposed:true,mandatory:false,committed:true,ready:true,
                geometryValid:true,opacity:1,rendererIdentity:"app.urgentFallback",role:"fallback",actionsEnabled:true,
                eventId:String(urgentEvent.id || ""),eventRevision:String(urgentEvent.revision || ""),rank:urgentEvent.notificationRank || 0})
        }
        const layers = [genericLayer,settingsLayer,infoLayer,racingLayer,teamLayer,sportLayer]
        for (let index=0; index<layers.length; index++) {
            const layer = layers[index]
            if (layer.active || layer.exiting) {
                const participant = layer.traceParticipant(app)
                participants.push(participant); moving = moving || participant.motionRunning
            }
        }
        if (notificationPreview.visible && notificationPreview.traceHost) {
            const participant = notificationPreview.traceHost.traceParticipant(false)
            participant.motionRunning = participant.motionRunning || notificationPreview.traceHost.notificationMotionRunningNow()
            participants.push(participant); moving = moving || participant.motionRunning
        }
        const scene = sceneHost.traceParticipant(app)
        participants.push(scene); moving = moving || scene.motionRunning
        return {revision:revision,requestId:traceRecorder.requestForRevision(revision),
            candidatePending:!!(themeService && themeCandidate.generation),sceneGraphValid:true,
            motionRunning:moving,participants:participants,route:overlay,inputFocus:activeFocusItem ? activeFocusItem.objectName : ""}
    }
    Connections { target: app.traceRecorder ? app.style : null
        function onAppearanceChanged() { if (app.traceRecorder) app.traceRecorder.invalidate("style.changed") }
    }
    Connections {
        target: app.traceRecorder ? contentLayer : null
        function onXChanged() { app.traceRecorder.invalidate("content.geometry") }
        function onYChanged() { app.traceRecorder.invalidate("content.geometry") }
        function onWidthChanged() { app.traceRecorder.invalidate("content.geometry") }
        function onHeightChanged() { app.traceRecorder.invalidate("content.geometry") }
        function onVisibleChanged() { app.traceRecorder.invalidate("content.visibility") }
        function onOpacityChanged() { app.traceRecorder.invalidate("content.opacity") }
    }
    onActiveFocusItemChanged: if (traceRecorder) { traceRecorder.invalidate("focus.changed"); traceRecorder.traceEvent("input.focus",{objectName:activeFocusItem ? activeFocusItem.objectName : ""}) }
    property var keypad: null
    property var dashboardState: null
    readonly property string activeContentId: familyId === "sports" ? "sport.hub" : familyId === "oggi" ? (viewIndex[0] === 0 ? "home.now" : viewIndex[0] === 1 ? "home.clock" : "home.day") : familyId === "meteo" ? (viewIndex[1] === 0 ? "weather.now" : "weather.forecast") : familyId === "account" ? "account.usage" : familyId === "sport" ? (sportView === "LA MIA SQUADRA" ? "sport.team" : "sport.overview") : familyId === "casa" ? ((viewIndex[6] || 0) === 0 ? "casa.overview" : "casa.devices") : familyId === "network" ? ((viewIndex[7] || 0) === 0 ? "network.overview" : "network.devices") : "racing.overview"
    onActiveContentIdChanged: { if (traceRecorder) traceRecorder.traceEvent("navigation.content",{surfaceId:activeContentId}); if (themeService) themeService.setActiveContent(activeContentId); Qt.callLater(function() { presentPage(contentLayer.children.find(host => host.active)) }) }
    readonly property var themeService: dashboardState ? dashboardState.appearance : null
    readonly property var themeCandidate: themeService ? themeService.candidateAppearance : ({})
    readonly property bool themePreparing: !!themeCandidate.generation

    readonly property var publicRoutes: {"alertDetail": "alerts.detail", "alerts": "alerts.inbox", "info": "device.info", "commands": "overlay.commands", "menu": "overlay.menu", "detail": "overlay.summary", "racingList": "racing.calendar", "racingDriver": "racing.driver.detail", "racingEvent": "racing.event.detail", "racingTiming": "racing.live", "racingSession": "racing.session.detail", "racingTable": "racing.standings", "services":"settings.services", "sportModules":"settings.sports", "themeManagement":"settings.appearance.management", "accountSettings": "settings.account", "appearance": "settings.appearance", "appearanceNotifications": "settings.appearance.notifications", "system": "settings.display", "settings": "settings.index", "integrations": "settings.integrations", "modules": "settings.modules", "notifications": "settings.notifications", "notificationCategories": "settings.notifications.categories", "notificationQuiet": "settings.notifications.quiet", "racingSettings": "settings.racing", "sources": "settings.sources", "sportSettings": "settings.sport", "sportList": "sport.fixtures", "sportDetail": "sport.match.detail", "sportTable": "sport.standings", "sportTeam": "sport.team.detail", "sportTeamPicker": "sport.team.picker", "casaDetail":"casa.detail", "casaSettings":"settings.casa", "networkDetail":"network.detail", "networkSettings":"settings.network", "networkRouter":"network.router", "networkWifi":"network.wifi", "networkPorts":"network.ports"}
    readonly property string overlayContentId: publicRoutes[overlay] || ""
    function restoreInputFocus() { inputOwner.forceActiveFocus() }
    function hasCandidateSurface(surfaceId) {
        if (!themeService || !surfaceId) return false
        const snapshot=themeCandidate
        if (!snapshot.generation) return false
        const descriptor=snapshot.presentationRegistry[snapshot.presentations[surfaceId]]
        return !!descriptor && descriptor.apiVersion === 2
    }
    function hasExternalSurface(surfaceId) {
        if (!surfaceId || !style.appearance) return false
        const id = style.appearance.presentations[surfaceId]
        const descriptor = style.appearance.presentationRegistry[id]
        return !!descriptor && descriptor.apiVersion === 2
    }
    readonly property var negotiatedLayout: style.appearance && hasExternalSurface("shell.main") ? style.appearance.layout || null : null
    function pageGeometry(surfaceId) {
        const area = negotiatedLayout && hasExternalSurface(surfaceId) ? negotiatedLayout.content : null
        return area ? Qt.rect(area.x,area.y,area.width,area.height) : Qt.rect(44,90,872,455)
    }
    // Compact shells reserve their header for every external overlay.
    function overlayGeometry(surfaceId) {
        const compact = negotiatedLayout && negotiatedLayout.guide.height === 0 && hasExternalSurface(surfaceId)
        const top = compact ? negotiatedLayout.header.y + negotiatedLayout.header.height : 0
        return Qt.rect(0,top,960,640-top)
    }
    property string presentedPageContentId: ""
    property string presentedFamilyId: ""
    property string presentedViewName: ""
    property var presentedNavigation: ({})
    property int pendingNavigationDirection: 0
    property bool pendingNavigationVertical: false
    function presentPage(host) {
        if (!host || !host.active || !host.currentReady || host.readiness !== "ready" || host.contentId !== activeContentId) return
        presentedPageContentId = host.contentId
        presentedFamilyId = familyId; presentedViewName = viewName()
        if (overlay === "") presentedNavigation = navigationSnapshot()
        if (pendingNavigationDirection) {
            const direction = pendingNavigationDirection, vertical = pendingNavigationVertical
            pendingNavigationDirection = 0
            animateMove(direction,vertical)
        }
    }
    function presentOverlay() {
        if (overlayHost.active && overlayHost.currentReady && overlayHost.readiness === "ready" && overlayHost.currentSurfaceId === overlayHost.contentId)
            presentedNavigation = navigationSnapshot()
    }
    function settledNavigation() {
        const page=contentLayer.children.find(host => host.active)
        const complete = overlay === "" ? presentedPageContentId === activeContentId && presentedFamilyId === familyId && presentedViewName === viewName() && !!page && page.currentReady && page.readiness === "ready" : !overlayHost.active || (overlayHost.currentReady && overlayHost.currentSurfaceId === overlayHost.contentId)
        return !complete && presentedNavigation.familyId ? presentedNavigation : navigationSnapshot()
    }
    function navigationSnapshot() {
        const mainPosition = familyId === "sports" ? 1 : (isRacing ? currentFamily.views.indexOf(racingView) : familyId === "sport" ? sportViews.indexOf(sportView) : (viewIndex[currentFamily.slot] || 0)) + 1
        let scopeId = familyId, count = currentFamily.views.length, position = mainPosition, label = viewName()
        if (overlay !== "") {
            scopeId = overlayContentId; count = 1; position = 1; label = ""
            let tabs = [], index = 0
            if (overlay === "sportList" || overlay === "sportTable") { scopeId = "sport.competition"; tabs = ["Partite","Classifica"]; index = overlay === "sportTable" ? 1 : 0 }
            else if (overlay === "sportDetail") { tabs = sportDetailTabs; index = sportDetailPage }
            else if (overlay === "sportTeam") { tabs = ["PARTITE","RISULTATI","INFO","ROSA"]; index = teamTab }
            else if (overlay === "info") { tabs = deviceInfo.tabs; index = infoPage }
            else if (overlay === "racingDriver") { tabs = racingDriverTabs; index = racingDriverPage }
            else if (overlay.indexOf("racing") === 0) {
                tabs = racingOverlay.tabs
                index = overlay === "racingTable" ? racingStandingTab : overlay === "racingSession" ? racingDetailPage : overlay === "racingTiming" ? racingTimingPage : overlay === "racingEvent" ? racingEventPage : 0
            }
            if (tabs.length) { count = tabs.length; position = Math.min(count,Math.max(1,index+1)); label = tabs[position-1] }
        }
        return {familyId:macroFamilyId,viewId:activeContentId,overlayId:overlayContentId,
            familyPosition:family+1,familyCount:families.length,viewPosition:mainPosition,viewCount:currentFamily.views.length,
            scopeId:scopeId,scopePosition:position,scopeCount:count,scopeLabel:label}
    }
    function shellGeometry() {
        const layout = negotiatedLayout
        function rectangle(area) { return Qt.rect(area.x,area.y,area.width,area.height) }
        return {header:layout ? rectangle(layout.header) : Qt.rect(0,0,960,90),
            content:pageGeometry(activeContentId),guide:layout ? rectangle(layout.guide) : Qt.rect(44,558,872,56),
            sceneSafeRegions:layout ? layout.sceneSafeRegions.map(rectangle) : [Qt.rect(0,90,32,455),Qt.rect(928,90,32,455)]}
    }
    function publicRows(rows) {
        return rows.map(row => {
            const item = typeof row === "string" ? {title:row} : Object.assign({},row)
            item.id = item.id === "" && item.name === "Nessuna preferita" ? "none" : String(item.id || item.target || item.canonicalMatchId || item.teamId || item.settingId || item.title || item.label || "")
            return item
        })
    }
    function publicKeyMap() {
        const commands=publicSurfaceCommands(overlay==="commands" ? activeContentId : overlayContentId || activeContentId)
        const labels={1:"HOME",3:"AVVISI",5:"CHIUDI GUIDA",7:"INDIETRO",9:"MENU"}
        for (const command of commands) if (command.key!==5) labels[command.key]=command.label
        const actions={1:"navigation.home",2:"selection.move",3:"navigation.inbox",4:"navigation.family.step",5:"navigation.back",6:"navigation.family.step",7:"navigation.back",8:"selection.move",9:"navigation.menu"}
        return [1,2,3,4,5,6,7,8,9].map(key=>({id:"key."+key,key:key,actionId:actions[key],targetId:"",label:labels[key] || "",enabled:true}))
    }
    function publicSurfaceCommands(surfaceId) {
        const page = surfaceId.indexOf("home.") === 0 || surfaceId.indexOf("weather.") === 0 || surfaceId === "sport.overview" || surfaceId === "sport.team" || surfaceId === "racing.overview" || surfaceId === "shell.main"
        const settings = surfaceId.indexOf("settings.") === 0
        const rows = ["network.router","network.wifi","network.ports"].indexOf(surfaceId)>=0 ? [[4,"SCHEDE"],[6,"SCHEDE"],[2,networkMetricsSection==="history" ? "FINESTRA" : "SELEZIONA"],[8,networkMetricsSection==="history" ? "FINESTRA" : "SELEZIONA"],[5,networkMetricsSection==="history" ? "METRICA" : "APRI"],[7,"INDIETRO"],[1,"HOME"]] : surfaceId === "sport.hub" ? [[2,"DISCIPLINE"],[8,"DISCIPLINE"],[4,"ARGOMENTO"],[6,"ARGOMENTO"],[5,"APRI"],[7,"INDIETRO"],[1,"HOME"]] :
            page && ["sport","f1","motogp"].indexOf(familyId)>=0 ? [[4,"SCHEDE"],[6,"SCHEDE"],[2,"VISTA"],[8,"VISTA"],[5,"DETTAGLI"],[7,"INDICE SPORT"],[1,"HOME"]] :
            surfaceId === "network.overview" || surfaceId === "network.devices" || surfaceId === "casa.overview" || surfaceId === "casa.devices" ? [[2,"SELEZIONA / SCHEDE"],[8,"SELEZIONA"],[4,"ARGOMENTO / VISTA"],[6,"ARGOMENTO / VISTA"],[5,"DETTAGLIO"],[7,"INDIETRO"],[1,"HOME"]] :
            surfaceId === "network.detail" ? [[2,"SCORRI"],[8,"SCORRI"],[4,"SCHEDE"],[6,"SCHEDE"],[5,"PREFERITO"],[7,"INDIETRO"],[1,"HOME"]] :
            surfaceId === "casa.detail" ? [[2,"SCORRI"],[8,"SCORRI"],[7,"INDIETRO"],[1,"HOME"]] :
            surfaceId === "account.usage" ? [[2,"SCORRI"],[8,"SCORRI"],[1,"HOME"],[3,"AVVISI"],[9,"MENU"]] :
            page ? [[2,"VISTA"],[8,"VISTA"],[4,"ARGOMENTO"],[6,"ARGOMENTO"],[5,"DETTAGLI"],[1,"HOME"],[3,"AVVISI"],[9,"MENU"]] :
            surfaceId === "overlay.commands" ? [[5,"CHIUDI GUIDA"],[7,"INDIETRO"],[1,"HOME"]] :
            surfaceId === "overlay.summary" ? [[7,"INDIETRO"],[1,"HOME"]] :
            surfaceId === "overlay.menu" || surfaceId === "sport.team.picker" ? [[2,"SELEZIONA"],[8,"SELEZIONA"],[5,"APRI"],[7,"INDIETRO"],[1,"HOME"]] :
            settings ? [[2,"SELEZIONA"],[8,"SELEZIONA"],[4,"REGOLA"],[6,"REGOLA"],[5,"CAMBIA"],[7,"INDIETRO"],[1,"HOME"]] :
            [[2,"SCORRI"],[8,"SCORRI"],[4,"SCHEDE"],[6,"SCHEDE"],[5,surfaceId === "sport.match.detail" ? sportDetailPage === 3 ? "SQUADRA" : "AGGIORNA" : "APRI"],[7,"INDIETRO"],[1,"HOME"]]
        return rows.map(row => ({id:"key."+row[0],key:row[0],label:row[1],enabled:true,actionId:"",targetId:""}))
    }
    function publicSurfacePayload(surfaceId, dataProjection) {
        if (["network.router","network.wifi","network.ports"].indexOf(surfaceId)>=0) return {
            networkMetricsView:networkMetricsView,
            selection:{selectedId:networkMetricsRows[networkMetricsIndex] ? networkMetricsRows[networkMetricsIndex].id : "", index:networkMetricsIndex,count:networkMetricsRows.length,tabId:networkMetricsSection,anchorId:networkMetricsTabsSelected ? "metrics.tabs" : ""},
            commands:publicSurfaceCommands(surfaceId),commandHints:[{key:1,label:"HOME"},{key:7,label:"INDIETRO"},{key:9,label:"MENU"}]
        }

        const hints = [{key:1,label:"HOME"},{key:3,label:"AVVISI"},{key:7,label:"INDIETRO"},{key:9,label:"MENU"}]
        // Auxiliary visuals have no provider/selection contract. Avoid coupling
        // their payloads to every domain and settings binding in the dashboard.
        if (surfaceId === "scene.main" || surfaceId.indexOf("alerts.") === 0)
            return {commandHints:hints}
        if (surfaceId === "shell.main") { const nav = settledNavigation(); return {commandHints:hints,
            families:families,currentFamilyId:nav.familyId,currentViewId:nav.viewId,navigation:nav,layout:shellGeometry(),commands:publicSurfaceCommands(surfaceId),
            uiStatus:{urgent:!!urgentEvent.id,recovery:!!(dashboardState && dashboardState.themeRecoveryError) || !!(themeService && themeService.status === "recovery"),quiet:quietActive,night:night,diagnostics:diagnostics},
            keyMap:publicKeyMap(),firstRun:!!(dashboardState && dashboardState.firstRun)} }
        let rows = [], selected = 0, tabs = [], tabId = "", description = "", feedback = ""
        if (surfaceId === "settings.network") { rows=networkSettingRows; selected=networkSettingsIndex; description="Dispositivi preferiti e ordine"; feedback=network.error || "" }
        else if (surfaceId.indexOf("network.") === 0) { rows=surfaceId === "network.detail" ? networkDetailRows : networkRows; selected=surfaceId === "network.detail" ? networkDetailIndex : Math.max(0,networkRows.findIndex(row => row.id === networkSelectedId)); if (surfaceId === "network.detail") { tabs=networkTabs; tabId=networkTabs[networkDetailTab] } else description=networkFilters[networkFilter] }
        else if (surfaceId === "settings.casa") { rows=casaSettingRows; selected=casaSettingsIndex; description="Dispositivi preferiti e ordine"; feedback=casa.error || "" }
        else if (surfaceId.indexOf("casa.") === 0) { rows=surfaceId === "casa.detail" ? (casaSelected ? casaSelected.metrics : []) : casaRows; selected=surfaceId === "casa.detail" ? casaMetricIndex : Math.max(0,casaRows.findIndex(row => row.id === casaSelectedId)) }
        else if (surfaceId === "settings.sport") {
            rows=[{id:"favourite",title:"Squadra preferita",value:((sportData.favouriteTeam || {}).data || {}).name || sportData.favourite || "Nessuna"},
                {id:"home",title:"Riepilogo Home",value:sportData.showOnHome ? "ATTIVO" : "DISATTIVO"},
                {id:"goals",title:"Notifiche gol",value:sportData.goalsEnabled ? "ATTIVE" : "DISATTIVE"},
                {id:"season",title:"Stagione",value:String(sportData.selectedSeason || "")},
                {id:"source",title:"Fonte dati",value:sport.source || ""}]; selected=sportSettingsIndex
        } else if (surfaceId === "settings.racing") {
            const data=(racingStates[racingSettingsKind] || {}).data || ({})
            rows=[{id:"year",title:"Stagione",value:String(data.selectedYear || data.year || "")},
                {id:"home",title:"Riepilogo Home",value:data.showOnHome ? "ATTIVO" : "DISATTIVO"},
                {id:"source",title:"Fonte dati",value:(racingStates[racingSettingsKind] || {}).source || ""}]; selected=racingSettingsIndex
        } else if (surfaceId.indexOf("settings.") === 0 && settingsPanel.active) {
            rows=settingsPanel.rows; selected=settingsPanel.selected; description=settingsPanel.description; feedback=settingsPanel.feedback
        } else if (surfaceId === "sport.hub") { rows=sportHubRows;selected=sportHubIndex;description="Scegli una disciplina" }
        else if (surfaceId === "overlay.menu") { rows=menuItems; selected=menuIndex }
        else if (surfaceId === "device.info") { rows=deviceInfo.rows; selected=infoIndex; tabs=deviceInfo.tabs; tabId=tabs[infoPage] || "" }
        else if (surfaceId === "sport.team.picker") { rows=teamPickerRows; selected=teamPickerIndex }
        else if (surfaceId === "sport.team.detail") { rows=teamRows; selected=teamIndex; tabs=["PARTITE","RISULTATI","INFO","ROSA"]; tabId=tabs[teamTab] }
        else if (surfaceId === "sport.match.detail") { rows=sportDetailPage === 3 ? fantasyRows : sportDetailPage === 1 ? sportMatch.stats || [] : sportDetailPage === 2 ? ((sportMatch.lineups || []).reduce((a,l) => (l.players || []).length > a.length ? l.players : a, [])) : sportMatch.events || []; selected=sportDetailPage === 3 ? fantasyPlayerIndex : sportDetailOffset; tabs=sportDetailTabs; tabId=tabs[sportDetailPage] }
        else if (surfaceId === "account.usage") { rows=accountWindows; selected=accountIndex }
        else if (surfaceId.indexOf("sport.") === 0) {
            rows=dataProjection === "route" && (surfaceId === "sport.overview" || surfaceId === "sport.team") ? [] : sportRows; selected=sportIndex
            if (surfaceId === "sport.overview") tabId=sportView
            if (surfaceId === "sport.fixtures" || surfaceId === "sport.standings") { tabs=["sport.fixtures","sport.standings"]; tabId=surfaceId }
        } else if (surfaceId === "racing.overview" && dataProjection === "route") {
            rows=[];tabId=racingView
        } else if (surfaceId.indexOf("racing.") === 0) {
            tabs=racingOverlay.tabs
            if (surfaceId === "racing.overview") tabId=racingView
            if (surfaceId === "racing.session.detail") { rows=racingDetailPage === 0 ? racingSession.results || [] : racingInfoRows; selected=racingDetailPage === 0 ? racingResultIndex : racingInfoIndex; tabId=tabs[racingDetailPage] || "" }
            else if (surfaceId === "racing.driver.detail") { rows=racingDriverRows; selected=racingDriverIndex; tabId=tabs[racingDriverPage] || "" }
            else if (surfaceId === "racing.event.detail") { rows=racingEventPage === 0 ? racingRows : racingInfoRows; selected=racingEventPage === 0 ? racingIndex : racingInfoIndex; tabId=tabs[racingEventPage] || "" }
            else if (surfaceId === "racing.live") { rows=racingTimingPage === 0 ? (racingData.live || {}).rows || [] : racingInfoRows; selected=racingTimingPage === 0 ? racingIndex : racingInfoIndex; tabId=tabs[racingTimingPage] || "" }
            else { rows=racingOverlay.rows; selected=racingIndex; if (surfaceId !== "racing.overview") tabId=tabs[racingStandingTab] || "" }
        }
        if (surfaceId.indexOf("settings.") === 0 && surfaceId !== "settings.casa" && surfaceId !== "settings.network") rows=PublicSettingsRows.canonicalize(surfaceId,rows,{families:allFamilies,visibleModules:visibleModules,
            racingKind:racingSettingsKind,advancedAppearance:settingsPanel.advancedAppearance,backend:dashboardState,
            appearance:style.appearance,sport:sportData,racing:(racingStates[racingSettingsKind] || {}).data || {},
            sportUpdating:sport.status === "updating",racingUpdating:(racingStates[racingSettingsKind] || {}).status === "updating",
            themes:themeService ? themeService.themes : [],fontFamilies:themeService && surfaceId.indexOf("settings.appearance") === 0 ? themeService.fontFamilies : [],
            revisions:themeService && (surfaceId === "settings.appearance" || surfaceId === "settings.appearance.management") ? themeService.revisions : [],
            status:themeService ? themeService.status : "ready",draft:themeService ? themeService.draft : {},notificationMode:settingsPanel.notificationMode})
        if (surfaceId === "settings.casa" || surfaceId === "settings.network") rows=rows.map(row => Object.assign({},row,{value:{available:true,value:row.value,displayText:String(row.value)}}))
        rows=publicRows(rows)
        const draft=themeService ? themeService.draft || {} : {},status=themeService ? themeService.status : "ready"
        const draftTokens=(draft.overrides || {}).tokens || {}
        const sourceOperation=surfaceId === "settings.sources" && dashboardState ? dashboardState.sourceRefreshStates[(settingsPanel.sourceEntries[selected] || {}).target] : null
        const operationStatus=sourceOperation ? ({running:"pending",queued:"pending",succeeded:"completed",failed:"failed",refused:"failed",cooldown:"failed",unavailable:"failed"})[sourceOperation.status] || "idle" : status === "saving" || status === "working" ? "pending" : status === "error" || status === "recovery" ? "failed" : "idle"
        const selectedId=surfaceId==="network.overview" && networkOverviewSection==="tools" ? networkTools[networkToolIndex].id : surfaceId.indexOf("network.") === 0 ? networkSelectedId : surfaceId.indexOf("casa.") === 0 ? casaSelectedId : rows[selected] ? rows[selected].id : surfaceId.indexOf("home.") === 0 || surfaceId.indexOf("weather.") === 0 || surfaceId === "account.usage" ? surfaceId : ""
        return {updatedAt:surfaceId === "device.info" ? deviceInfo.snapshot.updatedAt || null : null,networkOverviewSection:networkOverviewSection,networkTools:networkTools,rows:rows, networkDeviceRows:surfaceId.indexOf("network.")===0 ? networkRows : [], networkState:surfaceId.indexOf("network.") === 0 || surfaceId === "settings.network" ? network : null, networkDetailRows:surfaceId === "network.detail" ? networkDetailRows : [], casaState:surfaceId.indexOf("casa.") === 0 || surfaceId === "settings.casa" ? casa : null, selectedId:selectedId, selection:{selectedId:selectedId,index:surfaceId === "network.detail" ? networkDetailIndex : surfaceId === "casa.detail" ? casaMetricIndex : rows.length ? selected : -1,count:rows.length,tabId:tabId,
                anchorId:surfaceId.indexOf("network.")===0 && networkTabsSelected ? "network.tabs" : surfaceId.indexOf("casa.")===0 && casaTabsSelected ? "casa.tabs" : surfaceId === "sport.match.detail" && sportDetailPage === 3 ? String(((fantasyData.teams || [])[fantasyTeamIndex] || {}).id || "") : ""},sectionId:surfaceId,
            families:families, currentFamilyId:macroFamilyId, currentViewId:activeContentId, route:overlay,
            navigation:{familyId:familyId,viewId:activeContentId,overlayId:overlayContentId,familyPosition:family+1,familyCount:families.length,
                viewPosition:(isRacing ? currentFamily.views.indexOf(racingView) : familyId === "sport" ? sportViews.indexOf(sportView) : (viewIndex[currentFamily.slot] || 0))+1,viewCount:currentFamily.views.length},
            layout:shellGeometry(),
            uiStatus:{urgent:!!urgentEvent.id,recovery:!!(dashboardState && dashboardState.themeRecoveryError) || !!(themeService && themeService.status === "recovery"),quiet:quietActive,night:night,diagnostics:diagnostics},
            keyMap:publicKeyMap(),firstRun:!!(dashboardState && dashboardState.firstRun),
            tabs:tabs.map(label => ({id:label,label:label,enabled:true})), description:description,feedback:feedback,
            draft:themeService ? {editing:themeService.editing,themeId:draft.themeId,paletteMode:draft.paletteMode || "auto",
                motionMode:draft.motionMode,textScale:draftTokens["typography.textScale"] === undefined ? style.textScale : draftTokens["typography.textScale"],readyToApply:themeService.readyToApply,status:status,error:themeService.lastError} : null,
            operation:{requestId:"",status:operationStatus,errorCode:operationStatus === "failed" ? sourceOperation ? "source.operation.failed" : "appearance.operation.failed" : "",message:sourceOperation ? sourceOperation.message : themeService ? themeService.lastError : ""},
            sportMatch:surfaceId === "sport.match.detail" ? sportMatch : null, teamData:surfaceId === "sport.team.detail" ? Object.assign({},teamData,{info:publicRows(teamInfoRows),recordText:teamRecordText()}) : null, fantasyState:surfaceId === "sport.match.detail" ? fantasyState : null,
            racingEvent:surfaceId !== "racing.overview" && surfaceId.indexOf("racing.") === 0 ? racingEvent : null,racingSession:surfaceId !== "racing.overview" && surfaceId.indexOf("racing.") === 0 ? racingSession : null,racingDriver:surfaceId === "racing.driver.detail" ? racingDriver : null,kind:familyId,live:surfaceId === "racing.driver.detail" ? racingDriverLive : false,
            detailOperation:{requestId:"",status:(surfaceId.indexOf("racing.") === 0 ? racingData.detailLoading : sportData.detailLoading) ? "pending" : "idle",errorCode:"",message:""},
            teamPickerRows:surfaceId === "sport.team.picker" ? publicRows(teamPickerRows) : [], calendarScope:surfaceId === "sport.team.detail" ? teamData.calendarScope || "" : "", serieAOnly:surfaceId === "sport.team.detail" ? teamSerieAOnly : false,
            selectedRoundId:String(sportRound), favouriteTeamId:sportData.favouriteTeamId || "",
            savedTeamId:sportData.favouriteTeamId || "", origin:sportTeamDetail ? "team" : "sport",
            commands:publicSurfaceCommands(surfaceId),commandHints:[{key:1,label:"HOME"},{key:3,label:"AVVISI"},{key:7,label:"INDIETRO"},{key:9,label:"MENU"}]}
    }
    function publicActionOperation(action,target) {
        if (action === "network.metrics.refresh") return networkData.modeText && networkData.modeText.indexOf("Demo")===0 ? "" : "networkMetricsRefresh"
        if (action.indexOf("network.metrics.")===0) return ""
        const effective=action === "settings.activate" || action === "settings.adjust" ? target : action
        let source=action === "sources.refresh" ? target : action === "settings.activate" && target.indexOf("source.") === 0 ? target.slice(7) : ""
        if (source === "weather") source="meteo"
        if (["meteo","alerts","account","sport","f1","motogp"].indexOf(source) >= 0) return "source:"+source
        if ((action === "sources.refresh" && target === "casa") || (action === "settings.activate" && target === "source.casa")) return "casaRefresh"
        if (!networkData.modeText || networkData.modeText.indexOf("Demo") !== 0) { if ((action === "sources.refresh" && target === "network") || (action === "settings.activate" && target === "source.network") || action.indexOf("network.") === 0 && action !== "network.filter.step") return "networkRefresh" }
        return effective === "appearance.apply" ? "save" : effective === "appearance.import" || effective === "appearance.export" ? "transfer" : ""
    }
    function publicAppearanceSetting(surface,row,direction) {
        const service=themeService,id=row.id
        if (!service || service.status === "saving" || service.status === "working") return false
        if (id === "appearance.apply") return service.apply()
        if (id === "appearance.cancel") return service.cancel()
        if (id === "appearance.reset") return service.resetDraft()
        if (id === "appearance.reload") return service.reloadCatalog()
        if (id === "appearance.import" || id === "appearance.export") return service.transferPack(id.split(".")[1])
        if (id === "appearance.advanced" || id === "appearance.simple") { settingsPanel.advancedAppearance=id === "appearance.advanced"; optionIndex=0; return true }
        if (id === "appearance.notifications") { pushOverlay("appearanceNotifications"); return true }
        if (id === "appearance.management") {pushOverlay("themeManagement");return true}
        if (id === "appearance.back") { popOverlay(); return true }
        if (!service.editing) service.beginEdit()
        const snapshot=style.appearance,tokens=snapshot.tokens,metrics=settingsPanel.notificationMetrics
        const mode=settingsPanel.notificationMode,prefix="notifications."+mode+"."
        function choice(current) {
            const values=(row.options || []).map(option => option.value)
            return values.length ? settingsPanel.cycle(values,current,direction) : undefined
        }
        if (id === "appearance.palette" || id === "appearance.motion") {
            const section=id === "appearance.palette" ? "paletteMode" : "motionMode"
            return service.setSection(section,choice(service.draft[section] || "auto"))
        }
        if (id === "appearance.theme") return service.selectDraft(choice(service.draft.themeId))
        if (id === "appearance.revision") return service.stepRevision(direction)
        if (id === "appearance.textScale") return service.setToken("typography.textScale",Math.max(.85,Math.min(1.1,Math.round((style.textScale+direction*.05)*100)/100)))
        if (id === "appearance.cardRadius") return service.setToken("shape.radiusCard",Math.max(0,Math.min(24,style.radiusCard+direction*2)))
        if (id === "appearance.density") {
            const wide=style.listRows === 4
            return service.setTokens({"metrics.listRows":wide?3:4,"metrics.compactRows":wide?2:3,"metrics.overviewRows":wide?2:3,"metrics.fantasyRows":wide?4:5})
        }
        if (id === "appearance.scene") return service.setSection("scene",{enabled:!snapshot.scene.enabled})
        if (id === "appearance.accent") return service.setToken("colors.accent",choice(style.accent.toString()))
        if (id === "appearance.homeComposition") return service.setSection("presentations",Object.assign({},service.draft.overrides.presentations || {},{"home.now":choice(snapshot.presentations["home.now"])}))
        const fontTokens={"appearance.uiFont":"typography.uiFamily","appearance.numbersFont":"typography.numbersFamily","appearance.clockFont":"typography.displayFamily"}
        if (fontTokens[id]) return service.setToken(fontTokens[id],choice(tokens[fontTokens[id]]))
        if (id === "appearance.transitions") {
            const recipe=choice(snapshot.motion["navigate.family"].recipe)
            return service.setSection("motion",Object.assign({},service.draft.overrides.motion || {},{"navigate.family":{recipe:recipe,durationMs:160,distancePx:20,easing:"outCubic"},"navigate.view":{recipe:recipe,durationMs:160,distancePx:20,easing:"outCubic"}}))
        }
        if (id === "notifications.visual.mode") { notificationAppearanceMode=(notificationAppearanceMode+direction+6)%6; return true }
        if (id === "notifications.visual.preview") { notificationPreviewMode=mode; return true }
        if (id === "notifications.visual.reset") return service.resetNotifications()
        if (id.indexOf("notifications.visual.composition.") === 0) {
            const selectedMode=id.split(".").pop(),content=settingsPanel.notificationContent(selectedMode)
            return service.setSection("presentations",Object.assign({},service.draft.overrides.presentations || {},{[content]:choice(snapshot.presentations[content])}))
        }
        const sizes={"notifications.visual.padding":["padding",0,64],"notifications.visual.titleSize":["titleSize",18,72],
            "notifications.visual.bodySize":["bodySize",16,44],"notifications.visual.sourceSize":["sourceSize",16,32],"notifications.visual.radius":["radius",0,40]}
        if (sizes[id]) { const spec=sizes[id]; return service.setToken(prefix+spec[0],Math.max(spec[1],Math.min(spec[2],tokens[prefix+spec[0]]+direction*2))) }
        if (id === "notifications.visual.anchor") return service.setTokens({[prefix+"anchor"]:choice(metrics.anchor),[prefix+"insetY"]:0})
        if (id === "notifications.visual.inboxRows") return service.setToken("notifications.inbox.rows",Math.max(1,Math.min(5,tokens["notifications.inbox.rows"]+direction)))
        const noticeFonts={"notifications.visual.titleFont":"titleFamily","notifications.visual.bodyFont":"bodyFamily","notifications.visual.sourceFont":"sourceFamily"}
        if (noticeFonts[id]) return service.setToken(prefix+noticeFonts[id],choice(metrics[noticeFonts[id]]))
        if (id === "notifications.visual.icon" || id === "notifications.visual.source") {
            const token=id === "notifications.visual.icon" ? "showIcon" : "showSource"
            return service.setToken(prefix+token,!metrics[token])
        }
        if (id === "notifications.visual.enter" || id === "notifications.visual.exit") {
            const event=settingsPanel.notificationMotionPrefix+(id === "notifications.visual.exit" ? ".exit" : ".enter")
            return service.setSection("motion",Object.assign({},service.draft.overrides.motion || {},{[event]:{recipe:choice((snapshot.motion[event] || {}).recipe),durationMs:120,distancePx:20,easing:"outCubic"}}))
        }
        return false
    }
    function publicDispatch(context, action, target, arguments) {
        const args=arguments || {}, surface=context.contentId
        if (urgentEvent.id && surface !== "alerts.urgent") return false
        if (themePreparing && !urgentEvent.id && !(surface === "overlay.menu" && overlay === "menu")) {
            if (action === "navigation.home") { home(); return true }
            if (action === "navigation.back" || action === "appearance.cancel") { themeService.cancel(); return true }
            if (action === "navigation.menu") { pushOverlay("menu"); return true }
            return false
        }
        if (surface.indexOf("alerts.") === 0) {
            if (action === "scrollDetails") return notificationAction(surface.split(".").pop(),action,target,{offset:alertScroll+args.delta})
            if (action === "moveSelection") return notificationAction(surface.split(".").pop(),action,target,args.direction)
            return notificationAction(surface.split(".").pop(),action,target,args)
        }
        if (action === "navigation.home") { home(); return true }
        if (action === "navigation.back") { back(); return true }
        if (action === "navigation.menu") { pushOverlay("menu"); return true }
        if (action === "navigation.inbox") { pushOverlay("alerts"); return true }
        if (action === "navigation.family.step") { activateKey(args.direction < 0 ? 4 : 6); return true }
        if (action === "navigation.view.step" && (surface.indexOf("casa.")===0 || surface.indexOf("network.")===0)) { navigateView(args.direction); return true }
        if (action === "navigation.view.step" || action === "selection.move") { activateKey(args.direction < 0 ? 2 : 8); return true }
        if (action.indexOf("appearance.") === 0) {
            if (!themeService) return false
            if (action === "appearance.preview") { if (!themeService.editing) themeService.beginEdit(); return themeService.selectDraft(target) }
            if (action === "appearance.apply") return themeService.apply()
            if (action === "appearance.cancel") return themeService.cancel()
            if (action === "appearance.reset") return themeService.resetDraft()
            if (action === "appearance.reload") return themeService.reloadCatalog()
            if (action === "appearance.import" || action === "appearance.export") return themeService.transferPack(action.split(".")[1])
            if (action === "appearance.notificationPreview") { notificationPreviewMode=args.mode; return true }
            return false
        }
        if (action === "network.metrics.section" && surface === "network.overview") { if (["summary","tools"].indexOf(target)<0) return false; networkOverviewSection=target; return true }
        if (["network.router","network.wifi","network.ports"].indexOf(surface)>=0) {
            if (action === "network.metrics.refresh") return dashboardState && dashboardState.refreshNetworkMetrics()
            if (action === "network.metrics.section") { if (networkMetricsTabs.indexOf(target)<0) return false; networkMetricsSection=target; networkMetricsIndex=0; return true }
            if (action === "network.metrics.entity" || action === "details.open") return activateNetworkMetricRow(target)
            if (action === "network.metrics.window") { networkMetricsHours=networkMetricsHours===1 ? 24 : 1; return true }
            if (action === "network.metrics.metric") { networkMetricsMetric=(networkMetricsMetric+(args.direction || 1)+3)%3; return true }
            if (action === "selection.select") { const i=networkMetricsRows.findIndex(r=>r.id===target); if (i<0) return false; networkMetricsIndex=i; networkMetricsTabsSelected=false; return true }
        }
        if ((surface === "network.overview" || surface === "settings.network") && action === "details.open" && ["network.router","network.wifi","network.ports"].indexOf(target)>=0) { openNetworkMetrics(target); return true }
        if (surface === "network.detail" && action === "navigation.tab.select") { const i=networkTabs.indexOf(target); if (i<0) return false; networkDetailTab=i; networkDetailIndex=0; return true }
        if ((surface.indexOf("network.")===0 || surface === "settings.network") && action.indexOf("network.")===0) {
            if (action === "network.filter.step") { networkFilter=(networkFilter+(args.direction || 1)+networkFilters.length)%networkFilters.length; return true }
            if (action === "network.alias.set") return dashboardState && dashboardState.setNetworkAlias(target,args.alias || "")
            return networkSettingsAction(action,target,args.direction || 1)
        }
        if (surface === "settings.network" && action === "details.open") return networkSettingsAction(action,target,1)
        if (surface.indexOf("network.") === 0 && action === "details.open") { if (!(networkData.devices || []).some(row => row.id===target)) return false; openNetworkDevice(target); return true }
        if (surface.indexOf("network.") === 0 && action === "selection.select") { if (!networkRows.some(row => row.id===target)) return false; networkSelectedId=target; return true }
        if (surface === "settings.network" && action === "selection.select") { const i=networkSettingRows.findIndex(row => row.id===target); if (i<0) return false; networkSettingsIndex=i; return true }
        if (surface === "settings.casa" && action.indexOf("casa.") === 0) return casaSettingsAction(action,target,args.direction || 1)
        if (surface === "settings.casa" && action === "details.open") return casaSettingsAction(action,target,1)
        if (surface.indexOf("casa.") === 0 && action === "details.open") {
            if (!casaRows.some(row => row.id === target)) return false
            openCasaDevice(target); return true
        }
        if (surface.indexOf("casa.") === 0 && action === "selection.select") {
            if (!casaRows.some(row => row.id===target)) return false
            casaSelectedId=target; return true
        }
        if (surface === "settings.casa" && action === "selection.select") { const i=casaSettingRows.findIndex(row => row.id===target); if (i<0) return false; casaSettingsIndex=i; return true }
        if (action === "sources.refresh") return dashboardState ? dashboardState.refreshSource(target === "weather" ? "meteo" : target) : false
        if (surface === "sport.hub" && action === "selection.select") {
            if (!sportHubRows.some(row=>row.id===target)) return false
            sportHubSelectedId=target;return true
        }
        if (surface === "sport.hub" && action === "details.open") return openSportDiscipline(target)
        if (action === "details.refresh") {
            if (!dashboardState) return false
            if (surface.indexOf("racing.") === 0) { dashboardState.refreshRacingDetails(familyId); return true }
            if (surface === "sport.team.detail") { dashboardState.refreshSportTeam(); return true }
            if (surface === "sport.match.detail" && sportDetailPage === 3) { dashboardState.refreshFantacalcio(); return true }
            return dashboardState.refreshSource("sport")
        }
        if (action === "details.scroll") {
            if (surface.indexOf("sport.") === 0 || surface.indexOf("racing.") === 0) { if (args.delta !== 0) activateKey(args.delta < 0 ? 2 : 8); return true }
            return false
        }
        if (action === "details.open" && surface === activeContentId && target === surface) {
            activateKey(5); return true
        }
        if (action === "details.open" && surface === "sport.overview") {
            if (sportView === "CLASSIFICA") {
                const row = (sportData.standings || []).find(row => row.teamId === target)
                if (!row) return false
                sportTableIndex = (sportData.standings || []).indexOf(row)
                openSportTable(); return true
            }
            if (!sportFixtures.some(row => row.canonicalMatchId === target)) return false
            sportTeamDetail=false;sportMatchId=target;sportDetailPage=0;sportDetailOffset=0
            dashboardState.selectSportMatch(target);pushOverlay("sportDetail");return true
        }
        if (action === "details.open" && surface === "racing.overview") {
            if (racingView === "CLASSIFICA") {
                const index=(racingData.standings || []).findIndex(row => row.id === target)
                if (index < 0) return false
                racingStandingTab=0;pushOverlay("racingTable");racingIndex=index;return true
            }
            if (racingView === "IN CORSO") {
                const index=((racingData.live || {}).rows || []).findIndex(row => row.id === target)
                if (index < 0) return false
                racingTimingPage=0;pushOverlay("racingTiming");racingIndex=index;return true
            }
            if (!(racingData.events || []).some(row => row.id === target)) return false
            racingEventId=target;racingSessionId="";racingEventPage=0;racingInfoIndex=0
            dashboardState.selectRacing(familyId,target,"");pushOverlay("racingEvent");return true
        }
        const data=publicSurfacePayload(surface), index=data.rows.findIndex(row => row.id === target)
        if (action === "menu.activate") { if (index < 0) return false; menuIndex=index; selectMenu(); return true }
        if (action === "settings.activate" || action === "settings.adjust") {
            if (index >= 0 && data.rows[index].enabled === false) return false
            if (index >= 0 && action === "settings.adjust" && (data.rows[index].control === "action" || data.rows[index].control === "transfer")) return false
            if (index >= 0 && (surface.indexOf("settings.appearance") === 0 || data.rows[index].id.indexOf("appearance.")===0))
                return publicAppearanceSetting(surface,data.rows[index],action === "settings.adjust" ? args.direction : 1)
            if (index >= 0 && (surface === "settings.sport" || surface === "settings.racing")) {
                if (surface === "settings.sport") sportSettingsIndex=index
                else racingSettingsIndex=index
                activateKey(action === "settings.adjust" ? args.direction < 0 ? 4 : 6 : 5)
                return true
            }
            if (index < 0 || !settingsPanel.active) return false
            settingsPanel.setSelected(index)
            if (surface === "settings.sources") return dashboardState ? dashboardState.refreshSource(data.rows[index].target) : false
            settingsPanel.activate(action === "settings.adjust" ? args.direction : 1); return true
        }
        if (action === "selection.select" || action === "details.open") {
            if (index < 0) return false
            if (surface === "overlay.menu") menuIndex=index
            else if (surface === "device.info") infoIndex=index
            else if (surface === "settings.sport") sportSettingsIndex=index
            else if (surface === "settings.racing") racingSettingsIndex=index
            else if (surface.indexOf("settings.") === 0 && settingsPanel.active) settingsPanel.setSelected(index)
            else if (surface === "sport.team.picker") teamPickerIndex=index
            else if (surface === "sport.match.detail") { if (sportDetailPage === 3) fantasyPlayerIndex=index; else sportDetailOffset=index }
            else if (surface.indexOf("sport.team.") === 0) teamIndex=index
            else if (surface.indexOf("sport.") === 0) sportIndex=index
            else if (surface === "racing.session.detail") { if (racingDetailPage === 0) racingResultIndex=index; else racingInfoIndex=index }
            else if (surface === "racing.driver.detail") racingDriverIndex=index
            else if (surface === "racing.event.detail" && racingEventPage !== 0 || surface === "racing.live" && racingTimingPage !== 0) racingInfoIndex=index
            else if (surface.indexOf("racing.") === 0) racingIndex=index
            else return false
            if (action === "details.open") activateKey(5)
            return true
        }
        // Tab IDs are resolved by the app, never interpreted as arbitrary indexes.
        if (action === "tabs.select") {
            const tab=data.tabs.findIndex(row => row.id === target)
            if (tab < 0) return false
            if (surface === "device.info") deviceInfo.changeTab(tab)
            else if (surface === "sport.match.detail") sportDetailPage=tab
            else if (surface === "sport.team.detail") teamTab=tab
            else if (surface === "sport.fixtures" || surface === "sport.standings") {
                if (target !== surface) switchSportTab()
            }
            else if (surface === "racing.event.detail") racingEventPage=tab
            else if (surface === "racing.session.detail") racingDetailPage=tab
            else if (surface === "racing.driver.detail") racingDriverPage=tab
            else if (surface === "racing.live") racingTimingPage=tab
            else if (surface === "racing.standings") racingStandingTab=tab
            else return false
            return true
        }
        return false
    }

    readonly property var notificationContents: ["alerts.banner.small","alerts.banner.large","alerts.urgent","alerts.badge","alerts.inbox","alerts.detail"]
    property bool notificationInitialized: false
    property var submittedBanner: ({})
    property string notificationPreviewMode: ""
    property int notificationAppearanceMode: 0
    Binding { target: Theme; property: "service"; value: app.themeService }
    Binding { target: Theme; property: "fallbackNight"; value: app.night }
    onNightChanged: Qt.callLater(function() { if (app.themeService) app.themeService.setVariant(app.night ? "night" : "day") })
    Timer { interval: 0; running: true; onTriggered: if (app.themeService) app.themeService.setVariant(app.night ? "night" : "day") }
    property date now: new Date()
    // Add a family only when its provider and screens are ready.
    readonly property var casa: dashboardState ? dashboardState.casaState : ({status:"unavailable",source:"Tuya / Smart Life",updatedAt:0,data:{}})
    readonly property var casaData: casa.data || ({})
    property string casaSelectedId: ""
    property bool casaTabsSelected: false
    property int casaMetricIndex: 0
    property int casaSettingsIndex: 0
    readonly property var casaRows: (viewIndex[6] || 0) === 0 ? casaData.favourites || [] : casaData.devices || []
    readonly property var casaSelected: (casaData.devices || []).find(row => row.id === casaSelectedId) || null
    readonly property var casaSettingRows: [
        {id:"casa.devices",title:"Dispositivi e preferiti",detail:"Scegli fino a quattro tessere",value:"APRI",actionId:"details.open",targetId:"casa.devices",control:"action",enabled:!!casaData.configured && (casaData.favourites || []).length>0},
        {id:"casa.polling",title:"Aggiornamenti automatici",detail:casaData.modeText || "Configura il collegamento Smart Life",value:casaData.polling ? "ATTIVI" : "SOSPESI",actionId:"casa.polling.toggle",targetId:"casa",control:"toggle",enabled:!!casaData.quotaConfigured && !casaData.busy},
        {id:"casa.reload",title:"Rileggi configurazione",detail:"Collegamento e quota del progetto",value:"RILEGGI",actionId:"casa.config.reload",targetId:"casa",control:"action",enabled:!casaData.busy},
        {id:"casa.source",title:"Dati e aggiornamenti",detail:casa.error || "Ultima lettura e richieste del provider",value:"APRI",actionId:"details.open",targetId:"settings.sources",control:"action",enabled:true}
    ].concat((casaData.devices || []).map(row => ({id:row.id,title:row.name,detail:row.availability+(row.availabilityPrevious ? " · salvata" : ""),value:row.favourite ? "PREFERITO "+((casaData.favourites || []).findIndex(d => d.id === row.id)+1) : "AGGIUNGI",actionId:"casa.favourite.toggle",targetId:row.id,control:"toggle",enabled:!casaData.busy && (row.favourite || (casaData.favourites || []).length<4)})))
    function syncCasaSelection() {
        if (!casaRows.some(row => row.id === casaSelectedId)) casaSelectedId=casaRows.length ? casaRows[0].id : ""
        casaSettingsIndex=Math.min(casaSettingsIndex,Math.max(0,casaSettingRows.length-1))
    }
    onCasaRowsChanged: Qt.callLater(syncCasaSelection)
    onCasaSettingRowsChanged: Qt.callLater(syncCasaSelection)
    readonly property bool casaConsulted: familyId === "casa" && overlay === "" || overlay === "casaDetail" || overlay === "casaSettings"
    onCasaConsultedChanged: if (dashboardState) dashboardState.setCasaVisible(casaConsulted)
    function moveCasaSelection(direction) {
        const index=Math.max(0,casaRows.findIndex(row => row.id===casaSelectedId))
        if (casaTabsSelected) { if (direction>0) casaTabsSelected=false; return }
        if (direction<0 && index===0) { casaTabsSelected=true; return }
        if (casaRows.length) casaSelectedId=casaRows[Math.max(0,Math.min(casaRows.length-1,index+direction))].id
    }
    function openCasaDevice(identity) { casaSelectedId=identity; casaMetricIndex=0; pushOverlay("casaDetail") }
    function casaSettingsAction(action,target,direction) {
        if (!dashboardState) return false
        if (action === "casa.favourite.toggle") return dashboardState.toggleCasaFavourite(target)
        if (action === "casa.favourite.move") return dashboardState.moveCasaFavourite(target,direction)
        if (action === "casa.config.reload") return dashboardState.reloadCasaConfig()
        if (action === "casa.polling.toggle") return dashboardState.toggleCasaPolling()
        if (target === "casa.devices") { if (!(casaData.favourites || []).length) return false; familyId="casa"; const indices=viewIndex.slice(); indices[6]=1; viewIndex=indices; overlay=""; overlayStack=[]; return true }
        if (target === "settings.sources") { openSourceSettings("casa"); return true }
        return false
    }
    readonly property var network: dashboardState ? dashboardState.networkState : ({status:"unavailable",source:"iliadbox",updatedAt:0,data:{}})
    readonly property var networkData: network.data || ({})
    property string networkSelectedId: ""
    property bool networkTabsSelected: false
    property int networkDetailIndex: 0
    property int networkSettingsIndex: 0
    property int networkFilter:0
    property int networkDetailTab:0
    readonly property var networkFilters:["Tutti","Raggiungibili","Preferiti","Dati precedenti"]
    property string networkOverviewSection:"tools"
    property int networkToolIndex:0
    readonly property var networkRouterOverview: { const epoch=networkMetricsEpoch; return dashboardState ? dashboardState.networkMetricsView("router","","state",1,0,"") : ({}) }
    readonly property var networkTools: {
        const rows=networkRouterOverview.rows || [], down=rows.find(r=>r.id==="wan:down"), up=rows.find(r=>r.id==="wan:up")
        const temperatures=rows.filter(r=>r.id.indexOf("temp")===0)
        const samples=[down,up].concat(temperatures).filter(Boolean)
        return [
        {id:"network.router",title:"iliadbox · traffico WAN",value:down && up ? down.value+" ↓ · "+up.value+" ↑" : "Traffico non disponibile",detail:[temperatures.map(r=>r.title+" "+r.value).join(" · ") || "Temperatura iliadbox non disponibile",samples.some(r=>r.previous) ? "Dati precedenti" : "",down ? down.detail : ""].filter(Boolean).join(" · "),targetId:"network.router",previous:samples.some(r=>r.previous)},
        {id:"network.wifi",title:"Wi-Fi",value:"APRI",detail:"Radio, associazioni e link",targetId:"network.wifi",previous:false},
        {id:"network.ports",title:"Porte Ethernet",value:"APRI",detail:"Link, host e traffico condiviso",targetId:"network.ports",previous:false}]
    }
    property string networkMetricsSection:"state"
    property string networkWifiEntity:""
    property string networkPortEntity:""
    property string networkStationId:""
    property string networkMetricsLanReturnId:""
    property int networkMetricsHours:1
    property int networkMetricsMetric:0
    property int networkMetricsIndex:0
    property bool networkMetricsTabsSelected:true
    property int networkMetricsEpoch:0
    readonly property string networkMetricsRoute:overlay==="networkRouter" ? "router" : overlay==="networkWifi" ? "wifi" : overlay==="networkPorts" ? "ports" : ""
    readonly property string networkMetricsEntity:networkMetricsRoute==="wifi" ? networkWifiEntity : networkMetricsRoute==="ports" ? networkPortEntity : ""
    readonly property var networkMetricsTabs:networkMetricsRoute==="router" ? ["state","history"] : networkMetricsRoute==="wifi" ? ["radios","stations","detail"] : ["ports","hosts","history"]
    readonly property bool networkMetricsConsulted:networkMetricsRoute!=="" && !urgentEvent.id && !themePreparing
    readonly property bool networkOverviewConsulted:familyId==="network" && (viewIndex[7] || 0)===0 && overlay==="" && networkOverviewSection==="tools" && !urgentEvent.id && !themePreparing
    readonly property var networkMetricsInterest:[networkMetricsConsulted ? networkMetricsRoute : networkOverviewConsulted ? "router" : "",networkMetricsEntity,networkMetricsConsulted ? networkMetricsSection : "state",networkMetricsHours,networkMetricsMetric,networkStationId]
    onNetworkMetricsInterestChanged: if (dashboardState) dashboardState.setNetworkMetricsInterest(networkMetricsInterest[0],networkMetricsInterest[1],networkMetricsInterest[2],networkMetricsInterest[3],networkMetricsInterest[4],networkMetricsInterest[5])
    readonly property var networkMetricsView: { const epoch=networkMetricsEpoch; return dashboardState ? dashboardState.networkMetricsView(networkMetricsRoute,networkMetricsEntity,networkMetricsSection,networkMetricsHours,networkMetricsMetric,networkStationId) : ({}) }
    readonly property var networkMetricsRows:networkMetricsView.rows || []
    onNetworkMetricsRowsChanged: networkMetricsIndex=Math.min(networkMetricsIndex,Math.max(0,networkMetricsRows.length-1))
    function openNetworkMetrics(target) {
        const route={"network.router":"networkRouter","network.wifi":"networkWifi","network.ports":"networkPorts"}[target]
        if (!route) return
        networkMetricsSection=target==="network.router" ? "state" : target==="network.wifi" ? "radios" : "ports"
        networkMetricsIndex=0;networkMetricsTabsSelected=true;pushOverlay(route)
    }
    function activateNetworkMetricRow(target) {
        const row=networkMetricsRows.find(r=>r.id===target || r.targetId===target)
        if (!row || !row.targetId) return false
        if (row.id==="metrics.refresh") return dashboardState && dashboardState.refreshNetworkMetrics()
        if (networkMetricsRoute==="wifi" && networkMetricsSection==="radios") { networkWifiEntity=row.targetId; networkMetricsSection="stations" }
        else if (networkMetricsRoute==="wifi" && networkMetricsSection==="stations") { networkStationId=row.targetId; networkMetricsSection="detail" }
        else if (networkMetricsRoute==="ports" && networkMetricsSection==="ports") { networkPortEntity=row.targetId; networkMetricsSection="hosts" }
        else { if (!(networkData.devices || []).some(d=>d.id===row.targetId)) return false; openNetworkDevice(row.targetId);return true }
        networkMetricsIndex=0;networkMetricsTabsSelected=false;return true
    }
    readonly property var networkTabs:["identity","addresses","link","observations"]
    readonly property var networkFiltered:(networkData.devices || []).filter(row => networkFilter===0 || networkFilter===1 && !row.previous && row.statusText==="Raggiungibile secondo box" || networkFilter===2 && row.favourite || networkFilter===3 && row.previous)
    readonly property var networkRows: (viewIndex[7] || 0) === 0 ? (networkData.favourites || []).length ? networkData.favourites : (networkData.devices || []).slice(0,4) : networkFiltered
    readonly property var networkSelected: (networkData.devices || []).find(row => row.id === networkSelectedId) || null
    readonly property var networkDetailRows:networkSelected ? (networkSelected.details || []).filter(row => row.section===networkTabs[networkDetailTab]) : []
    readonly property var networkSettingRows: networkTools.map(r=>({id:r.id,title:r.title,detail:r.detail,value:r.value,actionId:"details.open",targetId:r.targetId,control:"action",enabled:true})).concat([
        {id:"network.devices",title:"Dispositivi e preferiti",detail:"Scegli fino a quattro tessere",value:"APRI",actionId:"details.open",targetId:"network.devices",control:"action",enabled:!!networkData.hasInventory},
        {id:"network.polling",title:"Aggiornamenti automatici",detail:networkData.modeText || "Configura il collegamento iliadbox",value:networkData.polling ? "ATTIVI" : "SOSPESI",actionId:"network.polling.toggle",targetId:"network",control:"toggle",enabled:!!networkData.configured && !networkData.busy},
        {id:"network.reload",title:"Rileggi configurazione",detail:"Credenziale privata e identità della iliadbox",value:"RILEGGI",actionId:"network.config.reload",targetId:"network",control:"action",enabled:!networkData.busy},
        {id:"network.source",title:"Dati e aggiornamenti",detail:network.error || "Ultima lettura e richieste del provider",value:"APRI",actionId:"details.open",targetId:"settings.sources",control:"action",enabled:true}
    ]).concat((networkData.devices || []).map(row => ({id:row.id,title:row.name,detail:row.statusText,value:row.favourite ? "PREFERITO "+((networkData.favourites || []).findIndex(d => d.id === row.id)+1) : "AGGIUNGI",actionId:"network.favourite.toggle",targetId:row.id,control:"toggle",enabled:!networkData.busy && (row.favourite || (networkData.favourites || []).length<4)})))
    function syncNetworkSelection() {
        if (overlay !== "networkDetail" && !networkRows.some(row => row.id === networkSelectedId)) networkSelectedId=networkRows.length ? networkRows[0].id : ""
        networkSettingsIndex=Math.min(networkSettingsIndex,Math.max(0,networkSettingRows.length-1))
    }
    onNetworkDetailRowsChanged: networkDetailIndex=Math.min(networkDetailIndex,Math.max(0,networkDetailRows.length-1))
    onNetworkRowsChanged: Qt.callLater(syncNetworkSelection)
    onNetworkSettingRowsChanged: Qt.callLater(syncNetworkSelection)
    readonly property bool networkConsulted: familyId === "network" && overlay === "" || overlay === "networkDetail" || overlay === "networkSettings"
    onNetworkConsultedChanged: if (dashboardState) dashboardState.setNetworkVisible(networkConsulted)
    function moveNetworkSelection(direction) {
        const index=Math.max(0,networkRows.findIndex(row => row.id===networkSelectedId))
        if (networkTabsSelected) { if (direction>0) networkTabsSelected=false; return }
        if (direction<0 && index===0) { networkTabsSelected=true; return }
        if (networkRows.length) networkSelectedId=networkRows[Math.max(0,Math.min(networkRows.length-1,index+direction))].id
    }
    function openNetworkDevice(identity) { if (networkMetricsRoute!=="") networkMetricsLanReturnId=networkSelectedId; networkSelectedId=identity; networkDetailIndex=0; networkDetailTab=0; pushOverlay("networkDetail") }
    function networkSettingsAction(action,target,direction) {
        if (["network.router","network.wifi","network.ports"].indexOf(target)>=0) { openNetworkMetrics(target); return true }
        if (!dashboardState) return false
        if (action === "network.favourite.toggle") return dashboardState.toggleNetworkFavourite(target)
        if (action === "network.favourite.move") return dashboardState.moveNetworkFavourite(target,direction)
        if (action === "network.config.reload") return dashboardState.reloadNetworkConfig()
        if (action === "network.polling.toggle") return dashboardState.toggleNetworkPolling()
        if (target === "network.devices") { if (!networkData.hasInventory) return false; familyId="network"; const indices=viewIndex.slice(); indices[7]=1; viewIndex=indices; overlay=""; overlayStack=[]; return true }
        if (target === "settings.sources") { openSourceSettings("network"); return true }
        return false
    }
    // Macroareas and provider slots are deliberately independent.
    readonly property var providerFamilies: [
        {id:"sport",slot:3,name:"CALCIO",views:app.sportViews},
        {id:"f1",slot:4,name:"FORMULA 1",views:app.racingViews("f1")},
        {id:"motogp",slot:5,name:"MOTOGP",views:app.racingViews("motogp")}
    ]
    readonly property var allFamilies: [
        {id:"oggi",slot:0,name:"OGGI",views:["ORA","OROLOGIO","GIORNATA"]},
        {id:"meteo",slot:1,name:"METEO",views:["ADESSO","PREVISIONI"]},
        {id:"account",slot:2,name:"ACCOUNT CHATGPT",views:["UTILIZZO"]},
        {id:"sports",slot:3,name:"SPORT",views:["DISCIPLINE"]},
        {id:"casa",slot:6,name:"CASA",views:["PREFERITI","DISPOSITIVI"]},
        {id:"network",slot:7,name:"RETE",views:["PANORAMICA","DISPOSITIVI"]}
    ]
    readonly property var visibleModules: dashboardState ? dashboardState.visibleModules : ["oggi","meteo","account"]
    readonly property bool sportGroupVisible: dashboardState ? dashboardState.sportGroupVisible : false
    readonly property var sportDisciplines: providerFamilies.filter(item => visibleModules.indexOf(item.id)>=0)
    readonly property var families: allFamilies.filter(item => item.id==="sports" ? sportGroupVisible && sportDisciplines.length>0 : visibleModules.indexOf(item.id)>=0)
    onFamiliesChanged: reconcileFamily()
    onSportDisciplinesChanged: {
        if (!notificationInitialized) return
        if (sportDisciplines.length && !sportDisciplines.some(row=>row.id===sportHubSelectedId))
            sportHubSelectedId=sportDisciplines[Math.min(sportHubIndex,sportDisciplines.length-1)].id
        reconcileFamily()
    }
    function reconcileFamily() {
        if (!notificationInitialized) return
        if (sportDisciplines.length && !sportDisciplines.some(row=>row.id===sportHubSelectedId)) sportHubSelectedId=sportDisciplines[0].id
        if (["sport","f1","motogp"].indexOf(familyId)>=0 && visibleModules.indexOf(familyId)<0)
            {
            familyId="sports"
            if (["sportDetail","sportList","sportTable","sportTeam","racingList","racingEvent","racingSession","racingDriver","racingTiming","racingTable"].indexOf(overlay)>=0) {overlay="";overlayStack=[]}
        }
        if (!families.some(item=>item.id===macroFamilyId)) familyId="oggi"
    }
    property string familyId: "oggi"
    readonly property string macroFamilyId: ["sport","f1","motogp"].indexOf(familyId)>=0 ? "sports" : familyId
    readonly property int family: Math.max(0,families.findIndex(item=>item.id===macroFamilyId))
    readonly property var currentFamily: providerFamilies.find(item=>item.id===familyId) || families[family] || allFamilies[0]
    onFamilyIdChanged: sportOverviewInteracted=false
    property string sportHubSelectedId: "sport"
    readonly property int sportHubIndex: Math.max(0,sportDisciplines.findIndex(row=>row.id===sportHubSelectedId))
    readonly property var sportHubRows: sportDisciplines.map(item=>{
        const envelope=item.id==="sport" ? sport : racingStates[item.id] || {},data=envelope.data || {}
        const match=item.id==="sport" ? (data.fixtures || []).filter(row=>row.kickoffUtc>=now.getTime()/1000).sort((a,b)=>a.kickoffUtc-b.kickoffUtc)[0] : (data.events || []).find(event=>event.start>=now.getTime()/1000) || null
        const summary=item.id==="sport" && match ? (match.homeTeam || "")+" – "+(match.awayTeam || "") : match ? match.name || match.title || "Programma disponibile" : "Nessun appuntamento disponibile"
        const status={active:"Aggiornato",stale:"Precedente",offline:"Offline · precedente",updating:"Aggiornamento",error:"Errore",unavailable:"Non disponibile"}[envelope.status] || "Non disponibile"
        return {id:item.id,title:item.name,detail:summary+" · "+status+(envelope.updatedAt ? " · "+eventStamp(envelope.updatedAt) : ""),enabled:true,actionId:"details.open",targetId:item.id,iconId:"sport."+(item.id==="sport" ? "football" : item.id),source:{sourceId:item.id,sourceLabel:envelope.source || "",status:envelope.status || "unavailable",updatedAt:envelope.updatedAt || null,hasData:!!envelope.updatedAt,isStale:envelope.status!=="active"}}
    })
    property var racingRouteStates: ({})
    function rememberDiscipline() {
        if (!isRacing) return
        const saved=Object.assign({},racingRouteStates),entry={}
        for (const key of ["racingEventId","racingSessionId","racingIndex","racingFocusedId","racingDetailPage","racingEventPage","racingInfoIndex","racingDriverId","racingDriverLive","racingDriverPage","racingDriverIndex","racingTimingPage","racingResultIndex","racingStandingTab"])
            entry[key]=app[key]
        saved[familyId]=entry;racingRouteStates=saved
    }
    function openSportDiscipline(id) {
        if (!sportGroupVisible || !sportDisciplines.some(item=>item.id===id)) return false
        rememberDiscipline();sportHubSelectedId=id;familyId=id
        if (isRacing) {
            const saved=racingRouteStates[id] || {}
            for (const key of ["racingEventId","racingSessionId","racingIndex","racingFocusedId","racingDetailPage","racingEventPage","racingInfoIndex","racingDriverId","racingDriverLive","racingDriverPage","racingDriverIndex","racingTimingPage","racingResultIndex","racingStandingTab"])
                app[key]=saved[key]===undefined ? (typeof app[key]==="string" ? "" : typeof app[key]==="boolean" ? false : 0) : saved[key]
        }
        Qt.callLater(function(){presentPage(contentLayer.children.find(host=>host.active))})
        return true
    }
    property var viewIndex: [0, 0, 0, 0, 0, 0, 0, 0]
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
    property var sportListBookmarks: ({})
    property var racingListBookmarks: ({})
    function rememberList() {
        if (overlay==="sportList") {
            const saved=Object.assign({},sportListBookmarks);saved[sportView]={id:sportFocusedId,round:sportRound,index:sportIndex};sportListBookmarks=saved
        }
        if (["racingList","racingTable","racingTiming"].indexOf(overlay)>=0) {
            const saved=Object.assign({},racingListBookmarks);saved[familyId+"|"+racingView]={id:racingFocusedId,index:racingIndex,tab:racingStandingTab,timingPage:racingTimingPage,infoIndex:racingInfoIndex};racingListBookmarks=saved
        }
    }
    function openSportList() {
        const source = sportView === "RISULTATI" ? sportData.lastFinished : sportView === "IN CORSO" ? sportOverviewMatches : sportData.upcoming
        const bookmark=sportListBookmarks[sportView]
        const retained=bookmark && sportFixtures.find(row=>row.canonicalMatchId===bookmark.id && row.round===bookmark.round)
        sportRound = retained ? bookmark.round : source && source.length ? source[0].round : ""
        sportFocusedId = ""; sportIndex = 0; sportListIndex = 0; sportTableIndex = 0
        pushOverlay("sportList")
        const first = source && source.length ? sportRows.findIndex(m => m.canonicalMatchId === source[0].canonicalMatchId) : 0
        sportIndex = retained ? Math.max(0,sportRows.findIndex(row=>row.canonicalMatchId===bookmark.id)) : Math.max(0, first)
        if (retained) sportFocusedId=bookmark.id
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
    property bool sportOverviewInteracted: false
    onSportOverviewPagesChanged: sportOverviewPage = Math.min(sportOverviewPage, sportOverviewPages - 1)
    onSportViewChanged: sportOverviewPage = 0
    Timer {
        objectName: "sportOverviewTimer"
        interval: 8000; repeat: true
        running: app.familyId === "sport" && !app.sportOverviewInteracted && app.overlay === "" && (app.sportView === "PROSSIME" || app.sportView === "IN CORSO") && app.sportOverviewPages > 1
        onTriggered: app.sportOverviewPage = (app.sportOverviewPage + 1) % app.sportOverviewPages
    }
    readonly property var sportMatch: sportTeamDetail ? ((teamData.fixtures || []).find(m => m.canonicalMatchId === sportMatchId) || ({})) : ((overlay === "sportDetail" || overlayStack.indexOf("sportDetail") >= 0 || sportView === "IN CORSO") ? sportFixtures.find(m => m.canonicalMatchId === sportMatchId) : null) ||
        ((overlay === "sportDetail" || overlayStack.indexOf("sportDetail")>=0) && sportMatchId ? ({}) : (sportView === "IN CORSO" ? (sportData.activeMatches || [])[0] : (sportData.upcoming || [])[0])) || ({})
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
        const bookmark=racingListBookmarks[familyId+"|"+racingView]
        racingStandingTab = bookmark ? bookmark.tab : 0; racingIndex = 0; racingFocusedId = ""
        if (racingView === "CLASSIFICA") pushOverlay("racingTable")
        else if (racingView === "IN CORSO") { racingTimingPage = bookmark ? bookmark.timingPage : 0; racingInfoIndex = bookmark ? bookmark.infoIndex : 0; pushOverlay("racingTiming") }
        else {
            pushOverlay("racingList")
            const initial = racingView === "RISULTATI" ? racingData.lastEvent : racingData.nextEvent
            if (initial) racingIndex = Math.max(0, racingRows.findIndex(e => e.id === initial.id))
        }
        const retained=bookmark ? racingRows.findIndex(row=>row.id===bookmark.id) : -1
        if (retained>=0) {racingIndex=retained;racingFocusedId=bookmark.id}
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
    property string alertFocusedId: ""
    property real alertScroll: 0
    property var selectedAlert: ({})
    onSelectedAlertChanged: alertScroll = 0
    onAlertIndexChanged: if (alertItems && alertItems[alertIndex]) alertFocusedId = alertItems[alertIndex].id
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
    onAlertItemsChanged: {
        const index = alertItems.findIndex(item => item.id === alertFocusedId)
        alertIndex = index >= 0 ? index : Math.min(alertIndex, Math.max(0, alertItems.length-1))
        alertFocusedId = alertItems[alertIndex] ? alertItems[alertIndex].id : ""
    }
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
        if (familyId === "sports") return "DISCIPLINE"
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
        pendingNavigationDirection = direction; pendingNavigationVertical = false
        familyId = families[(family + direction + families.length) % families.length].id
        Qt.callLater(function() { presentPage(contentLayer.children.find(host => host.active)) })
    }
    function navigateView(direction) {
        pendingNavigationDirection = direction; pendingNavigationVertical = true
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
        Qt.callLater(function() { presentPage(contentLayer.children.find(host => host.active)) })
    }
    function home() {
        pendingNavigationDirection = -1; pendingNavigationVertical = false
        notificationPreviewMode = ""
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
        Qt.callLater(function() { presentPage(contentLayer.children.find(host => host.active)) })
    }
    property var settingsRouteSelections: ({})
    readonly property var sharedSettingsRoutes: ["appearance","appearanceNotifications","themeManagement","services","sportModules","integrations","accountSettings"]
    function pushOverlay(target) {
        if (sharedSettingsRoutes.indexOf(overlay)>=0) {
            const saved=Object.assign({},settingsRouteSelections);saved[overlay]=optionIndex;settingsRouteSelections=saved
        }
        if (sharedSettingsRoutes.indexOf(target)>=0) optionIndex=settingsRouteSelections[target] || 0
        const stack = overlayStack.slice()
        stack.push(overlay)
        overlayStack = stack
        overlay = target
        if ((target === "appearance" || target === "appearanceNotifications") && themeService && !themeService.editing) themeService.beginEdit()
    }
    function popOverlay() {
        rememberList()
        if ((overlay === "racingEvent" || overlay === "racingTiming") && dashboardState) dashboardState.clearRacingSelection(familyId)
        if (overlay === "sportDetail" && dashboardState) dashboardState.clearFantacalcio()
        if (overlay === "sportDetail" && sportTeamDetail && dashboardState) dashboardState.clearSportTeamSelection()
        if (overlay === "sportTable") sportTableIndex = sportIndex
        if (overlay === "commands" && dashboardState) dashboardState.markCommandsSeen()
        const previous = overlay
        const stack = overlayStack.slice()
        overlay = stack.length ? stack.pop() : ""
        overlayStack = stack
        if (sharedSettingsRoutes.indexOf(overlay)>=0) optionIndex=settingsRouteSelections[overlay] || 0
        if (previous==="networkDetail" && networkMetricsRoute!=="" && networkMetricsLanReturnId) { networkSelectedId=networkMetricsLanReturnId;networkMetricsLanReturnId="" }
        if ((previous === "appearanceNotifications" || previous === "themeManagement") && overlay === "appearance") optionIndex = Math.max(0,settingsPanel.rows.findIndex(row=>row.target===previous || row.id===(previous==="appearanceNotifications" ? "appearance.notifications" : "appearance.management")))
        if (["appearance","appearanceNotifications","themeManagement","system"].indexOf(previous)>=0 && ["appearance","appearanceNotifications","themeManagement","system"].indexOf(overlay)<0 && themeService && themeService.editing) themeService.cancel()
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
        else if (["sport","f1","motogp"].indexOf(familyId)>=0) { rememberDiscipline();sportHubSelectedId=familyId;familyId="sports" }
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
    function notificationAction(mode, action, identifier, argument) {
        if (urgentEvent.id && mode !== "urgent") return false
        if (mode === "urgent") {
            if (identifier !== urgentEvent.id) return false
            const position = ({openDetails:5,dismiss:7,home:1})[action]
            if (!position) return false
            activateKey(position); return true
        }
        if (mode === "small" || mode === "large" || mode === "badge") {
            if (overlay !== "" || (mode !== "badge" && identifier !== bannerEvent.id)) return false
            if (action === "openInbox") { activateKey(3); return true }
            if (action === "home") { home(); return true }
            return false
        }
        if (mode === "inbox" && overlay === "alerts") {
            if (action === "selectEvent" || action === "openDetails") {
                const index = alertItems.findIndex(item => item.id === identifier)
                if (index < 0) return false
                alertIndex = index; alertFocusedId = identifier
                if (action === "openDetails") openSelectedAlert()
                return true
            }
            if (action === "moveSelection") { alertIndex = Math.max(0,Math.min(alertItems.length-1,alertIndex+(argument < 0 ? -1 : 1))); return true }
        } else if (mode === "detail" && overlay === "alertDetail" && action === "scrollDetails") {
            const maximum = detailHost.context ? detailHost.context.scrollMaximum : 0
            const step = Math.max(40,detailHost.height*.65)
            const value = argument && argument.offset !== undefined ? argument.offset : alertScroll+(argument && argument.direction < 0 ? -step : step)
            alertScroll = Math.max(0,Math.min(maximum,value)); return true
        } else if (!(mode === "detail" && overlay === "alertDetail")) return false
        if (action === "back") { back(); return true }
        if (action === "home") { home(); return true }
        return false
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
        if (!traceRecorder) return activateKeyImpl(position)
        const inputId = traceRecorder.beginInput("keypad")
        try { return activateKeyImpl(position) }
        finally { traceRecorder.endInput(inputId) }
    }
    function activateKeyImpl(position) {
        if (familyId === "sport" && position >= 1 && position <= 9) sportOverviewInteracted = true
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
        if (themePreparing && overlay !== "menu") {
            if (position === 1) home()
            else if (position === 7) themeService.cancel()
            else if (position === 9) pushOverlay("menu")
            return
        }
        if (notificationPreviewMode !== "") {
            if (position === 7) notificationPreviewMode = ""
            else if (position === 1) home()
            else if (position === 4 || position === 6) {
                const modes = ["small","large","urgent","badge","inbox","detail"]
                notificationPreviewMode = modes[(modes.indexOf(notificationPreviewMode)+(position === 4 ? -1 : 1)+modes.length)%modes.length]
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
        if (networkMetricsRoute!=="") {
            if (networkMetricsSection==="history") {
                if (position===2 || position===8) networkMetricsHours=networkMetricsHours===1 ? 24 : 1
                else if (position===5) networkMetricsMetric=(networkMetricsMetric+1)%3
            } else if (position===2 || position===8) {
                if (position===2 && networkMetricsIndex===0) networkMetricsTabsSelected=true
                else { networkMetricsTabsSelected=false;networkMetricsIndex=Math.max(0,Math.min(networkMetricsRows.length-1,networkMetricsIndex+(position===2 ? -1 : 1))) }
            } else if (position===5) { if (networkMetricsTabsSelected) networkMetricsTabsSelected=false;else if (networkMetricsRows[networkMetricsIndex]) activateNetworkMetricRow(networkMetricsRows[networkMetricsIndex].id) }
            if (position===4 || position===6) { const i=networkMetricsTabs.indexOf(networkMetricsSection); networkMetricsSection=networkMetricsTabs[(i+(position===4 ? -1 : 1)+networkMetricsTabs.length)%networkMetricsTabs.length];networkMetricsIndex=0 }
            return
        }
        if (overlay === "networkSettings") {
            if (position === 2 || position === 8) networkSettingsIndex=Math.max(0,Math.min(networkSettingRows.length-1,networkSettingsIndex+(position===2 ? -1 : 1)))
            else if (position === 5) { const row=networkSettingRows[networkSettingsIndex]; if (row && row.enabled) networkSettingsAction(row.actionId,row.targetId,1) }
            else if (position === 4 || position === 6) { const row=networkSettingRows[networkSettingsIndex]; if (row && (networkData.favourites || []).some(d => d.id===row.id)) networkSettingsAction("network.favourite.move",row.id,position===4 ? -1 : 1) }
            return
        }
        if (overlay === "networkDetail") {
            if (position===2 || position===8) networkDetailIndex=Math.max(0,Math.min(Math.max(0,networkDetailRows.length-1),networkDetailIndex+(position===2 ? -1 : 1)))
            else if (position===4 || position===6) { networkDetailTab=(networkDetailTab+(position===4 ? -1 : 1)+networkTabs.length)%networkTabs.length; networkDetailIndex=0 }
            else if (position===5 && dashboardState && networkSelectedId) dashboardState.toggleNetworkFavourite(networkSelectedId)
            return
        }
        if (overlay === "casaSettings") {
            if (position === 2 || position === 8) casaSettingsIndex=Math.max(0,Math.min(casaSettingRows.length-1,casaSettingsIndex+(position===2 ? -1 : 1)))
            else if (position === 5) { const row=casaSettingRows[casaSettingsIndex]; if (row && row.enabled) casaSettingsAction(row.actionId,row.targetId,1) }
            else if (position === 4 || position === 6) { const row=casaSettingRows[casaSettingsIndex]; if (row && (casaData.favourites || []).some(d => d.id===row.id)) casaSettingsAction("casa.favourite.move",row.id,position===4 ? -1 : 1) }
            return
        }
        if (overlay === "casaDetail") {
            const count=casaSelected ? casaSelected.metrics.length : 0
            if (position === 2 || position === 8) casaMetricIndex=Math.max(0,Math.min(Math.max(0,count-1),casaMetricIndex+(position===2 ? -1 : 1)))
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
        if (overlay === "alertDetail" && (position === 2 || position === 8)) {
            notificationAction("detail","scrollDetails",selectedAlert.id,{direction:position === 2 ? -1 : 1})
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
                const count = sportDetailPage === 0 ? (sportMatch.events || []).length : sportDetailPage === 1 ? (sportMatch.stats || []).length : sportDetailPage === 2 ? (sportMatch.lineups || []).reduce((n,l) => Math.max(n,(l.players || []).length),0) : 0
                sportDetailOffset = Math.min(Math.max(0, count - 4), sportDetailOffset + 1)
            } else if (position === 5) { if (sportTeamDetail) dashboardState.selectTeamMatch(sportMatchId); else dashboardState.selectSportMatch(sportMatchId) }
            return
        }
        if (overlay !== "") return
        if (familyId === "sports") {
            if (position===4 || position===6) navigateFamily(position===4 ? -1 : 1)
            else if (position===2 || position===8) {
                const index=Math.max(0,Math.min(sportDisciplines.length-1,sportHubIndex+(position===2 ? -1 : 1)))
                if (sportDisciplines[index]) sportHubSelectedId=sportDisciplines[index].id
            } else if (position===5) openSportDiscipline((sportDisciplines[sportHubIndex] || {}).id || "")
            return
        }
        if (["sport","f1","motogp"].indexOf(familyId)>=0 && (position===4 || position===6)) {
            navigateView(position===4 ? -1 : 1);return
        }
        if (familyId === "network") {
            if (position === 4 || position === 6) { if (networkTabsSelected) navigateView(position===4 ? -1 : 1); else navigateFamily(position===4 ? -1 : 1) }
            else if (networkOverviewSection==="tools" && (viewIndex[7] || 0)===0) { if (position===2 || position===8) { if (position===2 && networkToolIndex===0) networkTabsSelected=true;else { networkTabsSelected=false;networkToolIndex=Math.max(0,Math.min(2,networkToolIndex+(position===2 ? -1 : 1))) } } else if (position===5) { if (networkTabsSelected) networkOverviewSection="summary";else openNetworkMetrics(networkTools[networkToolIndex].id) } }
            else if (position === 2 || position === 8) moveNetworkSelection(position===2 ? -1 : 1)
            else if (position === 5) { if (networkTabsSelected) { if ((viewIndex[7] || 0)===0) networkOverviewSection=networkOverviewSection==="tools" ? "summary" : "tools";else networkFilter=(networkFilter+1)%networkFilters.length; } else if (networkSelectedId) openNetworkDevice(networkSelectedId) }
            return
        }
        if (familyId === "casa") {
            if (position === 4 || position === 6) { if (casaTabsSelected) navigateView(position===4 ? -1 : 1); else navigateFamily(position===4 ? -1 : 1) }
            else if (position === 2 || position === 8) moveCasaSelection(position===2 ? -1 : 1)
            else if (position === 5 && casaSelectedId) openCasaDevice(casaSelectedId)
            return
        }
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
        if (themeService) { themeService.setActiveContent(activeContentId); themeService.setPreparedContents(notificationContents.concat(shellHost.active ? ["shell.main"] : []).concat(overlayHost.active ? [overlayHost.contentId] : [])) }
        if (dashboardState) { dashboardState.setBannerPresentationAcknowledgement(true); dashboardState.setCasaVisible(casaConsulted); dashboardState.setNetworkVisible(networkConsulted) }
        notificationInitialized = true
        Qt.callLater(reconcileFamily)
        if (dashboardState && dashboardState.firstRun) pushOverlay("commands")
        updateBannerAvailability()
    }
    function updateBannerAvailability() {
        if (notificationInitialized && dashboardState) dashboardState.setBannerAvailable(overlay === "" && !!smallBanner.currentItem && !!largeBanner.currentItem)
    }
    function acknowledgeBannerFrame() {
        if (dashboardState && events.bannerPending && submittedBanner.id && overlay === "" && !urgentEvent.id) {
            const host = bannerEvent.bannerSize === "large" ? largeBanner : smallBanner
            if (host.show && host.currentReady && host.renderedEvent.id === submittedBanner.id)
                dashboardState.markBannerPresented(submittedBanner.id,submittedBanner.revision,submittedBanner.notificationRank)
        }
    }
    onBannerEventChanged: {
        if (traceRecorder) traceRecorder.traceEvent("notification.banner",{eventId:String(bannerEvent.id || ""),eventRevision:String(bannerEvent.revision || ""),rank:bannerEvent.notificationRank || 0})
        if (events.bannerPending && bannerEvent.id) app.update()
    }
    onAfterAnimating: {
        if (!events.bannerPending) {
            if (submittedBanner.id) submittedBanner = ({})
            return
        }
        submittedBanner = ({})
        if (events.bannerPending && bannerEvent.id && overlay === "" && !urgentEvent.id) {
            const host = bannerEvent.bannerSize === "large" ? largeBanner : smallBanner
            if (host.show && host.currentReady && host.currentLoader.opacity > 0.001 && host.currentItem.opacity > 0.001 && host.renderedEvent.id === bannerEvent.id)
                submittedBanner = {id:bannerEvent.id,revision:bannerEvent.revision || "",notificationRank:bannerEvent.notificationRank}
        }
    }
    onOverlayChanged: {
        if (overlay !== "networkDetail") Qt.callLater(syncNetworkSelection)
        // Read the new route directly: the derived overlayContentId can still
        // name the closing overlay while this change handler is executing.
        const preparedOverlay = publicRoutes[overlay] || ""
        if (themeService) themeService.setPreparedContents(notificationContents.concat(["shell.main"]).concat(preparedOverlay ? [preparedOverlay] : []))
        if (traceRecorder) traceRecorder.traceEvent("navigation.overlay",{route:overlay,surfaceId:traceRecorder.surfaceForRoute(overlay)})
        if (dashboardState) { updateBannerAvailability(); dashboardState.setSystemInfoVisible(overlay === "info") }
    }
    function syncClock() {
        const d = new Date()
        if (d.getMinutes() !== app.now.getMinutes() || d.getDate() !== app.now.getDate()) {
            app.now = d
        }
    }
    function currentThemeRenderCoherent() {
        if (!themeService || themeCandidate.generation) return false
        const hosts=[smallBanner,largeBanner,urgentHost,badgeHost,inboxHost,detailHost,shellHost,overlayHost]
        for (const host of hosts) if (host.active && (!host.currentReady || host.readiness !== "ready" || host.loadedRevision !== themeService.revision)) return false
        for (const host of contentLayer.children) if (host.active && (!host.currentReady || host.readiness !== "ready" || host.loadedRevision !== themeService.revision)) return false
        return !sceneHost.sceneEnabled || sceneHost.currentReady && sceneHost.readiness === "ready"
    }
    Timer {
        interval: 1000; running: !!app.themeService; repeat: true
        onTriggered: {
            app.themeService.heartbeat(app.currentThemeRenderCoherent())
            // A DTO can settle without changing any visible value. Recovering
            // readiness still requires a real submitted frame on an idle HUD.
            if (app.themeService.needsFrameAcknowledgement) app.update()
        }
    }
    property var pendingPublicActions: []
    function completePublicActions(operation,ok,error) {
        const kept=[]
        for (const entry of pendingPublicActions) {
            if (entry.operation === operation) themeService.apiFactory.completeAction(entry.context,entry.requestId,ok,error || "")
            else kept.push(entry)
        }
        pendingPublicActions=kept
    }
    Connections { target: app.dashboardState
        function onSourceRefreshFinished(source,ok,message) { app.completePublicActions("source:"+source,ok,ok ? "" : message) }
        function onNetworkMetricsChanged() { app.networkMetricsEpoch++ }
        function onNetworkMetricsRefreshFinished(ok,message) { app.completePublicActions("networkMetricsRefresh",ok,message) }
        function onNetworkRefreshFinished(ok,message) { app.completePublicActions("networkRefresh",ok,message) }
        function onCasaRefreshFinished(ok,message) { app.completePublicActions("casaRefresh",ok,message) }
    }
    Connections {
        target: app.themeService
        function onSaveFinished(ok) { app.completePublicActions("save",ok,app.themeService.lastError) }
        function onTransferFinished(ok,message) { app.completePublicActions("transfer",ok,ok ? "" : message) }
    }
    Connections {
        target: app.themeService ? app.themeService.apiFactory : null
        function onActionRequested(context,action,targetId,args,requestId) {
            const operation=app.publicActionOperation(action,targetId)
            // Register before dispatch: local Account rereads can finish synchronously.
            if (operation) app.pendingPublicActions=app.pendingPublicActions.concat([{context:context,requestId:requestId,operation:operation}])
            let ok=false, error=""
            try { ok=app.publicDispatch(context,action,targetId,args) } catch (failure) { error=String(failure) }
            if (!ok || !operation) {
                if (operation) app.pendingPublicActions=app.pendingPublicActions.filter(entry => entry.context !== context || entry.requestId !== requestId)
                app.themeService.apiFactory.completeAction(context,requestId,ok,error || (ok ? "" : "Azione non disponibile nello stato corrente"))
            }
            app.restoreInputFocus()
        }
    }
    Timer { objectName: "clockTimer"; interval: 1000; repeat: true; running: true; onTriggered: app.syncClock() }
    onFrameSwapped: {
        acknowledgeBannerFrame()
        if (themeService && themeService.needsFrameAcknowledgement) {
            const coherent=currentThemeRenderCoherent()
            const revision=themeService.revision
            Qt.callLater(function() { if (app.themeService) app.themeService.acknowledgeThemeFrame(revision,coherent) })
        }
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
        id: inputOwner
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

    ShellHost { id: shellHost; z: app.negotiatedLayout && app.negotiatedLayout.guide.height === 0 ? 2 : 0; objectName: "shellHost"; controller: app; style: app.style; anchors.fill: parent; active: app.hasExternalSurface("shell.main") || app.hasCandidateSurface("shell.main"); renderActive: app.hasExternalSurface("shell.main"); interactive: active && app.overlay === "" && !app.urgentEvent.id }
    Rectangle { visible: !shellHost.currentItem || !shellHost.active; x: 0; y: 0; width: 960; height: 5; color: app.accent }
    AppText { visible: !shellHost.currentItem || !shellHost.active; style: app.style; x: 44; y: 26; text: app.currentFamily.name + " · " + app.viewName(); color: app.style.accentTextOnCanvas; font.pixelSize: app.style.font35; font.weight: (true ) ? app.style.headingWeight : app.style.bodyWeight}
    AppText { visible: !shellHost.currentItem || !shellHost.active; style: app.style; x: 790; y: 33; width: 125; horizontalAlignment: Text.AlignRight; text: (app.family + 1) + "/" + app.families.length + "  ·  " + ((app.isRacing ? app.currentFamily.views.indexOf(app.racingView) : app.familyId === "sport" ? app.sportViews.indexOf(app.sportView) : (app.viewIndex[app.currentFamily.slot] || 0)) + 1) + "/" + app.currentFamily.views.length; color: app.muted; font.pixelSize: app.style.font23 }

    Item {
        id: contentLayer
        objectName: "contentLayer"
        x: 0; y: 90; width: 960; height: 455
        PageHost { objectName: "homeNow"; contentId: "home.now"; controller: app; style: app.style; active: app.familyId === "oggi" && app.viewIndex[0] === 0; interactive: active && app.overlay === "" && !app.urgentEvent.id }
        PageHost { objectName: "homeClock"; contentId: "home.clock"; controller: app; style: app.style; active: app.familyId === "oggi" && app.viewIndex[0] === 1; interactive: active && app.overlay === "" && !app.urgentEvent.id }
        PageHost { objectName: "homeDay"; contentId: "home.day"; controller: app; style: app.style; active: app.familyId === "oggi" && app.viewIndex[0] === 2; interactive: active && app.overlay === "" && !app.urgentEvent.id }
        PageHost { objectName: "weatherNow"; contentId: "weather.now"; controller: app; style: app.style; active: app.familyId === "meteo" && app.viewIndex[1] === 0; interactive: active && app.overlay === "" && !app.urgentEvent.id }
        PageHost { objectName: "weatherForecast"; contentId: "weather.forecast"; controller: app; style: app.style; active: app.familyId === "meteo" && app.viewIndex[1] === 1; interactive: active && app.overlay === "" && !app.urgentEvent.id }
        PageHost { objectName: "racingPanel"; contentId: "racing.overview"; controller: app; style: app.style; active: app.isRacing; interactive: active && app.overlay === "" && !app.urgentEvent.id }
        PageHost { objectName:"sportHub";contentId:"sport.hub";controller:app;style:app.style;active:app.familyId==="sports";interactive:active && app.overlay==="" && !app.urgentEvent.id }
        PageHost { objectName: "sportTeamPanel"; contentId: "sport.team"; controller: app; style: app.style; active: app.familyId === "sport" && app.sportView === "LA MIA SQUADRA"; interactive: active && app.overlay === "" && !app.urgentEvent.id }
        PageHost { objectName: "sportPanel"; contentId: "sport.overview"; controller: app; style: app.style; active: app.familyId === "sport" && app.sportView !== "LA MIA SQUADRA"; interactive: active && app.overlay === "" && !app.urgentEvent.id }
        PageHost { objectName:"casaOverview"; contentId:"casa.overview"; controller:app; style:app.style; active:app.familyId==="casa" && (app.viewIndex[6] || 0)===0; interactive:active && app.overlay==="" && !app.urgentEvent.id }
        PageHost { objectName:"casaDevices"; contentId:"casa.devices"; controller:app; style:app.style; active:app.familyId==="casa" && (app.viewIndex[6] || 0)===1; interactive:active && app.overlay==="" && !app.urgentEvent.id }
        PageHost { objectName:"networkOverview"; contentId:"network.overview"; controller:app; style:app.style; active:app.familyId==="network" && (app.viewIndex[7] || 0)===0; interactive:active && app.overlay==="" && !app.urgentEvent.id }
        PageHost { objectName:"networkDevices"; contentId:"network.devices"; controller:app; style:app.style; active:app.familyId==="network" && (app.viewIndex[7] || 0)===1; interactive:active && app.overlay==="" && !app.urgentEvent.id }
        PageHost { objectName: "accountPanel"; contentId: "account.usage"; controller: app; style: app.style; active: app.familyId === "account"; interactive: active && app.overlay === "" && !app.urgentEvent.id }
    }

    AppText { style: app.style; x: 44; y: 614; width: 872; font.pixelSize: app.style.font18; color: app.style.warningOnCanvas; visible: (app.dashboardState && !!app.dashboardState.themeRecoveryError || app.themeService && app.themeService.status === "recovery") && !app.urgentEvent.id; text: app.dashboardState && app.dashboardState.themeRecoveryError ? "ASPETTO DI RECUPERO · ripristinare il pacchetto software" : "ASPETTO DI RECUPERO · controllare Impostazioni → Aspetto" }
    MotionController { id: navigationMotion; traceRecorder: app.traceRecorder; traceOwner: "navigation" }
    MotionController { id: tabMotion; traceRecorder: app.traceRecorder; traceOwner: "tabs" }
    function animateTab() {
        if (!urgentEvent.id && overlay !== "") tabMotion.play(overlay === "sportTeam" ? teamOverlay : overlay.indexOf("racing") === 0 ? racingOverlay : sportOverlay,"tab.change",1,false)
    }
    onTeamTabChanged: animateTab()
    onRacingStandingTabChanged: animateTab()
    readonly property var notificationRegions: [smallBanner,largeBanner,detailHost,inboxHost,badgeHost,urgentHost].filter(host => host.show || host.exiting).reduce((regions,host) => regions.concat(host.context ? host.context.occupiedRegions : [Qt.rect(host.x,host.y,host.width,host.height)]),[])
    SceneHost { id: sceneHost; controller: app; traceRecorder: app.traceRecorder; style: app.style; familyId: app.familyId; occupiedRegions: app.notificationRegions; enforceSafeRegions: !!app.negotiatedLayout; safeRegions: app.negotiatedLayout ? app.negotiatedLayout.sceneSafeRegions : []; notificationEvent: app.urgentEvent.id ? app.urgentEvent : app.bannerEvent; suspended: app.overlay !== "" || !!app.urgentEvent.id || app.night || app.quietActive }
    onUrgentEventChanged: { if (traceRecorder) traceRecorder.traceEvent("notification.urgent",{eventId:String(urgentEvent.id || ""),eventRevision:String(urgentEvent.revision || ""),rank:urgentEvent.notificationRank || 0}); if (urgentEvent.id) { navigationMotion.settle(); tabMotion.settle() } }

    Rectangle { visible: !shellHost.currentItem || !shellHost.active; x: 44; y: 558; width: 872; height: 2; color: app.style.divider }
    AppText { visible: !shellHost.currentItem || !shellHost.active; style: app.style; x: 46; y: 578; text: ["sport","f1","motogp"].indexOf(app.familyId)>=0 ? "4/6  SCHEDE" : (app.familyId === "casa" && app.casaTabsSelected || app.familyId === "network" && app.networkTabsSelected) ? "4/6  VISTA" : "4/6  ARGOMENTO"; color: app.muted; font.pixelSize: app.style.font25 }
    AppText { visible: !shellHost.currentItem || !shellHost.active; style: app.style; x: 351; y: 578; text: app.familyId === "sports" ? "2/8  DISCIPLINE" : app.familyId === "account" ? (app.accountWindows.length > 2 ? "2/8  SCORRI" : "") : (app.familyId === "casa" || app.familyId === "network") ? "2/8  SELEZIONA" : "2/8  VISTA"; color: app.muted; font.pixelSize: app.style.font25 }
    AppText { visible: !shellHost.currentItem || !shellHost.active; style: app.style; x: 669; y: 578; text: app.familyId === "sports" ? "5  APRI" : app.familyId === "account" ? "9  MENU" : app.isRacing ? (app.racingView === "CLASSIFICA" ? "5 CLASSIFICA" : "5 APRI") : app.familyId === "sport" ? (app.sportView === "LA MIA SQUADRA" ? "5  SQUADRA" : app.sportView === "CLASSIFICA" ? "5  CLASSIFICA" : "5  PARTITE") : "5  DETTAGLI"; color: app.style.accentTextOnCanvas; font.pixelSize: app.style.font25 }

    NotificationHost {
        id: badgeHost; z: 3; objectName: "unreadAlertsBadge"; contentId: "alerts.badge"; controller: app
        show: app.familyId === "oggi" && app.overlay === "" && app.unreadAlertCount > 0 && !app.bannerEvent.id && !app.urgentEvent.id
        exitAllowed: false
    }
    AnimatedLayer { // private observer
        id: genericLayer; opacity: overlayHost.active && overlayHost.currentItem ? 0 : 1; traceRecorder: app.traceRecorder; traceSurfaceId: app.traceRecorder ? app.traceRecorder.surfaceForRoute(app.overlay) : ""
        anchors.fill: parent; active: app.networkMetricsRoute==="" && app.overlay !== "networkSettings" && app.overlay !== "networkDetail" && app.overlay !== "casaSettings" && app.overlay !== "casaDetail" && !settingsPanel.active && app.overlay !== "info" && app.overlay !== "alerts" && app.overlay !== "alertDetail" && app.overlay !== "" && app.overlay.indexOf("sport") !== 0 && app.overlay.indexOf("racing") !== 0; preempted: !!app.urgentEvent.id
        eventPrefix: "panel"
        DashboardOverlay { style: parent.style; dashboard: app; visible: true; anchors.fill: parent }
    }
    AnimatedLayer { // private observer
        id: settingsLayer; opacity: overlayHost.active && overlayHost.currentItem ? 0 : 1; traceRecorder: app.traceRecorder; traceSurfaceId: app.traceRecorder ? app.traceRecorder.surfaceForRoute(app.overlay) : ""
        anchors.fill: parent; active: settingsPanel.active; preempted: !!app.urgentEvent.id
        eventPrefix: "panel"
        SettingsPanel { style: parent.style; id: settingsPanel; dashboard: app; visible: true; anchors.fill: parent }
    }
    AnimatedLayer { // private observer
        id: infoLayer; opacity: overlayHost.active && overlayHost.currentItem ? 0 : 1; traceRecorder: app.traceRecorder; traceSurfaceId: app.traceRecorder ? app.traceRecorder.surfaceForRoute(app.overlay) : ""
        anchors.fill: parent; active: app.overlay === "info"; preempted: !!app.urgentEvent.id
        eventPrefix: "panel"
        DeviceInfo { style: parent.style; id: deviceInfo; dashboard: app; visible: true; anchors.fill: parent }
    }
    AnimatedLayer { // private observer
        id: racingLayer; opacity: overlayHost.active && overlayHost.currentItem ? 0 : 1; traceRecorder: app.traceRecorder; traceSurfaceId: app.traceRecorder ? app.traceRecorder.surfaceForRoute(app.overlay) : ""
        anchors.fill: parent; active: app.overlay.indexOf("racing") === 0; preempted: !!app.urgentEvent.id
        eventPrefix: "panel"
        MotorsportOverlay { id: racingOverlay; style: parent.style; dashboard: app; visible: true; anchors.fill: parent }
    }
    AnimatedLayer { // private observer
        id: teamLayer; opacity: overlayHost.active && overlayHost.currentItem ? 0 : 1; traceRecorder: app.traceRecorder; traceSurfaceId: app.traceRecorder ? app.traceRecorder.surfaceForRoute(app.overlay) : ""
        anchors.fill: parent; active: app.overlay.indexOf("sportTeam") === 0; preempted: !!app.urgentEvent.id
        eventPrefix: "panel"
        SportTeamOverlay { id: teamOverlay; style: parent.style; dashboard: app; visible: true; anchors.fill: parent }
    }
    AnimatedLayer { // private observer
        id: sportLayer; opacity: overlayHost.active && overlayHost.currentItem ? 0 : 1; traceRecorder: app.traceRecorder; traceSurfaceId: app.traceRecorder ? app.traceRecorder.surfaceForRoute(app.overlay) : ""
        anchors.fill: parent; active: app.overlay.indexOf("sport") === 0 && app.overlay.indexOf("sportTeam") !== 0; preempted: !!app.urgentEvent.id
        eventPrefix: "panel"
        SportOverlay { id: sportOverlay; style: parent.style; dashboard: app; visible: true; anchors.fill: parent }
    }
    OverlayHost { id: overlayHost; objectName: "overlayHost"; controller: app; style: app.style; contentId: app.overlayContentId.indexOf("alerts.") === 0 ? "" : app.overlayContentId; active: app.hasExternalSurface(contentId) || app.hasCandidateSurface(contentId); renderActive: app.hasExternalSurface(contentId); interactive: active && !app.urgentEvent.id }
    Rectangle { anchors.fill: parent; color: app.style.backgroundOverlay; visible: app.overlay === "alerts" || app.overlay === "alertDetail" }
    ThemeLoading { controller: app }
    NotificationHost {
        id: inboxHost; z: 3; objectName: "alertsInbox"; contentId: "alerts.inbox"; controller: app
        show: app.overlay === "alerts" && !app.urgentEvent.id; preempted: !!app.urgentEvent.id; exitAllowed: false
    }
    NotificationHost {
        id: detailHost; z: 3; objectName: "alertDetail"; contentId: "alerts.detail"; controller: app; eventSource: app.selectedAlert
        show: app.overlay === "alertDetail" && !app.urgentEvent.id; preempted: !!app.urgentEvent.id; exitAllowed: false
    }
    NotificationHost {
        id: smallBanner; z: 3; objectName: "eventBanner"; contentId: "alerts.banner.small"; controller: app; eventSource: app.bannerEvent
        show: !!app.bannerEvent.id && app.bannerEvent.bannerSize !== "large" && app.overlay === "" && !app.urgentEvent.id
        preempted: !!app.urgentEvent.id; exitAllowed: !app.bannerEvent.id && app.overlay === ""
        onCurrentItemChanged: app.updateBannerAvailability()
    }
    NotificationHost {
        id: largeBanner; z: 3; objectName: "eventLargeBanner"; contentId: "alerts.banner.large"; controller: app; eventSource: app.bannerEvent
        show: !!app.bannerEvent.id && app.bannerEvent.bannerSize === "large" && app.overlay === "" && !app.urgentEvent.id
        preempted: !!app.urgentEvent.id; exitAllowed: !app.bannerEvent.id && app.overlay === ""
        onCurrentItemChanged: app.updateBannerAvailability()
    }
    NotificationPreview { id: notificationPreview; controller: app; mode: app.notificationPreviewMode; visible: mode !== "" && !app.urgentEvent.id }
    NotificationHost { id: urgentHost; z: 4; objectName: "eventUrgent"; contentId: "alerts.urgent"; controller: app; eventSource: app.urgentEvent; show: !!app.urgentEvent.id; exitAllowed: false }

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
        AppText { style: app.style; x: 16; y: 12; text: "PANNELLO DEMO · F12"; color: app.style.accentTextOnCanvas; font.pixelSize: app.style.font23; font.weight: (true ) ? app.style.headingWeight : app.style.bodyWeight}
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
