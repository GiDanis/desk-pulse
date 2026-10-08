import QtQuick
QtObject {
    property string actorId: "companion"
    property string pose: "idle"
    property string locomotion: "idle"
    property int sequence: 0
    property bool paused: true
    property string motionMode: "off"
    property point anchor: Qt.point(0,0)
}
