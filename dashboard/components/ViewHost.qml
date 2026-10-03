import QtQuick
import "../themes"
Item {
    id: host
    required property string contentId
    required property var controller
    property StyleFacade style: Theme
    property var appearance: Theme.appearance
    property var service: controller.themeService
    property bool active: false
    property bool renderActive: active
    property bool exiting: false
    property bool animateSwap: true
    property bool interactive: active
    property Component contextFactory: Component {
        PresentationContext {
            contentId: host.contentId; controller: host.controller
            viewportWidth: host.width; viewportHeight: host.height
        }
    }
    property var currentItem: null
    property string readiness: "idle"
    property string lastError: ""
    property int loadedRevision: 0
    property int generation: 0
    property string loadedPresentationId: ""
    property var pendingLoader: null
    property var currentLoader: null
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
        if (active) prepare(appearance,0)
        else if (pendingLoader) { generation += 1; pendingLoader.destroy(); pendingLoader = null; readiness = currentItem ? "ready" : "idle" }
    }
    onInteractiveChanged: if (context) context.interactive = interactive
    onAppearanceChanged: if (active) prepare(appearance,0)
    onContentIdChanged: if (active) prepare(appearance,0)
    Connections {
        target: host.service
        function onCandidateChanged() {
            const candidate = host.service.candidateAppearance
            if (candidate.generation && host.active && candidate.requiredContents.indexOf(host.contentId) >= 0) host.prepare(candidate,candidate.generation)
            else if (host.pendingLoader && host.pendingLoader.serviceGeneration) {
                host.generation += 1; host.pendingLoader.destroy(); host.pendingLoader = null
                host.readiness = host.currentItem ? "ready" : "idle"
            }
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
        const old = currentLoader
        currentLoader = candidate; context = candidate.presentationContext; currentItem = candidate.item
        candidate.useLiveStyle = true
        candidate.stagedAppearance = null
        context.active = renderActive; context.interactive = interactive
        layoutMotion.settle()
        if (old) {
            old.presentationContext.active = false; old.presentationContext.interactive = false
            if (old.item && typeof old.item.settleMotion === "function") old.item.settleMotion()
            old.destroy()
        }
        pendingLoader = null; loadedPresentationId = candidate.presentationId
        loadedRevision = appearance.revision; readiness = "ready"
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
        const identifier = snapshot.presentations[contentId]
        if (!serviceGeneration && pendingLoader && pendingLoader.presentationId === identifier && pendingLoader.status === Loader.Ready) { commit(pendingLoader); return }
        if (currentItem && loadedPresentationId === identifier) { loadedRevision = snapshot.revision; readiness = "ready"; return }
        generation += 1
        if (pendingLoader) { pendingLoader.destroy(); pendingLoader = null }
        const descriptor = snapshot.presentationRegistry[identifier]
        if (!descriptor) {
            readiness = currentItem ? "ready" : "error"; lastError = "Presentazione non registrata: " + identifier
            if (serviceGeneration && service) service.reportCandidate(serviceGeneration,contentId,false,lastError)
            return
        }
        readiness = "loading"; lastError = ""
        const next = slot.createObject(host, {requestGeneration: generation, presentationId: identifier, requestedRevision: snapshot.revision,
            serviceGeneration: serviceGeneration, stagedAppearance: snapshot})
        pendingLoader = next
        next.setSource(Qt.resolvedUrl("../"+descriptor.file), {context: next.presentationContext})
        next.active = true
    }
    MotionController { id: layoutMotion; appearance: host.appearance }
    Component.onCompleted: prepare(appearance,0)
    Component {
        id: slot
        Loader {
            id: candidate
            property int requestGeneration: 0
            property int serviceGeneration: 0
            property string presentationId: ""
            property int requestedRevision: 0
            property var stagedAppearance: null
            property bool useLiveStyle: false
            property StyleFacade stagedStyle: StyleFacade { appearance: candidate.stagedAppearance }
            property var presentationContext: host.contextFactory.createObject(candidate)
            Binding { target: candidate.presentationContext; property: "style"; value: candidate.useLiveStyle ? host.style : candidate.stagedStyle }
            active: false; asynchronous: true
            visible: host.currentLoader === candidate
            width: host.width; height: host.height
            property bool acknowledged: false
            function ready() {
                if (status !== Loader.Ready || acknowledged || item.presentationReady === false) return
                if (requestGeneration !== host.generation || !host.active) { destroy(); return }
                acknowledged = true
                if (serviceGeneration) host.service.reportCandidate(serviceGeneration,host.contentId,true,"")
                else host.commit(candidate)
            }
            function fail(message) {
                if (requestGeneration !== host.generation) return
                host.lastError = message
                host.readiness = host.currentItem ? "ready" : "error"
                host.pendingLoader = null
                const failedGeneration = serviceGeneration
                destroy()
                if (failedGeneration) host.service.reportCandidate(failedGeneration,host.contentId,false,message)
                else if (!host.currentItem && host.service) host.service.recoverVisual(host.contentId,message)
            }
            onLoaded: ready()
            onStatusChanged: if (status === Loader.Error) fail("Errore caricamento " + presentationId)
            Connections {
                target: candidate.item; ignoreUnknownSignals: true
                function onPresentationReadyChanged() { candidate.ready() }
            }
            Timer {
                interval: 3000
                running: candidate.active && candidate.status === Loader.Ready && !candidate.acknowledged
                onTriggered: candidate.fail("Timeout preparazione " + candidate.presentationId)
            }
        }
    }
}
