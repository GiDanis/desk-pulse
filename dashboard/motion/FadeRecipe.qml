import QtQuick
QtObject {
    id: recipe
    property var target: null
    property int duration: 100
    property int curve: Easing.OutCubic
    property real endOpacity: 1
    property NumberAnimation animation: NumberAnimation { target: recipe.target; property: "opacity"; to: recipe.endOpacity; duration: recipe.duration; easing.type: recipe.curve }
    function play(item, configuration, direction, vertical) { target = item; duration = configuration.duration; curve = configuration.easing; endOpacity = configuration.exit ? 0 : 1; item.opacity = configuration.exit ? 1 : configuration.opacityFrom; animation.start() }
    function settle() { animation.stop(); if (target) target.opacity = 1; target = null }
}
