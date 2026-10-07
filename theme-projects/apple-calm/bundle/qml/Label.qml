pragma ComponentBehavior: Bound
import QtQuick

Text {
    id: root
    property var themeStyle: null
    property int size: 22
    property bool secondary: false
    color: themeStyle ? secondary ? themeStyle.textSecondary : themeStyle.textPrimary : "#1D1D1F"
    font.family: themeStyle ? themeStyle.uiFamily : "Sans Serif"
    font.pixelSize: Math.round(size * (themeStyle ? themeStyle.textScale : 1))
    font.weight: Font.Normal
    wrapMode: Text.Wrap
    elide: Text.ElideRight
    maximumLineCount: 2
    verticalAlignment: Text.AlignVCenter
}
