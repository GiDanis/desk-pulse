import QtQuick
QtObject {
    id: recipe
    readonly property bool running: animation.running
    property var target: null
    property string targetProperty: "opacity"
    property real destination: 1
    property int duration: 160
    property int curve: Easing.OutCubic
    property NumberAnimation animation: NumberAnimation {
        target: recipe.target; property: recipe.targetProperty; to: recipe.destination
        duration: recipe.duration; easing.type: recipe.curve
    }
    function play(item, configuration, direction, vertical) {
        target = item; targetProperty = configuration.propertyName
        destination = configuration.valueTo; duration = configuration.duration; curve = configuration.easing
        item[targetProperty] = configuration.valueFrom
        animation.start()
    }
    function settle() { animation.stop(); if (target) target[targetProperty] = destination; target = null }
}
