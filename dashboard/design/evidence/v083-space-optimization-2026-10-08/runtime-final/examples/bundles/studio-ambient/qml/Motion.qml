import QtQuick

QtObject {
    id: root
    readonly property bool running: fade.running
    property var target: null
    property int duration: 0
    property real endOpacity: 1
    property NumberAnimation fade: NumberAnimation { target: root.target; property: "opacity"; to: root.endOpacity; duration: root.duration; easing.type: Easing.OutCubic }
    function play(item, configuration, direction, vertical) {
        settle()
        target = item
        endOpacity = configuration.exit ? 0 : 1
        duration = configuration.motionMode === "off" ? 0 : configuration.motionMode === "reduced" ? Math.min(configuration.duration, 80) : configuration.duration
        target.opacity = configuration.motionMode === "off" ? endOpacity : configuration.exit ? 1 : configuration.opacityFrom
        if (duration > 0) fade.start()
    }
    function settle() { fade.stop(); if (target) target.opacity = endOpacity; target = null }
    Component.onDestruction: settle()
}
