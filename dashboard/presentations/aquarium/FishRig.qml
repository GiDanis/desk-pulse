import QtQuick
Item {
    id: fish
    required property var species
    property bool spriteMode: false
    property real phase: 0
    property real facing: 1
    property real tilt: 0
    readonly property real unit: width / 1000
    readonly property bool partsFailed: spriteMode ? spriteProbe.status === Image.Error : body.status === Image.Error || tail.status === Image.Error || fin.status === Image.Error
    readonly property bool partsReady: spriteMode ? spriteProbe.status === Image.Ready : body.status === Image.Ready && tail.status === Image.Ready && fin.status === Image.Ready
    property int tickCount: 0
    function rect(value) { return Qt.rect(value.x,value.y,value.width,value.height) }
    Item {
        id: ink
        anchors.centerIn: parent
        width:parent.width;height:parent.height
        rotation:fish.tilt
        transform:Scale {origin.x:ink.width/2;origin.y:ink.height/2;xScale:fish.facing}
        Image { id:spriteProbe;visible:false;source:fish.spriteMode ? fish.species.spriteUrl : "";asynchronous:true;cache:true }
        // The bake includes transparent padding around the 250x160 rig;
        // preserve its scale and full fin/tail envelope in the sprite branch.
        AnimatedSprite { anchors.centerIn:parent;width:parent.width*384/250;height:parent.height*256/160;visible:fish.spriteMode;source:fish.spriteMode ? fish.species.spriteUrl : "";frameWidth:384;frameHeight:256;frameCount:16;running:false;interpolate:false;currentFrame:((Math.floor(fish.phase/(2*Math.PI)*16)%16)+16)%16 }
        Item {
            visible:!fish.spriteMode
            x:fish.width*.38; y:-fish.width*.03
            Image {
                id:tail
                x:(fish.species.tailAnchor.x-fish.species.tailPivot.x)*fish.unit
                y:(fish.species.tailAnchor.y-fish.species.tailPivot.y)*fish.unit
                width:fish.species.tailRect.width*fish.unit;height:fish.species.tailRect.height*fish.unit
                source:fish.spriteMode ? "" : fish.species.atlasUrl
                sourceClipRect:fish.rect(fish.species.tailRect)
                asynchronous:true;cache:true
                transform:Rotation {origin.x:fish.species.tailPivot.x*fish.unit;origin.y:fish.species.tailPivot.y*fish.unit;angle:Math.sin(fish.phase)*12}
            }
            Image {
                id:body
                width:fish.species.bodyRect.width*fish.unit;height:fish.species.bodyRect.height*fish.unit
                source:fish.spriteMode ? "" : fish.species.atlasUrl;sourceClipRect:fish.rect(fish.species.bodyRect)
                asynchronous:true;cache:true
            }
            Image {
                id:fin
                x:(fish.species.finAnchor.x-fish.species.finPivot.x)*fish.unit
                y:(fish.species.finAnchor.y-fish.species.finPivot.y)*fish.unit
                width:fish.species.finRect.width*fish.unit;height:fish.species.finRect.height*fish.unit
                source:fish.spriteMode ? "" : fish.species.atlasUrl;sourceClipRect:fish.rect(fish.species.finRect)
                asynchronous:true;cache:true
                transform:Rotation {origin.x:fish.species.finPivot.x*fish.unit;origin.y:fish.species.finPivot.y*fish.unit;angle:Math.sin(fish.phase+.6)*9}
            }
        }
    }
}
