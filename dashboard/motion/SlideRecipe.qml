import QtQuick
QtObject {
    id: recipe
    property var target: null
    property string axis: "x"
    property real origin: 0
    property real distance: 20
    property int duration: 160
    property int curve: Easing.OutCubic
    property real destination: 0
    property real endOpacity: 1
    property ParallelAnimation animation: ParallelAnimation {
        NumberAnimation { target: recipe.target; property: recipe.axis; to: recipe.destination; duration: recipe.duration; easing.type: recipe.curve }
        NumberAnimation { target: recipe.target; property: "opacity"; to: recipe.endOpacity; duration: recipe.duration; easing.type: recipe.curve }
    }
    function play(item, configuration, direction, vertical) {
        target = item; axis = vertical ? "y" : "x"; origin = item[axis]
        distance = configuration.distance * direction; duration = configuration.duration
        curve = configuration.easing
        destination = configuration.exit ? origin + distance : origin
        endOpacity = configuration.exit ? 0 : 1
        item[axis] = configuration.exit ? origin : origin + distance
        item.opacity = configuration.exit ? 1 : configuration.opacityFrom
        animation.start()
    }
    function settle() { animation.stop(); if (target) { target[axis] = origin; target.opacity = 1 } target = null }
}
