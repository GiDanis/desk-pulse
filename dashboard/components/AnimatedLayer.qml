import QtQuick
import "../themes"
Item {
    id: root
    default property alias content: body.data
    property bool active: false
    property bool preempted: false
    property bool exitAllowed: true
    property var appearance: Theme.appearance
    property var frozenAppearance: null
    readonly property StyleFacade layerStyle: StyleFacade { appearance: root.active ? root.appearance : root.frozenAppearance || root.appearance }
    Component.onCompleted: frozenAppearance = appearance
    property string eventPrefix: "panel"
    property bool exiting: false
    visible: active || exiting
    enabled: active && !preempted
    onActiveChanged: {
        completion.stop()
        if (!active) frozenAppearance = appearance
        if (active) { exiting = false; controller.play(body,eventPrefix+".enter",1,false) }
        else if (exitAllowed && !preempted && appearance && appearance.motionMode !== "off") {
            exiting = true; controller.play(body,eventPrefix+".exit",1,false)
            completion.interval = appearance.motionMode === "reduced" ? 85 : (appearance.motion[eventPrefix+".exit"] || {durationMs:0}).durationMs+5
            completion.start()
        } else { exiting = false; controller.settle() }
    }
    onPreemptedChanged: if (preempted) { completion.stop(); exiting = false; controller.settle() }
    onAppearanceChanged: { completion.stop(); exiting = false; controller.settle() }
    Item { id: body; readonly property StyleFacade style: root.layerStyle; anchors.fill: parent }
    MotionController { id: controller; appearance: root.appearance }
    Timer { id: completion; onTriggered: { root.exiting = false; controller.settle() } }
}
