import QtQuick
import QtQuick3D
import SmartPC.Aquarium 1.0
Node {
    id: actor
    property var fish: ({})
    property real age: 0
    property real yaw: 0
    property bool warming: false
    property real fade: 1
    property bool shownSent: false
    readonly property bool meshReady: !!mesh && mesh.valid
    readonly property real phase: age*(fish.frequency || 1)*2*Math.PI+(fish.phase || 0)*Math.PI*2
    function advance(dt,w,h,safe) {
        age+=dt
        const radius=(fish.size || 120)*.78
        const left=safe.x+radius,right=safe.x+safe.width-radius
        const top=safe.y+radius,bottom=safe.y+safe.height-radius
        const amp=Math.max(20,(right-left)/2),speed=fish.speed || 25
        const seed=(fish.seed || 1)%997/997*6.28
        const initial=Math.asin(Math.max(-.95,Math.min(.95,((fish.startX || .5)-.5)*2)))
        const angle=age*speed/amp+((fish.seed || 0)%2 ? Math.PI-initial:initial)
        const px=(left+right)/2+amp*Math.sin(angle)
        const yPhase=age*speed/amp*.57+Math.asin(((fish.startY || .5)-.5)*2)
        const py=(top+bottom)/2+Math.max(8,(bottom-top)/2)*Math.sin(yPhase)
        const vz=9*Math.cos(age*.12+seed)
        const target=Math.atan2(-vz,speed*Math.cos(angle))*180/Math.PI
        let diff=(target-yaw+540)%360-180
        yaw=(yaw+Math.max(-dt*70,Math.min(dt*70,diff))+360)%360
        z=(fish.depth-1)*28+70*Math.sin(age*.12+seed)
        const projection=(1000-z)/1000
        x=(px-w/2)*projection;y=(h/2-py)*projection
        eulerRotation=Qt.vector3d(Math.sin(age*.35+seed)*3,yaw,Math.sin(yPhase)*5)
    }
    scale: Qt.vector3d(1,1,1).times(warming ? .015:(fish.size || 120)/102)
    Node { id: bodyBone }
    Node { id: middleBone; x:-10;eulerRotation.y:Math.sin(actor.phase)*5 }
    Node { id: tailBone; x:-36;eulerRotation.y:Math.sin(actor.phase-.7)*19 }
    Model {
        opacity:actor.fade
        geometry: FishMesh {id:mesh;source:actor.fish.assetUrl || ""}
        skin: Skin {
            joints:[bodyBone,middleBone,tailBone]
            inverseBindPoses:[Qt.matrix4x4(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1),Qt.matrix4x4(1,0,0,10,0,1,0,0,0,0,1,0,0,0,0,1),Qt.matrix4x4(1,0,0,36,0,1,0,0,0,0,1,0,0,0,0,1)]
        }
        castsShadows:false
        receivesShadows:false
        materials: PrincipledMaterial {baseColor:actor.fish.tint || "#ffffff";vertexColorsEnabled:true;roughness:.4;metalness:0;specularAmount:.35}
    }
}
