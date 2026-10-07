import QtQuick
import "../themes"
Item {
    id: host
    required property string contentId
    required property var controller
    readonly property var traceRecorder: controller && controller.traceRecorder !== undefined ? controller.traceRecorder : null
    property string traceInstanceId: ""
    property string traceRole: "live"
    readonly property bool traceMotionRunning: (layoutMotion.running || !layoutMotion.runningKnown)
    function traceIdentity() {
        if (traceRecorder && !traceInstanceId) traceInstanceId = traceRecorder.allocateInstance(contentId,traceRole)
        return traceInstanceId
    }
    function traceEvent(name, values) {
        if (!traceRecorder) return
        traceRecorder.invalidate(name)
        traceRecorder.traceEvent(name,Object.assign({instanceId:traceIdentity(),surfaceId:contentId,
            localGeneration:generation,revision:loadedRevision,rendererIdentity:loadedPresentationId,role:traceRole},values || {}))
    }
    function traceParticipant(mandatory) {
        const presence = controller.themeTracePresence(host,currentLoader)
        return {instanceId:traceIdentity(),surfaceId:contentId,revision:exiting ? style.appearance.revision : loadedRevision,
            observedRevision:style.appearance ? style.appearance.revision : -1,committedRevision:loadedRevision,exposed:presence.exposed,
            frontCommitted:!!currentItem && loadedRendererKey === rendererKey(style.appearance,style.appearance.presentations[contentId]),
            frontCommittedRevision:style.appearance.revision,frontReady:currentReady,
            frontRendererIdentity:loadedRendererKey,frontExpectedRendererIdentity:rendererKey(style.appearance,style.appearance.presentations[contentId]),
            mandatory:mandatory,committed:!!currentItem && readiness === "ready",ready:currentReady,
            geometryValid:presence.geometryValid,opacity:presence.opacity,visualGeometry:presence.visualGeometry,rendererIdentity:loadedRendererKey,
            localGeneration:generation,motionRunning:layoutMotion.traceRunningNow(),retainedExit:exiting,actionsEnabled:interactive}
    }
    Connections {
        target: host.traceRecorder ? host : null
        function onXChanged() { host.traceRecorder.invalidate("host.geometry") }
        function onYChanged() { host.traceRecorder.invalidate("host.geometry") }
        function onWidthChanged() { host.traceRecorder.invalidate("host.geometry") }
        function onHeightChanged() { host.traceRecorder.invalidate("host.geometry") }
        function onVisibleChanged() { host.traceRecorder.invalidate("host.visibility") }
        function onOpacityChanged() { host.traceRecorder.invalidate("host.opacity") }
    }
    Connections {
        target: host.traceRecorder ? host.currentLoader : null
        function onXChanged() { host.traceRecorder.invalidate("loader.geometry") }
        function onYChanged() { host.traceRecorder.invalidate("loader.geometry") }
        function onWidthChanged() { host.traceRecorder.invalidate("loader.geometry") }
        function onHeightChanged() { host.traceRecorder.invalidate("loader.geometry") }
        function onVisibleChanged() { host.traceRecorder.invalidate("loader.visibility") }
        function onOpacityChanged() { host.traceRecorder.invalidate("loader.opacity") }
    }
    Connections {
        target: host.traceRecorder ? host.currentItem : null
        function onWidthChanged() { host.traceRecorder.invalidate("renderer.geometry") }
        function onHeightChanged() { host.traceRecorder.invalidate("renderer.geometry") }
        function onVisibleChanged() { host.traceRecorder.invalidate("renderer.visibility") }
        function onOpacityChanged() { host.traceRecorder.invalidate("renderer.opacity") }
    }
    property StyleFacade style: Theme
    property var appearance: Theme.appearance
    property var service: controller.themeService
    // The application marshals one immutable candidate map per change. Hosts
    // share that QML snapshot; standalone hosts keep a single local binding.
    readonly property var candidateSnapshot: controller && controller.themeCandidate !== undefined
        ? controller.themeCandidate : (service ? service.candidateAppearance : ({}))
    property bool active: false
    property bool renderActive: active
    property bool exiting: false
    property bool animateSwap: true
    property int cacheLimit: 0
    property var retainedLoaders: []
    property bool interactive: active
    property Component contextFactory: Component {
        PresentationContext {
            contentId: host.contentId; controller: host.controller
            viewportWidth: host.width; viewportHeight: host.height
        }
    }
    property var currentItem: null
    readonly property bool currentContextReady: !currentLoader || !currentLoader.usePublicApi ||
        (currentLoader.publicAdapter.valid && !currentLoader.publicAdapter.refreshScheduled)
    readonly property bool currentReady: !!currentItem && currentContextReady && (currentLoader && currentLoader.usePublicApi ? currentItem.ready === true && currentItem.contentReady !== false : currentItem.presentationReady !== false)
    property string readiness: "idle"
    property string lastError: ""
    property int loadedRevision: 0
    property int generation: 0
    property string loadedPresentationId: ""
    property string loadedRendererKey: ""
    function rendererKey(snapshot, identifier, surface) {
        const row = snapshot.presentationRegistry[identifier]
        return row ? (row.rendererKey || "app:"+row.file)+":"+(surface || contentId) : ""
    }
    function clearRetained() {
        const loaders = retainedLoaders
        retainedLoaders = []
        for (const loader of loaders) loader.destroy()
    }
    function retainOrDestroy(loader) {
        if (!cacheLimit || loader.rendererKey !== rendererKey(appearance,loader.presentationId,loader.surfaceId)) {
            loader.destroy(); return
        }
        loader.stagedAppearance = appearance
        loader.useLiveStyle = false
        const loaders = retainedLoaders.concat([loader])
        while (loaders.length > cacheLimit) loaders.shift().destroy()
        retainedLoaders = loaders
    }
    function restoreInput() { if (controller && typeof controller.restoreInputFocus === "function") controller.restoreInputFocus() }
    property var pendingLoader: null
    property var currentLoader: null
    readonly property string currentSurfaceId: currentLoader ? currentLoader.surfaceId : ""
    property var context: null
    width: 872; height: 455
    visible: renderActive || exiting
    onRenderActiveChanged: if (context) { context.active = renderActive; context.interactive = interactive }
    onActiveChanged: {
        if (context) { context.active = renderActive; context.interactive = interactive }
        if (currentLoader) {
            if (!active) currentLoader.stagedAppearance = appearance
            currentLoader.useLiveStyle = active
            if (active) currentLoader.stagedAppearance = null
        }
        if (active) {
            const candidate=candidateSnapshot
            if (candidate.generation && candidate.requiredContents.indexOf(contentId) >= 0) prepare(candidate,candidate.generation)
            else prepare(appearance,0)
        }
        else if (pendingLoader) { generation += 1; pendingLoader.destroy(); pendingLoader = null; readiness = currentItem ? "ready" : "idle" }
    }
    onInteractiveChanged: if (context) context.interactive = interactive
    onAppearanceChanged: {
        const loaders = retainedLoaders.filter(loader => {
            if (loader.rendererKey === rendererKey(appearance,loader.presentationId,loader.surfaceId)) return true
            loader.destroy(); return false
        })
        retainedLoaders = loaders
        if (!active && currentLoader && currentLoader.rendererKey !== rendererKey(appearance,currentLoader.presentationId,currentLoader.surfaceId)) {
            const obsolete = currentLoader
            currentLoader = null; currentItem = null; context = null; readiness = "idle"
            obsolete.destroy()
        }
        if (active) prepare(appearance,0)
    }
    onContentIdChanged: if (active) prepare(appearance,0)
    onCandidateSnapshotChanged: {
            const candidate = candidateSnapshot
            if (candidate.generation && host.active && candidate.requiredContents.indexOf(host.contentId) >= 0) host.prepare(candidate,candidate.generation)
            else if (host.pendingLoader && host.pendingLoader.serviceGeneration) {
                host.generation += 1; host.pendingLoader.destroy(); host.pendingLoader = null
                host.readiness = host.currentItem ? "ready" : "idle"
            }
    }
    function dataUpdated(domain) {
        const ownsDomain = contentId.indexOf(domain+".") === 0 || domain === "weather" && contentId.indexOf("home.") === 0
        if (ownsDomain && active && interactive && currentLoader && readiness === "ready") layoutMotion.play(currentLoader,"data.update",1,false)
    }
    Connections {
        target: host.controller
        function onWeatherChanged() { host.dataUpdated("weather") }
        function onAccountChanged() { host.dataUpdated("account") }
        function onSportChanged() { host.dataUpdated("sport") }
        function onRacingChanged() { host.dataUpdated("racing") }
    }
    function commit(candidate) {
        if (traceRecorder) traceEvent("host.commit.begin",{candidateGeneration:candidate.requestGeneration,serviceGeneration:candidate.serviceGeneration,targetRevision:candidate.requestedRevision})
        const old = currentLoader
        currentLoader = candidate; context = candidate.presentationContext; currentItem = candidate.item
        candidate.useLiveStyle = true
        candidate.stagedAppearance = null
        context.active = renderActive; context.interactive = interactive
        layoutMotion.settle()
        if (old) {
            old.presentationContext.active = false; old.presentationContext.interactive = false
            if (old.item && typeof old.item.settleMotion === "function") old.item.settleMotion()
            retainOrDestroy(old)
        }
        pendingLoader = null; loadedPresentationId = candidate.presentationId; loadedRendererKey = candidate.rendererKey
        restoreInput()
        loadedRevision = appearance.revision; readiness = "ready"
        if (traceRecorder) traceEvent("host.commit.end",{serviceGeneration:candidate.serviceGeneration})
        if (old && renderActive && animateSwap) {
            const revision = loadedRevision
            Qt.callLater(function() {
                if (host.currentLoader === candidate && host.renderActive && host.appearance.revision === revision)
                    layoutMotion.play(candidate,"layout.swap",1,false)
            })
        }
    }
    function prepare(snapshot,serviceGeneration) {
        if (!active || !snapshot) return
        if (traceRecorder) traceEvent("host.prepare",{targetRevision:snapshot.revision,serviceGeneration:serviceGeneration})
        const identifier = snapshot.presentations[contentId]
        if (!serviceGeneration && pendingLoader && pendingLoader.rendererKey === rendererKey(snapshot,identifier) && pendingLoader.status === Loader.Ready) { commit(pendingLoader); return }
        if (currentItem && loadedRendererKey === rendererKey(snapshot,identifier)) { loadedRevision = snapshot.revision; readiness = "ready"; if (traceRecorder) traceEvent("host.reuse",{targetRevision:snapshot.revision,serviceGeneration:serviceGeneration}); return }
        generation += 1
        if (pendingLoader) { pendingLoader.destroy(); pendingLoader = null }
        if (!serviceGeneration) {
            const key = rendererKey(snapshot,identifier)
            const cachedIndex = retainedLoaders.findIndex(loader => loader.rendererKey === key)
            if (cachedIndex >= 0) {
                const loaders = retainedLoaders.slice()
                const cached = loaders.splice(cachedIndex,1)[0]
                retainedLoaders = loaders
                pendingLoader = cached
                cached.requestGeneration = generation
                cached.requestedRevision = snapshot.revision
                cached.serviceGeneration = 0
                cached.acknowledged = true
                cached.useLiveStyle = true
                cached.presentationContext.active = renderActive
                cached.presentationContext.interactive = interactive
                readiness = "loading"
                cached.publicAdapter.flushRefresh()
                cached.acknowledged = false
                if (traceRecorder) traceEvent("host.cache.reuse",{targetRevision:snapshot.revision})
                cached.ready()
                return
            }
        }
        const descriptor = snapshot.presentationRegistry[identifier]
        if (!descriptor) {
            readiness = currentItem ? "ready" : "error"; lastError = "Presentazione non registrata: " + identifier
            if (serviceGeneration && service) service.reportCandidate(serviceGeneration,contentId,false,lastError)
            return
        }
        readiness = "loading"; lastError = ""
        const next = slot.createObject(host, {requestGeneration: generation, presentationId: identifier, requestedRevision: snapshot.revision,
            surfaceId: contentId,
            serviceGeneration: serviceGeneration, stagedAppearance: snapshot,
            rendererKey: rendererKey(snapshot,identifier), usePublicApi: descriptor.apiVersion === 2,
            dataProjection: descriptor.dataProjection || "full",
            dataDomains: descriptor.dataDomains === undefined ? null : descriptor.dataDomains})
        pendingLoader = next
        if (service && descriptor.rendererIdentity) {
            next.resourceLease=service.acquireRevision(descriptor.rendererIdentity)
            if (!next.resourceLease) { next.fail("Risorsa tema non disponibile: "+identifier); return }
        }
        if (traceRecorder) traceEvent("host.loader.begin",{presentationId:identifier,targetRevision:snapshot.revision,serviceGeneration:serviceGeneration})
        if (next.usePublicApi && service && service.apiFactory) service.apiFactory.installForEngine(next)
        next.setSource(descriptor.sourceUrl || Qt.resolvedUrl("../"+descriptor.file), {context: next.usePublicApi ? next.publicAdapter.publicContext : next.presentationContext})
        next.active = true
    }
    MotionController { id: layoutMotion; appearance: host.appearance; traceRecorder: host.traceRecorder; traceOwner: host.traceInstanceId }
    Component.onCompleted: prepare(appearance,0)
    Component {
        id: slot
        Loader {
            id: candidate
            property int requestGeneration: 0
            property int serviceGeneration: 0
            property string presentationId: ""
            property string surfaceId: ""
            property string rendererKey: ""
            property bool usePublicApi: false
            property var dataDomains: null
            property string dataProjection: "full"
            property string resourceLease: ""
            Component.onDestruction: if (resourceLease && host.service) host.service.releaseRevision(resourceLease)
            property alias publicAdapter: publicAdapter
            PublicContextAdapter { id: publicAdapter; publicEnabled: candidate.usePublicApi; selectedModelDomains: candidate.dataDomains; dataProjection:candidate.dataProjection; factory: host.service ? host.service.apiFactory : null; legacy: candidate.presentationContext; surfaceId: candidate.surfaceId }
            property int requestedRevision: 0
            property var stagedAppearance: null
            property bool useLiveStyle: false
            property StyleFacade stagedStyle: StyleFacade { appearance: candidate.stagedAppearance }
            property var presentationContext: host.contextFactory.createObject(candidate, {contentId:candidate.surfaceId})
            Binding { target: candidate.presentationContext; property: "style"; value: candidate.useLiveStyle ? host.style : candidate.stagedStyle }
            active: false; asynchronous: true
            visible: host.currentLoader === candidate
            width: host.width; height: host.height
            property bool acknowledged: false
            function ready() {
                if (status !== Loader.Ready || acknowledged) return
                if (usePublicApi) {
                    if (publicAdapter.refreshScheduled) return
                    if (!publicAdapter.valid) { fail("Contratto dati pubblico non valido: "+presentationId); return }
                    if (item.ready === undefined) { fail("Renderer API 2 senza ready: "+presentationId); return }
                    if (item.error !== undefined && item.error) { fail("Errore renderer: "+String(item.error)); return }
                    if (item.ready !== true || item.contentReady === false) return
                } else if (item.presentationReady === false) return
                if (requestGeneration !== host.generation || !host.active) { destroy(); return }
                acknowledged = true
                if (host.traceRecorder) host.traceEvent("host.presentation.ready",{candidateGeneration:requestGeneration,serviceGeneration:serviceGeneration,targetRevision:requestedRevision,presentationId:presentationId})
                if (serviceGeneration) host.service.reportCandidate(serviceGeneration,host.contentId,true,"")
                else host.commit(candidate)
            }
            function fail(message) {
                if (requestGeneration !== host.generation) return
                if (host.traceRecorder) host.traceEvent("host.loader.fail",{candidateGeneration:requestGeneration,serviceGeneration:serviceGeneration,errorKind:status === Loader.Error ? "loadError" : status === Loader.Loading ? "loadingTimeout" : "presentationTimeout"})
                host.lastError = message
                host.readiness = host.currentItem ? "ready" : "error"
                host.restoreInput()
                host.pendingLoader = null
                const failedGeneration = serviceGeneration
                const live = host.currentLoader === candidate
                if (live && host.service) host.service.recoverVisual(host.contentId,message)
                destroy()
                if (failedGeneration) {
                    Qt.callLater(function() {
                        if (host.service) host.service.reportCandidate(failedGeneration, host.contentId, false, message)
                    })
                }
                else if (!host.currentItem && host.service) host.service.recoverVisual(host.contentId,message)
            }
            Connections {
                target: publicAdapter
                function onRefreshScheduledChanged() { if (!publicAdapter.refreshScheduled) candidate.ready() }
            }
            onLoaded: { if (host.traceRecorder) host.traceEvent("host.loader.ready",{candidateGeneration:requestGeneration,serviceGeneration:serviceGeneration,targetRevision:requestedRevision}); ready() }
            onStatusChanged: if (status === Loader.Error) fail("Errore caricamento " + presentationId)
            Connections {
                target: candidate.item; ignoreUnknownSignals: true
                function onPresentationReadyChanged() { candidate.ready() }
                function onReadyChanged() { candidate.ready() }
                function onContentReadyChanged() { candidate.ready() }
                function onErrorChanged() { if (candidate.item && candidate.item.error) candidate.fail("Errore renderer: "+String(candidate.item.error)) }
            }
            // Loading and presentation readiness have independent watchdogs.
            Timer {
                interval: 3000
                running: candidate.active && candidate.status === Loader.Loading
                onTriggered: candidate.fail("Timeout caricamento " + candidate.presentationId)
            }
            Timer {
                interval: 3000
                running: candidate.active && candidate.status === Loader.Ready && !candidate.acknowledged
                onTriggered: candidate.fail("Timeout preparazione " + candidate.presentationId)
            }
        }
    }
}
