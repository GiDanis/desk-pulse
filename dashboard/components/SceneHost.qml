import QtQuick
import "../themes"
Item {
    id: root
    property StyleFacade style: Theme
    property var appearance: Theme.appearance
    property string familyId: "oggi"
    property bool suspended: false
    readonly property var descriptor: appearance ? appearance.sceneRegistry[appearance.scene.renderer] : ({})
    readonly property bool canvasScene: descriptor && descriptor.sceneMode === "canvas"
    readonly property int actorWidth: descriptor && descriptor.footprint ? descriptor.footprint.width : 30
    readonly property int actorHeight: descriptor && descriptor.footprint ? descriptor.footprint.height : 30
    readonly property point desiredAnchor: Qt.point(familyId === "oggi" ? width - actorWidth - 10 : 12, height - 115)
    readonly property QtObject actorState: ActorState {
        paused: root.suspended || !root.sceneEnabled || root.appearance.motionMode !== "normal"
        anchor: root.desiredAnchor
        motionMode: root.appearance ? root.appearance.motionMode : "off"
    }
    readonly property bool sceneEnabled: appearance && appearance.scene.enabled
    visible: sceneEnabled && !suspended
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
    onFamilyIdChanged: relocate()
    onSuspendedChanged: if (suspended) { movement.settle(); poseCompletion.stop(); if (actorState.locomotion === "moving") actorState.locomotion = "idle" }
    onAppearanceChanged: {
        movement.settle()
        if (!sceneEnabled || appearance.motionMode !== "normal") { poseCompletion.stop(); if (actorState.locomotion === "moving") actorState.locomotion = "idle" }
    }
    onCanvasSceneChanged: relocate()
    Component.onCompleted: { actor.x = canvasScene ? 0 : desiredAnchor.x; actor.y = canvasScene ? 0 : desiredAnchor.y }
    Timer { id: poseCompletion; onTriggered: if (root.actorState.locomotion === "moving") root.actorState.locomotion = "idle" }
    MotionController { id: movement; appearance: root.appearance }
    Item {
        id: actor
        width: root.canvasScene ? root.width : root.actorWidth
        height: root.canvasScene ? root.height : root.actorHeight
        Loader {
            anchors.fill: parent
            active: root.sceneEnabled; asynchronous: true
            source: root.sceneEnabled ? Qt.resolvedUrl("../"+root.descriptor.file) : ""
            onLoaded: { item.active = Qt.binding(function() { return root.visible && !root.suspended }); item.style = Qt.binding(function() { return root.style }); item.actorState = root.actorState; item.configuration = Qt.binding(function() { return root.appearance.scene }) }
        }
    }
}
