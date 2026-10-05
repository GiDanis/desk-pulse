import QtQuick

// Only public pages negotiate their viewport. Legacy fallbacks retain their
// original geometry; the parent still supplies the existing navigation motion.
ViewHost {
    readonly property rect pageArea: controller.pageGeometry(contentId)
    x: pageArea.x
    y: pageArea.y - 90
    width: pageArea.width
    height: pageArea.height
    clip: controller.hasExternalSurface(contentId)
}
