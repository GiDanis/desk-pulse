import QtQuick
import "../themes"
Item {
    id: root
    property var appearance: Theme.appearance
    property var currentRecipe: null
    property string lastError: ""
    property int playingRevision: -1
    visible: false
    function settle() { if (currentRecipe) { currentRecipe.settle(); currentRecipe.destroy(); currentRecipe = null } }
    function play(target, eventId, direction, vertical, context) {
        settle()
        playingRevision = appearance ? appearance.revision : -1
        if (!appearance || appearance.motionMode === "off") return
        const spec = appearance.motion[eventId]
        if (!spec) return
        const registry = appearance.motionRegistry[spec.recipe]
        if (!registry) return
        const component = Qt.createComponent(Qt.resolvedUrl("../" + registry.file))
        if (component.status !== Component.Ready) { lastError = component.errorString(); return }
        currentRecipe = component.createObject(root)
        if (!currentRecipe) { lastError = component.errorString(); return }
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
