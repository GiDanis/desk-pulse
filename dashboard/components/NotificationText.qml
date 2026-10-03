import QtQuick
import "../themes"

Text {
    required property NotificationStyle style
    property string role: "body"
    color: role === "title" ? style.titleColor : role === "source" ? style.sourceColor : role === "guide" ? style.noticeAccent : style.bodyColor
    font.family: role === "title" ? style.titleFamily : role === "source" ? style.sourceFamily : role === "guide" ? style.guideFamily : style.bodyFamily
    font.pixelSize: role === "title" ? style.titleSize : role === "source" ? style.sourceSize : role === "guide" ? style.guideSize : style.bodySize
    font.weight: role === "title" || role === "guide" ? style.titleWeight : style.noticeBodyWeight
    textFormat: Text.PlainText
    wrapMode: Text.Wrap
}
