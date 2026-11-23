pragma ComponentBehavior: Bound
import QtQuick
import QtQuick3D
Item {
    id: root
    required property var ctx
    readonly property var scene:ctx.scene
    readonly property string populationKey:scene.assetRevision+":"+scene.populationRevision
    property var actors: ({})
    property var retiring: []
    property var candidate:null
    property string candidateId:""
    property int candidateFrames:0
    readonly property bool candidateSent:candidateReceipt.committed
    AquariumAcknowledgement {
        id: candidateReceipt
        ctx: root.ctx
        action: "aquarium.prepared"
        target: root.candidateId
    }
    readonly property string acknowledgementError: {
        if (candidateReceipt.errorText) return candidateReceipt.errorText
        for (const id of Object.keys(actors)) if (actors[id].shownAck.errorText) return actors[id].shownAck.errorText
        return ""
    }
    property int tickCount:0
    property int renderTicks:0
    property bool firstFrame:true
    readonly property bool ready:width>0 && height>0
    readonly property bool contentReady:ready
    readonly property string error:""
    readonly property bool assetsReady:scene.status==="ready" && background.status===Image.Ready && allMeshesReady()
    readonly property bool assetFailed:background.status===Image.Error || scene.status==="ready" && Object.keys(actors).length>0 && !allMeshesReady()
    readonly property bool moving:assetsReady && ctx.lifecycle.active && !ctx.lifecycle.preview && !ctx.motionPolicy.suspended && ctx.motionPolicy.mode==="normal" && scene.effectivePlayback==="running"
    readonly property bool presented:scene.status==="ready" && ctx.lifecycle.active && !ctx.lifecycle.preview && !ctx.motionPolicy.suspended
    readonly property bool needsAck:Object.keys(actors).some(id=>!actors[id].shownSent)
    readonly property var mandatoryRegions:[{role:"body",x:16,y:72,width:width-32,height:height-88}]
    readonly property var sceneStats:view.renderStats
    function allMeshesReady() {
        const key=populationKey
        const ids=Object.keys(actors)
        return ids.every(id=>actors[id].meshReady)
    }
    function sync() {
        const next={},rows=JSON.parse(JSON.stringify(scene.fish))
        for(const row of rows) {
            let actor=actors[row.id]
            if(!actor && candidate && candidate.fish.id===row.id) { actor=candidate;candidate=null;candidateId="";actor.warming=false;actor.fade=moving ? 0:1 }
            if(!actor) {
                actor=fishComponent.createObject(world,{fish:row,publicContext:root.ctx})
                actor.age=0
                actor.advance(0,width,height,ctx.safeArea)
            } else actor.fish=row
            next[row.id]=actor
        }
        for(const id of Object.keys(actors)) if(!next[id]) {
            if(moving)retiring=retiring.concat([actors[id]]);else actors[id].destroy()
        }
        actors=next
        const pending=JSON.parse(JSON.stringify(scene.pending))
        const p=pending.length ? pending[0]:null
        if(candidate && (!p || p.operationId!==candidateId)) {candidate.destroy();candidate=null;candidateId=""}
        if(p && !candidate) {candidate=fishComponent.createObject(world,{fish:p,warming:true,z:-150,publicContext:root.ctx});candidateId=p.operationId;candidateFrames=0}
    }
    onPopulationKeyChanged:Qt.callLater(sync)
    Component.onCompleted:Qt.callLater(sync)
    onMovingChanged:firstFrame=true
    Rectangle {anchors.fill:parent;color:"#193e49"}
    Image {id:background;anchors.fill:parent;source:Qt.resolvedUrl("../../assets/aquarium/calm-v1/background.png");sourceSize:Qt.size(960,640);fillMode:Image.PreserveAspectCrop;asynchronous:true}
    View3D {
        id:view;objectName:"aquariumView3D";anchors.fill:parent
        renderMode:View3D.Offscreen
        environment:SceneEnvironment {backgroundMode:SceneEnvironment.Transparent;antialiasingMode:SceneEnvironment.NoAA;tonemapMode:SceneEnvironment.TonemapModeLinear}
        camera:camera
        PerspectiveCamera {id:camera;z:1000;clipNear:1;clipFar:3000;fieldOfView:2*Math.atan(root.height/2000)*180/Math.PI}
        DirectionalLight {eulerRotation:Qt.vector3d(-35,-25,0);brightness:.9;ambientColor:"#869a9b";castsShadow:false}
        DirectionalLight {eulerRotation:Qt.vector3d(25,155,0);brightness:.5;castsShadow:false}
        Node {id:world}
    }
    Component {id:fishComponent;Fish3DActor {}}
    FrameAnimation {
        running:root.presented && (root.moving || root.candidate!==null || root.needsAck || root.retiring.length>0)
        onTriggered:{
            if(root.firstFrame) {root.firstFrame=false;return}
            const dt=Math.min(frameTime,.05)
            root.renderTicks++
            if(root.moving)root.tickCount++
            for(const id of Object.keys(root.actors)) {
                const a=root.actors[id]
                if(root.moving)a.advance(dt,root.width,root.height,root.ctx.safeArea)
                a.fade=root.moving ? Math.min(1,a.fade+dt/.7):1
                if(!a.shownSent && a.fish.visitId && root.renderTicks%15===0) a.shownAck.tick()
            }
            const leaving=[]
            for(const a of root.retiring) {
                a.fade=root.moving ? Math.max(0,a.fade-dt/.7):0
                if(a.fade>0) {a.advance(dt,root.width,root.height,root.ctx.safeArea);leaving.push(a)} else a.destroy()
            }
            if(root.retiring.length)root.retiring=leaving
            if(root.candidate && root.candidate.meshReady && !root.candidateSent) {
                root.candidateFrames++
                if(root.candidateFrames>=3 && root.renderTicks%15===0)candidateReceipt.tick()
            }
        }
    }
    Rectangle {anchors.fill:parent;color:"#071720";opacity:root.ctx.style.variant==="night" ? .25:0}
    Rectangle {
        visible:!!root.scene.errorText || !!root.acknowledgementError || !root.assetsReady || root.ctx.motionPolicy.mode!=="normal" || root.scene.effectivePlayback!=="running"
        x:24;y:Math.min(parent.height-height-24,root.ctx.safeArea.y+root.ctx.safeArea.height-height-8);width:Math.min(900,message.implicitWidth+32);height:44;radius:12;color:"#dd152d36"
        Text {id:message;anchors.centerIn:parent;color:"#f0f3f1";font.pixelSize:20;font.family:root.ctx.style.uiFamily;text:root.acknowledgementError || root.scene.errorText || (root.assetFailed ? "Modello non disponibile · Menu per sostituire il pesce":root.scene.status!=="ready" ? "Preparazione acquario 3D…":root.ctx.motionPolicy.mode!=="normal" ? "Movimento disattivato nelle impostazioni Aspetto":root.scene.effectivePlayback!=="running" ? "In pausa · 5 per riprendere":"Preparazione dei pesci…")}
    }
}
