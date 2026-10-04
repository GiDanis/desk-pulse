import QtQuick
Item {
    property var style
    property var actorState
    property var configuration
    property var occupiedRegions: []
    property var notificationEvent: ({})
    property bool active: false
    Rectangle { x: 44; y: 600; width: 18; height: 18; color: parent.style ? parent.style.accent : "#ffffff" }
}
