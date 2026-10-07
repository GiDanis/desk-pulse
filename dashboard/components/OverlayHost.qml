import QtQuick
ViewHost {
    readonly property rect panelArea: controller.overlayGeometry(contentId)
    x: panelArea.x; y: panelArea.y; width: panelArea.width; height: panelArea.height
    animateSwap: false
    cacheLimit: 6
    function publishDestination() {
        if (active && currentReady && readiness === "ready" && typeof controller.presentOverlay === "function")
            Qt.callLater(function() { controller.presentOverlay() })
    }
    onCurrentReadyChanged: publishDestination()
    onReadinessChanged: publishDestination()
}
