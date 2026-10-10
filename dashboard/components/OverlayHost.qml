import QtQuick
ViewHost {
    readonly property rect panelArea: controller.overlayGeometry(contentId)
    x: panelArea.x; y: panelArea.y; width: panelArea.width; height: panelArea.height
    animateSwap: false
    cacheLimit: 6
    property string presentedRendererKey: ""
    function publishDestination() {
        if (active && currentReady && readiness === "ready" && currentSurfaceId === contentId && typeof controller.presentOverlay === "function")
            Qt.callLater(function() {
                if (!active || !renderActive || !currentReady || currentSurfaceId !== contentId) return
                controller.presentOverlay()
                if (presentedRendererKey !== loadedRendererKey) {
                    presentedRendererKey = loadedRendererKey
                    animateEntrance()
                }
            })
    }
    onRenderActiveChanged: { if (!renderActive) presentedRendererKey = ""; else publishDestination() }
    onCurrentReadyChanged: publishDestination()
    onReadinessChanged: publishDestination()
}
