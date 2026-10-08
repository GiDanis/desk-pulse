import QtQuick
import SmartPC.ThemeApi 2.0

Item {
    id: root
    required property SceneContext context
    readonly property bool ready: true
    readonly property string error: ""
    function settleMotion() { breathe.stop(); companion.scale = 1 }
    Rectangle { id: companion; anchors.centerIn: parent; width: Math.min(26, parent.width); height: Math.min(26, parent.height); radius: width / 2; color: root.context.style.accent
        Rectangle { x: parent.width * 0.25; y: parent.height * 0.35; width: 3; height: 3; radius: 1.5; color: root.context.style.background }
        Rectangle { x: parent.width * 0.63; y: parent.height * 0.35; width: 3; height: 3; radius: 1.5; color: root.context.style.background }
    }
    SequentialAnimation { id: breathe; loops: Animation.Infinite; running: root.context.lifecycle.active && !root.context.suspended && !root.context.actor.paused && root.context.motionPolicy.mode === "normal"
        NumberAnimation { target: companion; property: "scale"; from: 1; to: 0.9; duration: 1200 }
        NumberAnimation { target: companion; property: "scale"; from: 0.9; to: 1; duration: 1200 }
    }
    Connections { target: root.context.lifecycle; function onActiveChanged() { if (!root.context.lifecycle.active) root.settleMotion() } }
    Connections { target: root.context.motionPolicy; function onModeChanged() { if (root.context.motionPolicy.mode !== "normal") root.settleMotion() } }
    Component.onDestruction: settleMotion()
}
