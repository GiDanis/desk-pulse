import QtQuick
import "../themes"
Item {
    id: host
    required property string contentId
    required property var controller
    property StyleFacade style: Theme
    property var appearance: Theme.appearance
    readonly property var service: controller.themeService
    property bool active: false
    property bool interactive: active
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
    visible: active
    onActiveChanged: {
        if (context) { context.active = active; context.interactive = interactive }
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
    Connections {
        target: host.service
        function onCandidateChanged() {
            const candidate = host.service.candidateAppearance
            if (candidate.generation && host.active) host.prepare(candidate,candidate.generation)
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
        currentLoader = candidate; currentItem = candidate.item; context = candidate.presentationContext
        candidate.useLiveStyle = true
        candidate.stagedAppearance = null
        context.active = active; context.interactive = interactive
        layoutMotion.settle()
        if (old) { old.presentationContext.active = false; old.presentationContext.interactive = false; old.destroy() }
        pendingLoader = null; loadedPresentationId = candidate.presentationId
        loadedRevision = appearance.revision; readiness = "ready"
        if (old) layoutMotion.play(candidate,"layout.swap",1,false)
    }
    function prepare(snapshot,serviceGeneration) {
        if (!active || !snapshot) return
        const identifier = snapshot.presentations[contentId]
        if (!serviceGeneration && pendingLoader && pendingLoader.presentationId === identifier && pendingLoader.status === Loader.Ready) { commit(pendingLoader); return }
        if (currentItem && loadedPresentationId === identifier) { loadedRevision = snapshot.revision; readiness = "ready"; return }
        generation += 1
        if (pendingLoader) { pendingLoader.destroy(); pendingLoader = null }
        const descriptor = snapshot.presentationRegistry[identifier]
        if (!descriptor) { readiness = "error"; lastError = "Presentazione non registrata: " + identifier; return }
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
            property PresentationContext presentationContext: PresentationContext {
                contentId: host.contentId; controller: host.controller
                style: candidate.useLiveStyle ? host.style : candidate.stagedStyle
                active: false; interactive: false
            }
            active: false; asynchronous: true
            visible: host.currentLoader === candidate
            width: host.width; height: host.height
            onLoaded: {
                if (requestGeneration !== host.generation || !host.active) { destroy(); return }
                if (serviceGeneration) host.service.acceptCandidate(serviceGeneration,true,"")
                else host.commit(candidate)
            }
            onStatusChanged: if (status === Loader.Error && requestGeneration === host.generation) {
                const message = "Errore caricamento " + presentationId
                host.lastError = message
                host.readiness = host.currentItem ? "ready" : "error"
                host.pendingLoader = null
                const failedGeneration = serviceGeneration
                destroy()
                if (failedGeneration) host.service.acceptCandidate(failedGeneration,false,message)
                else if (!host.currentItem && host.service) host.service.recoverVisual(host.contentId,message)
            }
        }
    }
}
