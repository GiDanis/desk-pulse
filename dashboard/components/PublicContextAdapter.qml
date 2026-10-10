import QtQuick

// Application-private adapter. The renderer receives only publicContext.
Item {
    id: adapter
    objectName: "publicContextAdapter"
    visible: false
    required property var factory
    required property var legacy
    required property string surfaceId
    property var publicContext: null
    property bool valid: false
    property bool publicEnabled: true
    property var heldPayload: ({})
    property var selectedModelDomains: null
    property string dataProjection: "full"
    readonly property var modelDomains: selectedModelDomains !== null ? selectedModelDomains : factory && typeof factory.modelDomains === "function"
        ? factory.modelDomains(surfaceId) : ["weather","account","nextEvent","sport","team","fantasy","racing","casa","network"]
    readonly property var payload: {
        if (!publicEnabled) return ({})
        const c = legacy
        if (!c) return ({})
        // Retained, hidden renderers must not subscribe to the whole dashboard.
        // Resume from the current controller transaction before exposing them.
        if (valid && c.active === false && c.exiting !== true)
            return Object.assign({}, heldPayload, {active:false, interactive:false, suspended:true})
        const result = {active:c.active,interactive:c.interactive,style:c.style,
            viewportWidth:c.viewportWidth,viewportHeight:c.viewportHeight,
            appearanceRevision:c.style && c.style.appearance ? c.style.appearance.revision : 0,
            motionMode:c.style && c.style.appearance ? c.style.appearance.motionMode : "off"}
        const keys = ["visualStyle","mode","actions","safeArea","iconId","selection","clockText","dateText","event","items","selectedEventId","unreadCount",
            "sourceStatus","scrollOffset","scrollMaximum","occupiedRegions","preview","exiting","ready","error",
            "commandHints","guideText","sourceText","validityText","actorState","notificationEvent","configuration","suspended"]
        for (const key of keys) if (c[key] !== undefined) result[key] = c[key]
        // Marshal only provider domains defined by this context. Shell, menu,
        // settings and notifications must never copy a complete Sport tree.
        if (modelDomains.length && c.model) {
            const model = {}
            for (const domain of modelDomains) if (c.model[domain] !== undefined) model[domain] = c.model[domain]
            result.model = model
        }
        if (c.controller) {
            const app = c.controller
            if ((surfaceId === "sport.standings" || surfaceId === "sport.fixtures") && result.model && result.model.sport && app.sportRounds !== undefined) {
                const envelope=result.model.sport, data=envelope.data || ({})
                const rounds=data.rounds && data.rounds.length ? data.rounds : app.sportRounds.map(id => ({id:String(id),label:String(id)}))
                result.model.sport=Object.assign({},envelope,{data:{standings:data.standings || [],rounds:rounds,
                    favouriteTeamId:data.favouriteTeamId || data.favourite || "",fixtures:[]}})
                // Rows are supplied by publicSurfacePayload below in keypad order.
            }
            if (dataProjection === "route" && result.model && surfaceId === "sport.overview" && result.model.sport) {
                const envelope = result.model.sport, data = envelope.data || ({})
                const matches = app.sportView === "CLASSIFICA" ? [] : app.sportView === "RISULTATI" ? data.lastFinished || [] : app.sportOverviewMatches.slice(app.sportOverviewPage*app.style.overviewRows,(app.sportOverviewPage+1)*app.style.overviewRows)
                result.model.sport = Object.assign({},envelope,{data:{competitionId:data.competitionId,competitionName:data.competitionName,season:data.season,
                    calendarScope:data.calendarScope,fixtures:matches,standings:app.sportView === "CLASSIFICA" ? data.standings || [] : [],
                    favouriteTeamId:data.favouriteTeamId || data.favourite || "",hasLiveView:!!data.hasLiveView,
                    activeLiveVerified:!!data.activeLiveVerified,partialError:data.partialError || "",rounds:data.rounds || []}})
            }
            if (dataProjection === "route" && result.model && surfaceId === "racing.overview" && result.model.racing) {
                const envelope=result.model.racing, data=envelope.data || ({})
                // Overview cards use event metadata, never nested session results,
                // driver laps or pit-stop trees. Details keep the full provider.
                const events=(data.events || []).map(row => ({id:row.id,name:row.name,roundId:row.roundId || row.round || "",
                    startsAt:row.startsAt === undefined ? row.start : row.startsAt,
                    endsAt:row.endsAt === undefined ? row.end : row.endsAt,circuit:row.circuit || ""}))
                result.model.racing=Object.assign({},envelope,{data:{kind:app.familyId === "motogp" ? "motogp" : "f1",year:data.year,
                    events:events,standings:app.racingView === "CLASSIFICA" ? data.standings || [] : [],constructors:[],
                    live:app.racingView === "IN CORSO" ? data.live || ({}) : ({}),
                    detailLoading:!!data.detailLoading,detailError:data.detailError || "",partialError:data.partialError || ""}})
            }
            if (dataProjection === "route" && result.model && surfaceId === "sport.team" && result.model.team) {
                const envelope = result.model.team, data = envelope.data || ({})
                result.model.team = Object.assign({},envelope,{data:Object.assign({},data,{fixtures:(data.fixtures || []).filter(row => row.status !== "finished" && row.status !== "cancelled").slice(0,3)})})
            }
            result.epoch = app.now.getTime()/1000
            result.night = c.style && c.style.appearance ? c.style.appearance.variant === "night" : !!app.night
            result.familyId = app.familyId
            result.route = app.overlay
            result.urgent = !!app.urgentEvent.id
            result.suspended = c.active === false || !!app.urgentEvent.id && surfaceId !== "alerts.urgent"
            if (typeof app.publicSurfacePayload === "function") Object.assign(result,app.publicSurfacePayload(surfaceId,dataProjection))
            if (dataProjection === "route" && surfaceId === "racing.overview") {
                result.rows=[]
                result.selection=Object.assign({},result.selection,{selectedId:"",index:-1})
            }
            if (dataProjection === "route" && surfaceId === "sport.overview") {
                result.rows = []
                const data=result.model.sport.data
                result.selection = Object.assign({},result.selection,{selectedId:"",index:-1,count:(app.sportView === "CLASSIFICA" ? data.standings : data.fixtures).length})
            }
        }
        if (c.actorState) {
            const actor=c.actorState
            result.actor={actorId:actor.actorId,pose:actor.pose,locomotion:actor.locomotion,sequence:actor.sequence,
                paused:actor.paused,anchor:{x:actor.anchor.x,y:actor.anchor.y},motionMode:actor.motionMode}
        }
        return result
    }
    function refresh() {
        if (!factory || !publicContext || disposed) return
        const snapshot = payload
        if (!valid || legacy.active !== false || legacy.exiting === true) heldPayload = snapshot
        valid = factory.updateLegacy(publicContext,snapshot)
    }
    // A completed public action must expose its resulting state synchronously.
    function flushRefresh() {
        if (disposed) return
        refreshScheduled = true
        refresh()
        refreshScheduled = false
    }
    // One provider/navigation transaction can invalidate several dependent
    // bindings. Publish its final snapshot once before the next GUI frame.
    // Initial creation remains synchronous for the renderer's required context.
    property bool refreshScheduled: false
    property bool disposed: false
    function scheduleRefresh() {
        if (refreshScheduled || disposed || !publicContext) return
        refreshScheduled = true
        Qt.callLater(function() {
            if (!refreshScheduled) return
            if (!disposed) refresh()
            refreshScheduled = false
        })
    }
    onPayloadChanged: scheduleRefresh()
    function initialize() {
        if (!factory || !publicEnabled || publicContext) return
        // Private bridge: build the validated initial tree once. Older factories
        // retain the default-then-update path, including invalid-payload recovery.
        if (typeof factory.createLegacy === "function") {
            const snapshot = payload
            publicContext = factory.createLegacy(surfaceId,snapshot,adapter)
            if (publicContext) { heldPayload = snapshot; valid = true; return }
        }
        publicContext = factory.create(surfaceId,adapter)
        refresh()
    }
    onPublicEnabledChanged: initialize()
    Component.onCompleted: initialize()
    Component.onDestruction: {
        disposed = true
        if (factory && publicContext) factory.release(publicContext)
    }
}
