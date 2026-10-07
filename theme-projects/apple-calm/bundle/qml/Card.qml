pragma ComponentBehavior: Bound
import QtQuick

Rectangle {
    property var style: null
    color: style ? style.surface : "#FFFFFF"
    radius: style ? style.radiusCard : 24
    border.width: 1
    border.color: style ? style.border : "#CDD2DA"
}
