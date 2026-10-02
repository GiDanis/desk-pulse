import QtQuick
QtObject {
    id: recipe
    property var target: null
    property string axis: "x"
    property real origin: 0
    property real distance: 20
    property int duration: 160
    property int curve: Easing.OutCubic
    property NumberAnimation animation: NumberAnimation {
        target: recipe.target; property: recipe.axis; to: recipe.origin
        duration: recipe.duration; easing.type: recipe.curve
    }
    function play(item, configuration, direction, vertical) {
        target = item; axis = vertical ? "y" : "x"; origin = item[axis]
        distance = configuration.distance * direction; duration = configuration.duration
        curve = configuration.easing; item[axis] = origin + distance; animation.start()
    }
    function settle() { animation.stop(); if (target) target[axis] = origin; target = null }
}
