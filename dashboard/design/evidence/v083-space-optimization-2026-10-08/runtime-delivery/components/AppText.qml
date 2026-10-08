import QtQuick
import "../themes"
Text {
    property StyleFacade style: Theme
    property string role: "body"
    font.pixelSize: role === "heading" ? style.font37 : role === "display" ? style.font139 : role === "numbers" ? style.font33 : role === "caption" ? style.font20 : style.font22
    font.family: role === "numbers" ? style.numbersFamily : role === "display" ? style.displayFamily : style.uiFamily
    font.weight: role === "heading" ? style.headingWeight : style.bodyWeight
}
