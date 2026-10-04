import QtQuick
import "../themes"
Item {
    id: root
    default property alias content: body.data
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
        target: root.traceRecorder ? body : null
        function onXChanged() { root.traceRecorder.invalidate("render.x") }
        function onYChanged() { root.traceRecorder.invalidate("render.y") }
        function onWidthChanged() { root.traceRecorder.invalidate("render.width") }
        function onHeightChanged() { root.traceRecorder.invalidate("render.height") }
        function onVisibleChanged() { root.traceRecorder.invalidate("render.visible") }
        function onOpacityChanged() { root.traceRecorder.invalidate("render.opacity") }
    }
    property var traceRecorder: null
    property string traceSurfaceId: ""
    property string traceInstanceId: ""
    property string traceRetainedSurface: ""
    readonly property bool traceMotionRunning: controller.running
    function traceIdentity() { if (traceRecorder && !traceInstanceId) traceInstanceId = traceRecorder.allocateInstance(traceSurfaceId,"legacyInline"); return traceInstanceId }
    function traceEvent(name) { if (traceRecorder) { traceRecorder.invalidate(name); traceRecorder.traceEvent(name,{instanceId:traceIdentity(),surfaceId:traceSurfaceId,active:active,exiting:exiting,revision:layerStyle.appearance.revision}) } }
    function traceParticipant(app) {
        const presence = app.themeTracePresence(root,body)
        return {instanceId:traceIdentity(),surfaceId:active ? traceSurfaceId : traceRetainedSurface,revision:layerStyle.appearance.revision,
            observedRevision:body.style.appearance.revision,exposed:presence.exposed,mandatory:active,
            committed:true,ready:true,geometryValid:presence.geometryValid,opacity:presence.opacity,visualGeometry:presence.visualGeometry,
            rendererIdentity:"legacyInline",motionRunning:controller.traceRunningNow(),retainedExit:exiting,actionsEnabled:enabled}
    }
    property bool active: false
    property bool preempted: false
    property bool exitAllowed: true
    property var appearance: Theme.appearance
    property var frozenAppearance: null
    readonly property StyleFacade layerStyle: StyleFacade { appearance: root.active ? root.appearance : root.frozenAppearance || root.appearance }
    Component.onCompleted: frozenAppearance = appearance
    property string eventPrefix: "panel"
    property bool exiting: false
    visible: active || exiting
    enabled: active && !preempted
    onActiveChanged: {
        if (traceRecorder && active) traceRetainedSurface = traceSurfaceId
        if (traceRecorder) traceEvent("overlay.active")
        completion.stop()
        if (!active) frozenAppearance = appearance
        if (active) { exiting = false; controller.play(body,eventPrefix+".enter",1,false) }
        else if (exitAllowed && !preempted && appearance && appearance.motionMode !== "off") {
            exiting = true; controller.play(body,eventPrefix+".exit",1,false)
            completion.interval = appearance.motionMode === "reduced" ? 85 : (appearance.motion[eventPrefix+".exit"] || {durationMs:0}).durationMs+5
            completion.start()
        } else { exiting = false; controller.settle() }
    }
    onPreemptedChanged: if (preempted) { completion.stop(); exiting = false; controller.settle() }
    onAppearanceChanged: { completion.stop(); exiting = false; controller.settle() }
    Item { id: body; readonly property StyleFacade style: root.layerStyle; anchors.fill: parent }
    MotionController { id: controller; appearance: root.appearance; traceRecorder: root.traceRecorder; traceOwner: root.traceInstanceId }
    Timer { id: completion; onTriggered: { root.exiting = false; controller.settle() } }
}
