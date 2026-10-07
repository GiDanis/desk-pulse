pragma ComponentBehavior: Bound
import QtQuick
import "IconPaths.js" as Artwork

Item {
    id: root
    property var style: null
    property string iconId: ""
    property var descriptor: ({})
    property string symbol: ""
    property color tint: "#1D1D1F"
    property int opticalSize: 32
    property bool active: true
    readonly property string resolvedSymbol: Artwork.paths[symbol] ? symbol : Artwork.aliases[iconId] || "unknown"
    readonly property bool ready: drawing.status === Image.Ready
    readonly property string error: drawing.status === Image.Error ? "Icona non disponibile" : ""
    implicitWidth: opticalSize
    implicitHeight: opticalSize
    width: opticalSize
    height: opticalSize
    function settleMotion() { }
    Image {
        id: drawing
        anchors.fill:parent
        readonly property int atlasCell: Artwork.cell(root.resolvedSymbol,root.tint)
        source:"icon-atlas.png"
        sourceClipRect:Qt.rect((atlasCell % Artwork.columns)*Artwork.tile,Math.floor(atlasCell / Artwork.columns)*Artwork.tile,Artwork.tile,Artwork.tile)
        cache:true
        smooth:true
    }
}
