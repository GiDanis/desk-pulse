import QtQuick
QtObject {
    id: recipe
    readonly property bool running: animation.running
    property var target: null
    property point destination: Qt.point(0,0)
    property int duration: 160
    property int curve: Easing.OutCubic
    property ParallelAnimation animation: ParallelAnimation {
        NumberAnimation { target: recipe.target; property: "x"; to: recipe.destination.x; duration: recipe.duration; easing.type: recipe.curve }
        NumberAnimation { target: recipe.target; property: "y"; to: recipe.destination.y; duration: recipe.duration; easing.type: recipe.curve }
    }
    function play(item, configuration, direction, vertical) {
        target = item; destination = configuration.anchor
        if (configuration.motionMode !== "normal") return
        duration = configuration.duration; curve = configuration.easing
        item.x = configuration.previousAnchor.x; item.y = configuration.previousAnchor.y
        animation.start()
    }
    function settle() { animation.stop(); if (target) { target.x = destination.x; target.y = destination.y }; target = null }
}
