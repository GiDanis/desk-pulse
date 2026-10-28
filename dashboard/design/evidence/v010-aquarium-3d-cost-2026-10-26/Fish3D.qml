import QtQuick3D
Node {
    id:fish
    required property var bodyGeometry
    required property var eyeGeometry
    required property var tailGeometry
    required property var finGeometry
    required property var bodyMaterial
    required property var finMaterial
    required property var eyeMaterial
    required property var pupilMaterial
    property real phase:0
    Model { geometry:fish.bodyGeometry;materials:[fish.bodyMaterial];castsShadows:false }
    Node { x:-35;eulerRotation.y:Math.sin(fish.phase)*22
        Model {geometry:fish.tailGeometry;materials:[fish.finMaterial];castsShadows:false}
    }
    Node {x:1;y:-3;z:9;eulerRotation.x:-45-Math.sin(fish.phase+.6)*18
        Model {geometry:fish.finGeometry;materials:[fish.finMaterial];castsShadows:false}
    }
    Node {x:1;y:-3;z:-9;eulerRotation.x:45+Math.sin(fish.phase+.6)*18
        Model {geometry:fish.finGeometry;materials:[fish.finMaterial];castsShadows:false}
    }
    Model {x:8;y:16;eulerRotation.z:-65;geometry:fish.finGeometry;materials:[fish.finMaterial];castsShadows:false}
    Model {x:25;y:7;z:9;scale:Qt.vector3d(3.4,3.4,2);geometry:fish.eyeGeometry;materials:[fish.eyeMaterial];castsShadows:false}
    Model {x:25;y:7;z:-9;scale:Qt.vector3d(3.4,3.4,2);geometry:fish.eyeGeometry;materials:[fish.eyeMaterial];castsShadows:false}
    Model {x:26;y:7;z:10.9;scale:Qt.vector3d(1.7,1.7,.7);geometry:fish.eyeGeometry;materials:[fish.pupilMaterial];castsShadows:false}
    Model {x:26;y:7;z:-10.9;scale:Qt.vector3d(1.7,1.7,.7);geometry:fish.eyeGeometry;materials:[fish.pupilMaterial];castsShadows:false}
}
