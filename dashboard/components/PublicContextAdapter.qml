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
    readonly property var payload: {
        if (!publicEnabled) return ({})
        const c = legacy
        if (!c) return ({})
        const result = {active:c.active,interactive:c.interactive,style:c.style,
            viewportWidth:c.viewportWidth,viewportHeight:c.viewportHeight,
            appearanceRevision:c.style && c.style.appearance ? c.style.appearance.revision : 0,
            motionMode:c.style && c.style.appearance ? c.style.appearance.motionMode : "off"}
        const keys = ["visualStyle","mode","actions","safeArea","iconId","model","selection","clockText","dateText","event","items","selectedEventId","unreadCount",
            "sourceStatus","scrollOffset","scrollMaximum","occupiedRegions","preview","exiting","ready","error",
            "commandHints","guideText","sourceText","validityText","actorState","notificationEvent","configuration","suspended"]
        for (const key of keys) if (c[key] !== undefined) result[key] = c[key]
        if (c.controller) {
            const app = c.controller
            result.epoch = app.now.getTime()/1000
            result.familyId = app.familyId
            result.route = app.overlay
            result.urgent = !!app.urgentEvent.id
            result.suspended = c.active === false || !!app.urgentEvent.id && surfaceId !== "alerts.urgent"
            if (typeof app.publicSurfacePayload === "function") Object.assign(result,app.publicSurfacePayload(surfaceId))
        }
        if (c.actorState) {
            const actor=c.actorState
            result.actor={actorId:actor.actorId,pose:actor.pose,locomotion:actor.locomotion,sequence:actor.sequence,
                paused:actor.paused,anchor:{x:actor.anchor.x,y:actor.anchor.y},motionMode:actor.motionMode}
        }
        return result
    }
    function refresh() { if (factory && publicContext) valid=factory.updateLegacy(publicContext,payload) }
    onPayloadChanged: refresh()
    function initialize() {
        if (!factory || !publicEnabled || publicContext) return
        publicContext = factory.create(surfaceId,adapter)
        refresh()
    }
    onPublicEnabledChanged: initialize()
    Component.onCompleted: initialize()
    Component.onDestruction: if (factory && publicContext) factory.release(publicContext)
}
