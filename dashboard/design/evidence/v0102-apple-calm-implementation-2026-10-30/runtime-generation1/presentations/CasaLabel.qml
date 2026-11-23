import QtQuick
Text {
    required property var visualStyle
    textFormat: Text.PlainText
    font.family: visualStyle.uiFamily
    font.pixelSize: visualStyle.font22
    font.weight: visualStyle.bodyWeight
    color: visualStyle.textPrimary
    elide: Text.ElideRight
    renderType: Text.NativeRendering
}
