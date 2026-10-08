import QtQuick
import "../themes"
Rectangle {
    property StyleFacade style: Theme
    color: style.surface
    radius: style.radiusCard
    border.color: style.border
    border.width: style.borderWidth
}
