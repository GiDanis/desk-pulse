import QtQuick
import "../themes"
Item {
    id: root
    Connections {
        target: root.traceRecorder ? root : null
        function onXChanged() { root.traceRecorder.invalidate("host.x") }
        function onYChanged() { root.traceRecorder.invalidate("host.y") }
        function onWidthChanged() { root.traceRecorder.invalidate("host.width") }
        function onHeightChanged() { root.traceRecorder.invalidate("host.height") }
        function onVisibleChanged() { root.traceRecorder.invalidate("host.visible") }
        function onOpacityChanged() { root.traceRecorder.invalidate("host.opacity") }
    }
    Connections {
        target: root.traceRecorder ? actor : null
        function onXChanged() { root.traceRecorder.invalidate("render.x") }
        function onYChanged() { root.traceRecorder.invalidate("render.y") }
        function onWidthChanged() { root.traceRecorder.invalidate("render.width") }
        function onHeightChanged() { root.traceRecorder.invalidate("render.height") }
        function onVisibleChanged() { root.traceRecorder.invalidate("render.visible") }
        function onOpacityChanged() { root.traceRecorder.invalidate("render.opacity") }
    }
    property var traceRecorder: null
    property var controller: null
    readonly property bool publicRenderer: descriptor && descriptor.apiVersion === 2
    readonly property bool currentReady: publicRenderer ? publicScene.currentReady : sceneLoader.status === Loader.Ready
    property string lastError: ""
    readonly property string readiness: publicRenderer ? publicScene.readiness : sceneLoader.status === Loader.Ready ? "ready" : sceneLoader.status === Loader.Error ? "error" : sceneLoader.status === Loader.Loading ? "loading" : "idle"
    property string traceInstanceId: ""
    property string traceLoadedRenderer: ""
    readonly property bool traceMotionRunning: (movement.running || !movement.runningKnown)
    function traceIdentity() { if (traceRecorder && !traceInstanceId) traceInstanceId = traceRecorder.allocateInstance("scene.main","live"); return traceInstanceId }
    function traceEvent(name) { if (traceRecorder) { traceRecorder.invalidate(name); traceRecorder.traceEvent(name,{instanceId:traceIdentity(),surfaceId:"scene.main",revision:appearance.revision,rendererIdentity:traceLoadedRenderer,actorId:actorState.actorId,actorSequence:actorState.sequence,loadingStatus:sceneLoader.status}) } }
    function traceParticipant(app) {
        const presence = app.themeTracePresence(root,actor)
        const loaded = publicRenderer ? publicScene.readiness === "ready" && !!publicScene.currentItem : sceneLoader.status === Loader.Ready && !!sceneLoader.item
        if (publicRenderer) return publicScene.traceParticipant(sceneEnabled && visible)
        return {instanceId:traceIdentity(),surfaceId:"scene.main",revision:appearance.revision,
            observedRevision:loaded && sceneLoader.item.style ? sceneLoader.item.style.appearance.revision : -1,
            exposed:presence.exposed,mandatory:sceneEnabled && visible,committed:loaded && traceLoadedRenderer === appearance.scene.renderer,committedRevision:appearance.revision,ready:loaded,
            frontCommitted:loaded && traceLoadedRenderer === appearance.scene.renderer,frontCommittedRevision:loaded && sceneLoader.item.style ? sceneLoader.item.style.appearance.revision : -1,frontReady:loaded,frontRendererIdentity:traceLoadedRenderer,frontExpectedRendererIdentity:appearance.scene.renderer,
            geometryValid:presence.geometryValid,opacity:presence.opacity,visualGeometry:presence.visualGeometry,rendererIdentity:traceLoadedRenderer,
            actorId:actorState.actorId,actorSequence:actorState.sequence,motionRunning:movement.traceRunningNow(),
            retainedExit:false,actionsEnabled:false}
    }
    property StyleFacade style: Theme
    property var appearance: Theme.appearance
    property string familyId: "oggi"
    property bool suspended: false
    property var occupiedRegions: []
    property bool enforceSafeRegions: false
    property var safeRegions: []
    property var notificationEvent: ({})
    readonly property var descriptor: appearance ? appearance.sceneRegistry[appearance.scene.renderer] : ({})
    readonly property bool canvasScene: descriptor && (descriptor.sceneMode === "canvas" || descriptor.sceneMode === "background" || descriptor.sceneMode === "decoration")
    readonly property int actorWidth: descriptor && descriptor.footprint ? descriptor.footprint.width : 30
    readonly property int actorHeight: descriptor && descriptor.footprint ? descriptor.footprint.height : 30
    readonly property point nominalAnchor: Qt.point(familyId === "oggi" ? width - actorWidth - 10 : 12, height - 115)
    function intersects(point) { return occupiedRegions.some(region => point.x < region.x+region.width && point.x+actorWidth > region.x && point.y < region.y+region.height && point.y+actorHeight > region.y) }
    readonly property point alternateAnchor: Qt.point(familyId === "oggi" ? 12 : width-actorWidth-10,height-115)
    readonly property var candidateAnchors: {
        if (!enforceSafeRegions) return [nominalAnchor,alternateAnchor]
        const preferred = familyId === "oggi" ? safeRegions.slice().reverse() : safeRegions
        return preferred.filter(region => region.width >= actorWidth && region.height >= actorHeight).map(region =>
            Qt.point(Math.max(region.x,Math.min(nominalAnchor.x,region.x+region.width-actorWidth)),
                     Math.max(region.y,Math.min(nominalAnchor.y,region.y+region.height-actorHeight))))
    }
    readonly property point desiredAnchor: candidateAnchors.find(point => !intersects(point)) || candidateAnchors[0] || Qt.point(0,0)
    readonly property rect actorSafeArea: {
        if (!enforceSafeRegions || canvasScene) return Qt.rect(0,0,width,height)
        const area = safeRegions.find(region => desiredAnchor.x >= region.x && desiredAnchor.y >= region.y
            && desiredAnchor.x+actorWidth <= region.x+region.width && desiredAnchor.y+actorHeight <= region.y+region.height)
        return area ? Qt.rect(area.x,area.y,area.width,area.height) : Qt.rect(0,0,0,0)
    }
    readonly property bool regionBlocked: !canvasScene && (!candidateAnchors.length || intersects(desiredAnchor)) || canvasScene && occupiedRegions.length > 0 && !descriptor.respectsOccupiedRegions
    readonly property QtObject actorState: ActorState {
        paused: root.suspended || root.regionBlocked || !root.sceneEnabled || root.appearance.motionMode !== "normal"
        anchor: root.desiredAnchor
        motionMode: root.appearance ? root.appearance.motionMode : "off"
    }
    readonly property bool sceneEnabled: appearance && appearance.scene.enabled
    visible: sceneEnabled && !suspended && !regionBlocked
    objectName: "sceneHost"
    anchors.fill: parent
    // The default actor travels in the clear strip below the content; a registered
    // canvas renderer owns the full viewport and receives the same persistent state.
    function sceneFailure(message) {
        lastError=message
        if (controller && controller.themeService) controller.themeService.recoverScene(message)
    }
    function relocate() {
        movement.settle()
        const previous = Qt.point(actor.x,actor.y)
        actor.x = canvasScene ? 0 : desiredAnchor.x
        actor.y = canvasScene ? 0 : desiredAnchor.y
        actorState.sequence += 1
        if (!actorState.paused && !canvasScene) {
            actorState.locomotion = "moving"
            movement.play(actor,"scene.relocate",1,false,{anchor: desiredAnchor, previousAnchor: previous})
            poseCompletion.interval = (appearance.motion["scene.relocate"] || {durationMs:0}).durationMs + 10
            poseCompletion.restart()
        } else if (actorState.locomotion === "moving") actorState.locomotion = "idle"
    }
    onDesiredAnchorChanged: relocate()
    onRegionBlockedChanged: if (regionBlocked) {
        movement.settle(); poseCompletion.stop()
        if (actorState.locomotion === "moving") actorState.locomotion = "idle"
    }
    onSuspendedChanged: if (suspended) { movement.settle(); poseCompletion.stop(); if (actorState.locomotion === "moving") actorState.locomotion = "idle" }
    onAppearanceChanged: {
        movement.settle()
        if (!sceneEnabled || appearance.motionMode !== "normal") { poseCompletion.stop(); if (actorState.locomotion === "moving") actorState.locomotion = "idle" }
    }
    onCanvasSceneChanged: relocate()
    Component.onCompleted: { actor.x = canvasScene ? 0 : desiredAnchor.x; actor.y = canvasScene ? 0 : desiredAnchor.y }
    Timer { id: poseCompletion; onTriggered: if (root.actorState.locomotion === "moving") root.actorState.locomotion = "idle" }
    MotionController { id: movement; appearance: root.appearance; traceRecorder: root.traceRecorder; traceOwner: root.traceInstanceId }
    Item {
        id: actor
        clip: root.enforceSafeRegions || root.canvasScene
        width: root.canvasScene ? root.width : root.actorWidth
        height: root.canvasScene ? root.height : root.actorHeight
        ViewHost {
            id: publicScene
            contentId: "scene.main"; controller: root.controller; style: root.style
            anchors.fill: parent; active: root.sceneEnabled && root.publicRenderer || root.controller && root.controller.hasCandidateSurface("scene.main") && root.controller.themeCandidate.scene.enabled; renderActive: root.visible
            interactive: false; animateSwap: false
            contextFactory: Component {
                QtObject {
                    property var controller: root.controller
                    property string contentId: "scene.main"
                    property var style: root.style
                    property bool active: false
                    property bool interactive: false
                    property int viewportWidth: root.width
                    property int viewportHeight: root.height
                    property rect safeArea: root.actorSafeArea
                    property var actorState: root.actorState
                    property var occupiedRegions: root.occupiedRegions
                    property var notificationEvent: root.notificationEvent
                    property var configuration: root.appearance.scene
                    property bool suspended: root.suspended || root.regionBlocked
                }
            }
        }
        Timer { interval: 2500; running: sceneLoader.status === Loader.Loading; onTriggered: root.sceneFailure("Timeout caricamento scena") }
        Loader {
            id: sceneLoader
            onStatusChanged: {
                if (root.traceRecorder) root.traceEvent(status === Loader.Error ? "scene.loader.error" : "scene.loader.status")
                if (status === Loader.Error) root.sceneFailure("Renderer scena non caricabile")
            }
            anchors.fill: parent
            active: root.sceneEnabled && !root.publicRenderer; asynchronous: true
            source: root.sceneEnabled && !root.publicRenderer ? root.descriptor.sourceUrl || Qt.resolvedUrl("../"+root.descriptor.file) : ""
            onLoaded: {
                root.traceLoadedRenderer = root.appearance.scene.renderer
                if (root.traceRecorder) root.traceEvent("scene.loader.ready")
                item.active = Qt.binding(function() { return root.visible && !root.suspended })
                item.style = Qt.binding(function() { return root.style }); item.actorState = root.actorState
                item.configuration = Qt.binding(function() { return root.appearance.scene })
                if (item.occupiedRegions !== undefined) item.occupiedRegions = Qt.binding(function() { return root.occupiedRegions })
                if (item.notificationEvent !== undefined) item.notificationEvent = Qt.binding(function() { return root.notificationEvent })
            }
        }
    }
}
