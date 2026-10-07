pragma ComponentBehavior: Bound
import QtQuick

Item {
    id: root
    property int count: 0
    property int currentPosition: 1
    property bool vertical: false
    property string groupId: ""
    property bool resettingGroup: false
    property var themeStyle: null
    property var motionPolicy: null
    readonly property int selectedIndex: Math.max(0, Math.min(count - 1, currentPosition - 1))
    readonly property real targetPosition: selectedIndex * 20
    readonly property int duration: !motionPolicy || motionPolicy.suspended || motionPolicy.urgent || motionPolicy.mode === "off" ? 0 : motionPolicy.mode === "reduced" ? 80 : 140
    property real position: targetPosition
    property bool initialized: false
    property bool settling: false
    readonly property bool animating: travel.running
    implicitWidth: vertical ? 10 : Math.max(10, (count - 1) * 20 + 10)
    implicitHeight: vertical ? Math.max(10, (count - 1) * 20 + 10) : 10
    visible: count > 0
    function settleMotion() {
        settling = true
        position = Qt.binding(function() { return root.targetPosition })
        settling = false
    }
    Component.onCompleted: { initialized = true; settleMotion() }
    onGroupIdChanged: {
        resettingGroup = true
        Qt.callLater(function() { settleMotion(); resettingGroup = false })
    }
    onDurationChanged: if (duration === 0) settleMotion()
    Behavior on position {
        enabled: root.initialized && !root.resettingGroup && !root.settling && root.duration > 0
        NumberAnimation { id: travel; duration: root.duration; easing.type: Easing.OutCubic }
    }
    Repeater {
        model: Math.max(0, root.count)
        delegate: Rectangle {
            required property int index
            x: root.vertical ? 2 : index * 20 + 2
            y: root.vertical ? index * 20 + 2 : 2
            width: 6; height: 6; radius: 3
            color: root.themeStyle ? root.themeStyle.textSecondary : "#5D626C"
            opacity: 0.4
        }
    }
    Rectangle {
        x: root.vertical ? 0 : root.position
        y: root.vertical ? root.position : 0
        width: 10; height: 10; radius: 5
        color: root.themeStyle ? root.themeStyle.semantic.accentDecoration : "#0066CC"
    }
}
