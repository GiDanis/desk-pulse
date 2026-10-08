import QtQuick
import "../themes"
Item {
    id: root
    property var traceRecorder: null
    property string traceOwner: ""
    property string traceEventId: ""
    readonly property bool running: !!currentRecipe && currentRecipe.running === true
    readonly property bool runningKnown: !currentRecipe || currentRecipe.running !== undefined
    // Query the recipe directly while signal handlers are still propagating.
    // Host derived bindings may retain the previous value during runningChanged.
    function traceRunningNow() { return !!currentRecipe && currentRecipe.running !== false }
    function traceMotion(name) { if (traceRecorder) { traceRecorder.invalidate(name); traceRecorder.traceEvent(name,{instanceId:traceOwner,motionEvent:traceEventId,revision:playingRevision,running:running}) } }
    // Observe the resolved controller property: a child's signal can precede
    // evaluation of this binding and expose the previous running value.
    onRunningChanged: if (traceRecorder) traceMotion(running ? "motion.started" : "motion.stopped")
    property var appearance: Theme.appearance
    property var currentRecipe: null
    property var resourceService: Theme.service
    property string resourceLease: ""
    property string lastError: ""
    property int playingRevision: -1
    visible: false
    function settle() { if (resourceLease && resourceService) { resourceService.releaseRevision(resourceLease); resourceLease="" }
        if (traceRecorder && currentRecipe) traceMotion("motion.settle"); if (currentRecipe) { currentRecipe.settle(); currentRecipe.destroy(); currentRecipe = null } }
    function play(target, eventId, direction, vertical, context) {
        settle()
        traceEventId = eventId
        playingRevision = appearance ? appearance.revision : -1
        if (traceRecorder) traceMotion("motion.play")
        if (!appearance || appearance.motionMode === "off") { if (traceRecorder) traceMotion("motion.off"); return }
        const spec = appearance.motion[eventId]
        if (!spec) { if (traceRecorder) traceMotion("motion.missingSpec"); return }
        if (spec.recipe === "builtin.cut") { if (traceRecorder) traceMotion("motion.cut"); return }
        const registry = appearance.motionRegistry[spec.recipe]
        if (!registry) { if (traceRecorder) traceMotion("motion.missingRecipe"); return }
        if (resourceService && registry.rendererIdentity) resourceLease=resourceService.acquireRevision(registry.rendererIdentity)
        if (registry.rendererIdentity && resourceService && !resourceLease) { lastError="Risorsa animazione non disponibile"; return }
        const component = Qt.createComponent(registry.sourceUrl || Qt.resolvedUrl("../" + registry.file))
        if (component.status !== Component.Ready) { settle(); lastError = component.errorString(); if (traceRecorder) traceMotion("motion.recipeError"); return }
        currentRecipe = component.createObject(root)
        if (!currentRecipe) { if (resourceLease && resourceService) { resourceService.releaseRevision(resourceLease); resourceLease="" }; lastError = component.errorString(); if (traceRecorder) traceMotion("motion.recipeError"); return }
        const curves = {linear: Easing.Linear, outCubic: Easing.OutCubic, outQuad: Easing.OutQuad, inOutQuad: Easing.InOutQuad}
        currentRecipe.play(target, Object.assign({},spec,context || {},{motionMode: appearance.motionMode, duration: appearance.motionMode === "reduced" ? Math.min(spec.durationMs,80) : spec.durationMs,
                           distance: appearance.motionMode === "reduced" ? Math.min(spec.distancePx,4) : spec.distancePx,
                           easing: curves[spec.easing], exit: eventId.endsWith(".exit"), opacityFrom: spec.opacityFrom === undefined ? 0.35 : spec.opacityFrom}), direction || 1, vertical || false)
    }
    // A commit can start the new revision's tween during signal propagation.
    // Settle an older tween without cancelling the one just started by that commit.
    onAppearanceChanged: if (!appearance || playingRevision !== appearance.revision) settle()
    Component.onDestruction: settle()
}
