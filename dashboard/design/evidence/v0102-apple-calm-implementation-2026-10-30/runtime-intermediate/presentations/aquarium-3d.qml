import QtQuick
import SmartPC.ThemeApi 2.14
Item {
    id:root
    required property Aquarium3DContext context
    readonly property bool ready:!context.scene.runtimeAvailable || visual.status===Loader.Ready && visual.item.ready
    readonly property bool contentReady:ready
    readonly property string error:""
    readonly property bool assetsReady:!!visual.item && visual.item.assetsReady
    readonly property bool assetFailed:visual.status===Loader.Error || !!visual.item && visual.item.assetFailed
    readonly property bool moving:!!visual.item && visual.item.moving
    readonly property int tickCount:visual.item ? visual.item.tickCount:0
    readonly property var sceneStats:visual.item ? visual.item.sceneStats:null
    property bool requested:false
    function load() {if(context.scene.runtimeAvailable && !requested) {requested=true;visual.setSource(Qt.resolvedUrl("aquarium/Aquarium3DVisual.qml"),{ctx:context})}}
    Loader {id:visual;anchors.fill:parent;asynchronous:true}
    Connections {target:root.context.scene;function onRuntimeAvailableChanged(){root.load()}}
    Component.onCompleted:load()
    Text {visible:!root.context.scene.runtimeAvailable;x:28;y:110;width:900;color:root.context.style.textPrimary;font.pixelSize:22;text:"Rendering 3D non disponibile · Menu per gestire i pesci"}
}
