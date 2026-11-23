pragma ComponentBehavior: Bound
import QtQuick
import "AquariumMotion.js" as Motion
Item {
    id: root
    required property var ctx
    readonly property var aquariumState: ctx ? ctx.aquarium : null
    readonly property string epoch: aquariumState ? aquariumState.sessionId+":"+aquariumState.assetRevision : ""
    property var rows: []
    property var speciesRows: []
    property int readinessRevision: 0
    property int tickCount: 0
    property int discardedFrames: 0
    property real activeTime: 0
    property bool firstFrame: true
    property var actors: []
    property bool benchmarkSprite: false
    property int benchmarkPopulation: 0
    readonly property real fishEnvelopeRadius: .95
    readonly property bool assetFailed: background.status === Image.Error || fishFailed()
    readonly property bool assetsReady: aquariumState && aquariumState.status === "ready" && background.status === Image.Ready && fishReady()
    readonly property bool preparingAssets: !aquariumState || aquariumState.status === "idle" || aquariumState.status === "loading"
    readonly property bool ready: width > 0 && height > 0 && (preparingAssets || assetsReady || assetFailed || aquariumState && aquariumState.status === "error")
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property bool moving: assetsReady && ctx.lifecycle.active && !ctx.lifecycle.preview && aquariumState.effectivePlayback === "running" && ctx.motionPolicy.mode === "normal" && !ctx.motionPolicy.suspended
    readonly property var mandatoryRegions: [{role:"body",x:16,y:72,width:width-32,height:height-88}]
    function fishReady() {
        const revision=readinessRevision
        if (!fishItems.count) return false
        for (let i=0;i<fishItems.count;i++) if (!fishItems.itemAt(i) || !fishItems.itemAt(i).partsReady) return false
        return true
    }
    function fishFailed() {
        const revision=readinessRevision
        for (let i=0;i<fishItems.count;i++) {
            const item=fishItems.itemAt(i) as FishRig
            if (item && item.partsFailed) return true
        }
        return false
    }
    function initialize() {
        if (!aquariumState) return
        // Remove delegates before replacing their species lookup. A transition
        // to loading/error must never feed an old fish an empty species DTO.
        rows=[]
        actors=[]
        speciesRows=JSON.parse(JSON.stringify(aquariumState.species))
        const initial=JSON.parse(JSON.stringify(aquariumState.instances))
        if (benchmarkPopulation>0 && initial.length) {
            const result=[]
            for(let i=0;i<benchmarkPopulation;i++) result.push(Object.assign({},initial[i%initial.length],{id:"bench-"+i,startX:.1+(i*.173)% .8,startY:.2+(i*.231)% .55,phase:(i*.173)%1}))
            rows=result
        } else rows=initial
        actors=[];activeTime=0;firstFrame=true
        Qt.callLater(resetMotion)
    }
    function resetMotion() {
        const safe=ctx ? ctx.safeArea : {x:16,y:72,width:width-32,height:height-88}
        const next=[]
        for(let i=0;i<fishItems.count;i++) {
            const item=fishItems.itemAt(i),row=rows[i]
            if(!item || !row) continue
            // Envelope includes outstretched fins and the maximum body tilt,
            // rather than only the unrotated Item's height.
            const margin=item.width*root.fishEnvelopeRadius
            const area={x:safe.x+margin,y:safe.y+margin,width:Math.max(1,safe.width-2*margin),height:Math.max(1,safe.height-2*margin)}
            const start={x:area.x+row.startX*area.width,y:area.y+row.startY*area.height}
            const random=Motion.rng((aquariumState.seed+i*7919)>>>0),direction={x:i%2 ? -1:1,y:.05}
            next.push({curve:Motion.segment(start,direction,area,random),distance:0,area:area,radius:margin,random:random,phase:row.phase*2*Math.PI,face:direction.x})
            item.x=start.x-item.width/2;item.y=start.y-item.height/2;item.facing=direction.x
        }
        actors=next
    }
    function advance(dt) {
        if(firstFrame) { firstFrame=false;return }
        if(!isFinite(dt) || dt<=0) return
        if(dt>.100) {discardedFrames++;return}
        activeTime+=dt;tickCount++
        for(let i=0;i<actors.length;i++) {
            const a=actors[i],item=fishItems.itemAt(i)
            if(!item) continue
            a.distance+=item.species.speed*dt
            if(a.distance>a.curve.length) {
                const end=Motion.sample(a.curve,a.curve.length)
                a.curve=Motion.segment({x:end.x,y:end.y},{x:end.dx,y:end.dy},a.area,a.random)
                a.distance=0
            }
            const p=Motion.sample(a.curve,a.distance), target=p.dx>=0 ? 1:-1
            a.face+=Motion.clamp(target-a.face,-dt*2.5,dt*2.5)
            item.facing=a.face
            item.x=p.x-item.width/2;item.y=p.y-item.height/2
            item.tilt=Motion.clamp(Math.atan2(p.dy,Math.abs(p.dx))*180/Math.PI,-25,25)*(target>0 ? 1:-1)
            item.phase=a.phase+activeTime*item.species.tailFrequency*2*Math.PI
            item.tickCount++
        }
    }
    // Typed DTO fields are published in one GUI transaction. Defer copying
    // arrays until the revision and its species/instances are all installed.
    onEpochChanged: Qt.callLater(initialize)
    onBenchmarkPopulationChanged: initialize()
    onWidthChanged:Qt.callLater(resetMotion)
    onHeightChanged:Qt.callLater(resetMotion)
    onMovingChanged:firstFrame=true
    Component.onCompleted:Qt.callLater(initialize)
    Rectangle { anchors.fill:parent;color:"#193e49" }
    Image { id:background;anchors.fill:parent;source:root.aquariumState ? root.aquariumState.backgroundUrl : "";sourceSize:Qt.size(960,640);fillMode:Image.PreserveAspectCrop;asynchronous:true;cache:true }
    Rectangle {anchors.fill:parent;color:"#071720";opacity:root.ctx && root.ctx.style.variant === "night" ? .26:0}
    Repeater {
        id:fishItems
        model:root.rows
        onItemAdded:{root.readinessRevision++;Qt.callLater(root.resetMotion)}
        onItemRemoved:root.readinessRevision++
        delegate:FishRig {
            required property var modelData
            required property int index
            spriteMode:root.benchmarkSprite
            species:root.speciesRows.find(row=>row.id===modelData.speciesId) || ({})
            width:(species.referenceSize || 100)*(modelData.depth===0 ? .82:modelData.depth===2 ? 1.12:1)
            height:width*.64;z:modelData.depth
            opacity:modelData.depth===0 ? .8:1
            onPartsReadyChanged:root.readinessRevision++
            onPartsFailedChanged:root.readinessRevision++
        }
    }
    FrameAnimation {id:clock;running:root.moving;onTriggered:root.advance(frameTime)}
    Rectangle {
        visible:root.preparingAssets || root.assetFailed || root.aquariumState && (root.aquariumState.status === "error" || root.aquariumState.requestedPlayback === "paused" || root.ctx.motionPolicy.mode !== "normal")
        x:24;y:parent.height-height-24;width:message.implicitWidth+32;height:44;radius:12;color:"#dd152d36";z:5
        Text {id:message;anchors.centerIn:parent;color:"#f0f3f1";font.pixelSize:20;font.family:root.ctx ? root.ctx.style.uiFamily:"Sans Serif";text:root.preparingAssets ? "Preparazione acquario…" : root.assetFailed || root.aquariumState && root.aquariumState.status === "error" ? "Acquario non disponibile · Menu per uscire" : root.ctx.motionPolicy.mode !== "normal" ? "Movimento disattivato nelle impostazioni Aspetto" : "In pausa · 5 per riprendere"}
    }
}
