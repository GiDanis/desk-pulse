import QtQuick
import "../themes"
import "../themes/FallbackAppearance.js" as Fallback
import "../presentations/notifications"

ViewHost {
    id: host
    // Only the selected renderer for each surface is prepared, never every theme.
    active: true
    property bool show: false
    property bool preempted: false
    property bool exitAllowed: true
    property bool preview: false
    traceRole: preview ? "preview" : "live"
    readonly property bool notificationMotionRunning: motion.running
    function notificationMotionRunningNow() { return motion.traceRunningNow() }
    readonly property bool urgentFallbackActive: urgentFallback.active
    property var eventSource: ({})
    property var previewItems: []
    property int previewUnreadCount: 1
    property var renderedEvent: ({})
    property var frozenAppearance: null
    readonly property string mode: contentId.split(".").pop()
    readonly property NotificationStyle metrics: NotificationStyle { appearance: host.style.appearance; mode: host.mode }
    style: StyleFacade { appearance: host.exiting ? host.frozenAppearance : host.appearance }
    renderActive: show
    interactive: show && !preempted && !preview
    // This host owns enter/exit: two controllers must not animate the same Loader.
    animateSwap: false
    property int enteredRevision: -1
    x: metrics.insetX
    y: metrics.anchor === "top" ? metrics.insetY : metrics.anchor === "bottom" ? 640-height-metrics.insetY : (640-height)/2+metrics.insetY
    width: metrics.panelWidth
    height: Math.min(640-(metrics.anchor === "center" ? 2*Math.abs(metrics.insetY) : metrics.insetY),Math.max(metrics.panelHeight,currentItem ? currentItem.implicitHeight : 0))
    contextFactory: Component {
        NotificationContext {
            contentId: host.contentId
            viewportWidth: host.width; viewportHeight: host.height
            sourceEvent: host.renderedEvent; preview: host.preview; exiting: host.exiting
            sourceItems: host.preview ? host.previewItems : host.show ? host.controller.alertItems : []
            selectedEventId: host.preview ? "preview" : host.controller.alertFocusedId
            unreadCount: host.preview ? host.previewUnreadCount : host.controller.unreadAlertCount
            sourceStatus: host.preview ? "Demo · nessuna fonte esterna" : host.controller.events.sourceStatus || "in attesa"
            scrollOffset: host.preview ? 0 : host.controller.alertScroll
            actionHandler: function(action, identifier, argument) { return host.controller.notificationAction(host.mode,action,identifier,argument) }
            occupiedRegions: host.currentItem && host.currentItem.occupiedRegions ?
                host.currentItem.occupiedRegions.map(region => Qt.rect(host.x+region.x,host.y+region.y,region.width,region.height)) : [Qt.rect(host.x,host.y,host.width,host.height)]
        }
    }
    function captureEvent() {
        if (!eventSource || !eventSource.id) return
        if ((mode === "small" || mode === "large") && (eventSource.bannerSize === "large" ? "large" : "small") !== mode) return
        renderedEvent = eventSource
    }
    function settleMotion() {
        if (traceRecorder) traceEvent("notification.settle",{mode:mode,eventId:renderedEvent.id || "",eventRevision:String(renderedEvent.revision || ""),rank:renderedEvent.notificationRank || 0})
        exitTimer.stop(); exiting = false; motion.settle()
        if (currentLoader) currentLoader.opacity = 1
        if (currentItem && typeof currentItem.settleMotion === "function") currentItem.settleMotion()
    }
    function enter() {
        if (traceRecorder && show) traceEvent("notification.enter",{mode:mode,eventId:renderedEvent.id || "",eventRevision:String(renderedEvent.revision || ""),rank:renderedEvent.notificationRank || 0})
        if (show && currentLoader && mode !== "urgent") {
            enteredRevision = appearance.revision
            const expected = currentLoader, revision = enteredRevision
            const spec = appearance.motion[motionPrefix+".enter"]
            if (appearance.motionMode !== "off" && spec && (spec.recipe === "builtin.fade" || spec.recipe === "builtin.slide"))
                expected.opacity = spec.opacityFrom === undefined ? 0.35 : spec.opacityFrom
            // Start after style bindings/settlement have completed for the commit.
            Qt.callLater(function() {
                if (show && currentLoader === expected && appearance.revision === revision)
                    motion.play(expected,motionPrefix+".enter",1,false)
                else if (currentLoader === expected) expected.opacity = 1
            })
        }
    }
    readonly property string motionPrefix: mode === "small" || mode === "large" ? "banner."+mode : "alerts."+mode
    onEventSourceChanged: captureEvent()
    onShowChanged: {
        exitTimer.stop()
        if (show) { exiting = false; enter() }
        else {
            frozenAppearance = appearance
            if (traceRecorder) traceEvent("notification.freeze",{mode:mode,frozenRevision:appearance.revision,eventId:renderedEvent.id || ""})
            if (currentLoader && exitAllowed && !preempted && mode !== "urgent" && appearance.motionMode !== "off") {
                exiting = true
                motion.play(currentLoader,motionPrefix+".exit",1,false)
                const recipe = appearance.motion[motionPrefix+".exit"] || {durationMs:0}
                exitTimer.interval = (appearance.motionMode === "reduced" ? Math.min(recipe.durationMs,80) : recipe.durationMs)+5
                exitTimer.start()
            } else settleMotion()
        }
    }
    onPreemptedChanged: if (preempted) settleMotion()
    onCurrentItemChanged: { motion.settle(); enter(); if (context) context.ready = true }
    // Public contexts stay read-only. An external detail renderer reports its
    // measured scroll extent on its root; the host owns the private input.
    Binding {
        target: host.context
        property: "scrollMaximum"
        when: !!host.context && !!host.currentItem && typeof host.currentItem.scrollMaximum === "number"
        value: host.currentItem ? Math.max(0,host.currentItem.scrollMaximum || 0) : 0
        restoreMode: Binding.RestoreBindingOrValue
    }
    Connections {
        target: host
        function onAppearanceChanged() { if (host.enteredRevision !== host.appearance.revision) host.settleMotion() }
    }
    Connections {
        target: host.context
        function onSettleMotionRequested() { host.settleMotion() }
    }
    Component.onCompleted: captureEvent()
    MotionController { id: motion; appearance: host.appearance; traceRecorder: host.traceRecorder; traceOwner: host.traceInstanceId }
    Timer { id: exitTimer; onTriggered: host.settleMotion() }
    // Emergency urgent is compiled with the application and never waits for a theme Loader.
    Loader {
        id: urgentFallback
        objectName: "urgentFallback"
        onActiveChanged: if (host.traceRecorder) host.traceEvent("notification.fallback",{fallbackActive:active,mode:host.mode,eventId:host.eventSource.id || ""})
        active: host.mode === "urgent" && host.show && !host.currentReady
        x: -host.x; y: -host.y; width: 960; height: 640; asynchronous: false
        sourceComponent: Component {
            UrgentVisual {
                context: NotificationContext {
                    contentId: "alerts.urgent"; sourceEvent: host.eventSource
                    style: StyleFacade { appearance: Fallback.base }
                    active: true; interactive: !host.preview; preview: host.preview
                    actionHandler: function(action, identifier, argument) { return host.controller.notificationAction("urgent",action,identifier,argument) }
                }
            }
        }
    }
}
