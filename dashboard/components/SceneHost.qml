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
    property string traceInstanceId: ""
    property string traceLoadedRenderer: ""
    readonly property bool traceMotionRunning: (movement.running || !movement.runningKnown)
    function traceIdentity() { if (traceRecorder && !traceInstanceId) traceInstanceId = traceRecorder.allocateInstance("scene.main","live"); return traceInstanceId }
    function traceEvent(name) { if (traceRecorder) { traceRecorder.invalidate(name); traceRecorder.traceEvent(name,{instanceId:traceIdentity(),surfaceId:"scene.main",revision:appearance.revision,rendererIdentity:traceLoadedRenderer,actorId:actorState.actorId,actorSequence:actorState.sequence,loadingStatus:sceneLoader.status}) } }
    function traceParticipant(app) {
        const presence = app.themeTracePresence(root,actor)
        const loaded = sceneLoader.status === Loader.Ready && !!sceneLoader.item
        return {instanceId:traceIdentity(),surfaceId:"scene.main",revision:appearance.revision,
            observedRevision:loaded && sceneLoader.item.style ? sceneLoader.item.style.appearance.revision : -1,
            exposed:presence.exposed,mandatory:sceneEnabled && visible,committed:loaded && traceLoadedRenderer === appearance.scene.renderer,committedRevision:appearance.revision,ready:loaded,
            geometryValid:presence.geometryValid,opacity:presence.opacity,rendererIdentity:traceLoadedRenderer,
            actorId:actorState.actorId,actorSequence:actorState.sequence,motionRunning:traceMotionRunning,
            retainedExit:false,actionsEnabled:false}
    }
    property StyleFacade style: Theme
    property var appearance: Theme.appearance
    property string familyId: "oggi"
    property bool suspended: false
    property var occupiedRegions: []
    property var notificationEvent: ({})
    readonly property var descriptor: appearance ? appearance.sceneRegistry[appearance.scene.renderer] : ({})
    readonly property bool canvasScene: descriptor && descriptor.sceneMode === "canvas"
    readonly property int actorWidth: descriptor && descriptor.footprint ? descriptor.footprint.width : 30
    readonly property int actorHeight: descriptor && descriptor.footprint ? descriptor.footprint.height : 30
    readonly property point nominalAnchor: Qt.point(familyId === "oggi" ? width - actorWidth - 10 : 12, height - 115)
    function intersects(point) { return occupiedRegions.some(region => point.x < region.x+region.width && point.x+actorWidth > region.x && point.y < region.y+region.height && point.y+actorHeight > region.y) }
    readonly property point alternateAnchor: Qt.point(familyId === "oggi" ? 12 : width-actorWidth-10,height-115)
    readonly property point desiredAnchor: !intersects(nominalAnchor) ? nominalAnchor : !intersects(alternateAnchor) ? alternateAnchor : nominalAnchor
    readonly property bool regionBlocked: !canvasScene && intersects(desiredAnchor) || canvasScene && occupiedRegions.length > 0 && !descriptor.respectsOccupiedRegions
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
        width: root.canvasScene ? root.width : root.actorWidth
        height: root.canvasScene ? root.height : root.actorHeight
        Loader {
            id: sceneLoader
            onStatusChanged: if (root.traceRecorder) root.traceEvent(status === Loader.Error ? "scene.loader.error" : "scene.loader.status")
            anchors.fill: parent
            active: root.sceneEnabled; asynchronous: true
            source: root.sceneEnabled ? Qt.resolvedUrl("../"+root.descriptor.file) : ""
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
