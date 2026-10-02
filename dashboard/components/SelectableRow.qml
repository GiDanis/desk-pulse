import QtQuick
import "../themes"
Surface {
    property bool selectedState: false
    property bool available: true
    color: selectedState ? style.surfaceFocused : style.surface
    radius: style.radiusRow
    border.color: selectedState ? style.accent : style.border
    onSelectedStateChanged: {
        if (selectedState && visible) feedbackMotion.play(indicator,"focus.change",1,false)
        else feedbackMotion.settle()
    }
    onVisibleChanged: if (!visible) feedbackMotion.settle()
    Rectangle { id: indicator; x: 12; y: parent.height - 4; width: parent.width - 24; height: 2; color: parent.style.accent; visible: parent.selectedState }
    MotionController { id: feedbackMotion; appearance: parent.style.appearance }
    border.width: selectedState ? style.focusWidth : 1
}
