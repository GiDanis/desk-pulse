import QtQuick
import "../themes"
AppText {
    property bool urgent: false
    readonly property string homeKey: "1"
    readonly property string backKey: "7"
    text: urgent ? "5 DETTAGLI · " + backKey + " CHIUDI · " + homeKey + " HOME" : backKey + " INDIETRO · " + homeKey + " HOME"
    color: style.accent
    font.pixelSize: style.font25
}
