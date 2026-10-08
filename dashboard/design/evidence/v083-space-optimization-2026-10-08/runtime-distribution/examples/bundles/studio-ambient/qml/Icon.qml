import QtQuick

Item {
    id: root
    property var style: null
    property string iconId: ""
    property var descriptor: ({})
    property string symbol: "unknown"
    property color tint: "#ffffff"
    property int opticalSize: 32
    property bool active: true
    readonly property bool ready: true
    function settleMotion() { }
    implicitWidth: opticalSize; implicitHeight: opticalSize
    Rectangle { anchors.centerIn: parent; width: parent.width * 0.6; height: width; radius: width / 2; color: "transparent"; border.width: 2; border.color: root.tint }
    Rectangle { x: parent.width * 0.47; y: parent.height * 0.2; width: 2; height: parent.height * 0.35; color: root.tint }
    Rectangle { x: parent.width * 0.47; y: parent.height * 0.7; width: 2; height: 2; color: root.tint }
}
