import QtQuick
import "../themes"
Item {
    property StyleFacade style: Theme
    property bool active: false
    property var configuration: ({})
    property var actorState: ({})
    width: 30; height: 30
    Rectangle { anchors.fill: parent; radius: style.radiusCard; color: style.accent }
    Rectangle { x: 7; y: 9; width: 4; height: 4; color: style.background }
    Rectangle { x: 19; y: 9; width: 4; height: 4; color: style.background }
}
