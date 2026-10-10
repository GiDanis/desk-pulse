import QtQuick

// Built-in dashboards use the shared compact viewport. External pages negotiate
// their own area; external legacy fallbacks retain the calibrated viewport.
ViewHost {
    readonly property rect pageArea: controller.pageGeometry(contentId)
    x: pageArea.x
    y: pageArea.y - 90
    width: pageArea.width
    height: pageArea.height
    clip: controller.hasExternalSurface(contentId) || controller.builtinDashboardLayout
    renderActive: active || controller.presentedPageContentId === contentId
    function publishDestination() {
        if (active && currentReady && readiness === "ready" && typeof controller.presentPage === "function")
            Qt.callLater(function() { controller.presentPage(hostPage) })
    }
    id: hostPage
    onCurrentReadyChanged: publishDestination()
    onReadinessChanged: publishDestination()
    onLoadedRevisionChanged: publishDestination()
}
