import QtQuick
import "../themes"

Text {
    required property NotificationStyle style
    property bool focused: false
    property string role: "body"
    color: role === "title" ? (focused ? style.focusedTitleColor : style.titleColor) : role === "source" ? (focused ? style.focusedSourceColor : style.sourceColor) : role === "guide" ? style.guideColor : (focused ? style.focusedBodyColor : style.bodyColor)
    font.family: role === "title" ? style.titleFamily : role === "source" ? style.sourceFamily : role === "guide" ? style.guideFamily : style.bodyFamily
    font.pixelSize: role === "title" ? style.titleSize : role === "source" ? style.sourceSize : role === "guide" ? style.guideSize : style.bodySize
    font.weight: role === "title" || role === "guide" ? style.titleWeight : style.noticeBodyWeight
    textFormat: Text.PlainText
    wrapMode: Text.Wrap
}
