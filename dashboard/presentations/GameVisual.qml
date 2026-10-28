import QtQuick
import QtQuick.Shapes
import SmartPC.Game 1.0

Item {
    id: root
    objectName: "gameVisual"
    signal posePresented(var sample)
    required property var ctx
    readonly property bool ready: !!ctx
    readonly property var visual: ctx ? ctx.style : null
    readonly property var g: ctx ? ctx.game : ({})
    property var scene: ({})
    readonly property var meta: scene.meta || ({})
    readonly property var cars: scene.cars || []
    readonly property bool track: ctx && ctx.contentId === "game.track"
    readonly property bool menu: ctx && ctx.contentId === "game.menu"
    readonly property bool leaderboard: ctx && ctx.contentId === "game.leaderboard"
    readonly property bool progress: ctx && ctx.contentId === "game.progress"
    readonly property var rows: ctx ? ctx.rows : []
    readonly property color ink: visual ? visual.textPrimary : "white"
    readonly property color muted: visual ? visual.textSecondary : "gray"
    readonly property color accent: visual ? visual.accent : "#68aaba"
    readonly property real factor: visual ? visual.textScale : 1
    readonly property string uiFont: visual ? visual.uiFamily : "Sans Serif"
    readonly property string numberFont: visual ? visual.numbersFamily : "Sans Serif"
    readonly property int pageSize: menu ? (factor>1.05 ? 4 : 5) : 4
    readonly property var trainingProgress: g.progress || ({})
    readonly property int selected: meta.selected || 0
    readonly property var observed: cars.find(row => row.id === String(selected) || row.id === "eval-"+selected) || cars[selected] || cars[0] || ({})
    readonly property string selectedName: observed.name || g.selectedDriverName || "Pilota"
    readonly property string selectedTelemetry: selectedName+(meta.presentation === "population" ? " · #"+(observed.attempt || 1) : "")+((observed.completed || observed.status === "arrivato" || observed.status === "ritirato" || g.runState === "paused") ? " · ultima" : "")+(observed.speed !== undefined ? " · "+Math.round(observed.speed*3.6)+" km/h" : "")+(observed.simRate !== undefined && observed.simRate !== null && !observed.completed && g.runState === "running" ? " · "+Number(observed.simRate).toFixed(2)+"×" : "")
    property var pendingScene: ctx ? ctx.scene : ({})
    property var consumedScene: null
    property real renderNow: 0
    property real consumedMs: 0
    property string poseEpoch: ""
    property real previousSceneTime: 0
    readonly property real presentationDelay:ctx && ctx.motionPolicy.mode === "normal" ? (meta.presentation === "population" ? 200 : 120) : 0
    property var sensorSamples: []
    property var presentedSensors: []
    property var displayedTiming: ({})
    property string timingKey: ""
    property var presentationTrace: []
    property bool tracing: false
    property string sceneResetReason: "initial"
    property int previousSensorSelection: -1
    readonly property var selectedCar: {
        for (let i=0;i<vehicleItems.count;i++) {
            const item=vehicleItems.itemAt(i)
            if (item && item.carId === observed.id) return item
        }
        return vehicleItems.count ? vehicleItems.itemAt(0) : null
    }
    function syncScene(now, snap) {
        const next=pendingScene || ({})
        if (!snap && consumedScene === next) return
        const m=next.meta || ({})
        const epoch=(next.session || "")+":"+(next.trackId || "")+":"+(m.presentation || "")+":"+((next.mode || "").indexOf("infinito")>=0 || next.mode === "impara_sorpasso" ? "continuous" : (m.generation || 0))+":"+(m.evaluationIndex || 0)
        const sceneTime=Number(m.time || 0)
        const reset=snap || epoch !== poseEpoch || m.presentation === "preview" && sceneTime<previousSceneTime
        sceneResetReason=snap ? "snap" : epoch !== poseEpoch ? "session-or-generation" : m.presentation === "preview" && sceneTime<previousSceneTime ? "new-attempt" : ""
        poseEpoch=epoch
        previousSceneTime=sceneTime
        if (consumedScene !== next) {
            // Materialize the public QVariant containers once. Repeated indexed
            // reads then use JS arrays instead of crossing the Qt boundary.
            scene=JSON.parse(JSON.stringify(next))
            consumedScene=next
            consumedMs=now
        }
        const selected=Number(m.selected || 0)
        const row=cars.find(c => c.id === String(selected) || c.id === "eval-"+selected) || cars[selected] || cars[0] || ({})
        const timing=row.timing || ({})
        const key=epoch+":"+(row.id || "")+":"+(timing.source || "")+":"+(timing.policy || "")+":"+(timing.revision || 0)
        if (key !== timingKey) { displayedTiming=timing;timingKey=key }
        const stamp=Number(next.timestamp || now/1000)*1000
        if (reset || previousSensorSelection !== Number(m.selected || 0)) sensorSamples=[]
        previousSensorSelection=Number(m.selected || 0)
        sensorSamples.push({t:stamp,values:scene.sensors || []})
        if (sensorSamples.length>16) sensorSamples.shift()
        if (snap) presentedSensors=scene.sensors || []
        for (let i=0;i<vehicleItems.count;i++) {
            const item=vehicleItems.itemAt(i)
            if (item) item.acceptSample(cars[i] || ({}),stamp,reset)
        }
    }
    function present(now) {
        renderNow=now
        syncScene(now,false)
        for (let i=0;i<vehicleItems.count;i++) {
            const item=vehicleItems.itemAt(i)
            if (item) item.advancePose(now-presentationDelay)
        }
        const at=now-presentationDelay
        if (tracing) {
        const sample={poseSampleMs:selectedCar ? selectedCar.poseSampleMs : 0,poseFromMs:selectedCar ? selectedCar.poseFromMs : 0,poseToMs:selectedCar ? selectedCar.poseToMs : 0,poseAlpha:selectedCar ? selectedCar.poseAlpha : 0,receivedMs:Number(scene.receivedMs || 0),consumedMs:consumedMs,presentedMs:now,publishedMs:Number(scene.timestamp || 0)*1000,sequence:scene.sequence || 0,simulatedTime:meta.time || 0,generation:meta.generation || 0,scenario:meta.evoTraining ? meta.evoTraining.scenario : 0,resetKey:observed.resetKey || "",policy:meta.policyVersion || "",policySwitchAt:meta.policySwitch ? meta.policySwitch.at : null,activity:meta.phase || "",resetReason:selectedCar ? selectedCar.lastResetReason : sceneResetReason,pilot:selectedName,physicalX:observed.x || 0,physicalY:observed.y || 0,presentedX:selectedCar ? selectedCar.px : 0,presentedY:selectedCar ? selectedCar.py : 0}
        posePresented(sample)
        presentationTrace.push(sample)
        if (presentationTrace.length>120) presentationTrace.shift()
        }
        while (sensorSamples.length>2 && sensorSamples[1].t<=at) sensorSamples.shift()
        if (sensorSamples.length) {
            const a=sensorSamples[0],b=sensorSamples.length>1 ? sensorSamples[1] : a
            const alpha=b.t>a.t ? Math.max(0,Math.min(1,(at-a.t)/(b.t-a.t))) : 1
            presentedSensors=a.values.map((value,i) => value+((b.values[i] === undefined ? value : b.values[i])-value)*alpha)
        }
    }
    onPendingSceneChanged:if (!frameClock.running) syncScene(Number(pendingScene.timestamp || 0)*1000,true)
    onCtxChanged:if (!frameClock.running) syncScene(Number(pendingScene.timestamp || 0)*1000,true)
    Component.onCompleted:syncScene(Number(pendingScene.timestamp || 0)*1000,true)
    GamePresentationClock {
        id:frameClock
        running:root.track && root.g.runState === "running" && root.ctx.lifecycle.active && !root.ctx.motionPolicy.suspended
        onTick:now => root.present(now)
        onRunningChanged:if (!running) root.syncScene(root.renderNow,true)
    }
    FrameAnimation {
        id:displayAnimation
        running:frameClock.running && frameClock.displaySync
        onTriggered:if (currentFrame%2 === 0) frameClock.pulse()
    }
    function action(id,target,args) { if (ctx && ctx.lifecycle.interactive) ctx.requestAction(id,target || "",args || {}) }
    function timeText(value) { return value === null || value === undefined ? "—" : Number(value).toFixed(2)+" s" }
    function lapTime(value) {
        if (value === null || value === undefined) return "—"
        const ms=Math.round(Number(value)*1000),m=Math.floor(ms/60000),sec=Math.floor(ms%60000/1000)
        return m+":"+String(sec).padStart(2,"0")+","+String(ms%1000).padStart(3,"0")
    }
    function detail(row) {
        if (menu) return row.detail || ""
        if (leaderboard && ctx.section === "qualification") return "Giro "+lapTime(row.bestLap)+" · versione "+String(row.policyHash || "").slice(0,10)
        if (leaderboard) return (row.valid !== undefined ? row.valid+"/"+(row.total || 5)+" · "+(row.laps || 1)+" giri · "+timeText(row.time) : row.status+" · "+timeText(row.finishTime))+(row.previous ? " · modello precedente" : "")
        return (({race_master:"Maestro",residual_ppo:"PPO",residual_sac:"SAC",residual_td3:"TD3",residual_tactic:"TD3 tattico"})[row.algorithm] || row.algorithm || "")+" · "+(row.reference ? "Riferimento pronto" : row.verified ? "Campione verificato" : row.hasPolicy ? row.algorithm && (row.algorithm.indexOf("residual_")===0 || row.algorithm === "race_master") ? "Base pronta" : "Modello precedente" : row.hasCandidate ? "Allenamento salvato" : "Da allenare")+" · "+(row.steps || 0)+" passi"
    }

    Rectangle {
        anchors.fill:parent
        visible:root.menu || root.ctx && root.ctx.contentId === "game.driver.details"
        color:root.visual ? root.visual.background : "#101820"
    }

    Item {
        id: arena
        objectName:"gameArena"
        visible: root.track
        width: root.width; height: root.height-56
        clip: true
        property var drawing: ({kind:"oval",bounds:[[-73,-37],[73,37]]})
        property string outerPath: "M0,0 Z"
        property string innerPath: "M0,0 Z"
        readonly property var trackSpec:root.g.configuration ? root.g.configuration.track || ({}) : ({})
        readonly property string geometryKey:(root.g.trackId || "oval-1")+":"+(trackSpec.revision || 0)+":"+(trackSpec.geometryHash || "")+":"+width+":"+height
        readonly property bool oval:drawing.kind!=="polygon"
        readonly property var bounds:drawing.bounds || [[-73,-37],[73,37]]
        readonly property bool following: root.cars.length>0 && (root.g.mode === "gara" ? !oval && Number(drawing.length || 0)>600 && root.g.camera !== "circuito" : root.g.camera === "segui" || root.g.camera === "duello")
        readonly property bool groupCamera:following && root.g.mode === "gara"
        readonly property var rival: {
            if (!following || groupCamera || root.g.camera !== "duello" || root.meta.presentation === "population") return root.selectedCar
            const picked=root.selectedCar
            if (!picked) return null
            let best=picked, distance=Infinity
            for (let i=0;i<vehicleItems.count;i++) {
                const item=vehicleItems.itemAt(i)
                if (!item || item===picked || item.status !== "in corsa") continue
                const d=Math.hypot(item.px-picked.px,item.py-picked.py)
                if (d<distance) { best=item;distance=d }
            }
            return best
        }
        readonly property var groupBounds: {
            if (root.g.mode !== "gara" || !root.cars.length) return [0,0,0,0]
            let xmin=Infinity,xmax=-Infinity,ymin=Infinity,ymax=-Infinity
            for (let i=0;i<vehicleItems.count;i++) {
                const item=vehicleItems.itemAt(i)
                if (!item) continue
                xmin=Math.min(xmin,item.px);xmax=Math.max(xmax,item.px)
                ymin=Math.min(ymin,item.py);ymax=Math.max(ymax,item.py)
            }
            return xmin===Infinity ? [0,0,0,0] : [xmin,xmax,ymin,ymax]
        }
        readonly property real selectedX:root.selectedCar ? root.selectedCar.px : 0
        readonly property real selectedY:root.selectedCar ? root.selectedCar.py : 0
        readonly property real selectedYaw:root.selectedCar ? -root.selectedCar.angle*Math.PI/180 : 0
        readonly property real rivalX:rival ? rival.px : selectedX
        readonly property real rivalY:rival ? rival.py : selectedY
        readonly property bool duel: !groupCamera && following && root.meta.presentation !== "population" && root.g.camera === "duello" && Math.hypot(rivalX-selectedX,rivalY-selectedY)<100
        property real cameraX: groupCamera ? (groupBounds[0]+groupBounds[1])/2 : following ? selectedX+(duel ? rivalX-selectedX : Math.cos(selectedYaw)*12)/2 : (bounds[1][0]+bounds[0][0])/2
        property real cameraY: groupCamera ? (groupBounds[2]+groupBounds[3])/2 : following ? selectedY+(duel ? rivalY-selectedY : Math.sin(selectedYaw)*12)/2 : (bounds[1][1]+bounds[0][1])/2
        property real scale: groupCamera ? Math.min(8,width/(groupBounds[1]-groupBounds[0]+80),height/(groupBounds[3]-groupBounds[2]+80)) : following ? Math.min(Math.max(5,8-Math.abs(Number(root.observed.speed || 0))/15),duel ? Math.min(width/(Math.abs(rivalX-selectedX)+60),height/(Math.abs(rivalY-selectedY)+60)) : 8) : oval ? Math.min(width/(root.g.mode === "gara" ? Math.max(152,Math.abs(groupBounds[0])*2+12,Math.abs(groupBounds[1])*2+12) : 152),height/(root.g.mode === "gara" ? Math.max(82.6666667,Math.abs(groupBounds[2])*2+12,Math.abs(groupBounds[3])*2+12) : 82.6666667)) : Math.min((width-24)/(bounds[1][0]-bounds[0][0]+24),(height-24)/(bounds[1][1]-bounds[0][1]+24))
        readonly property real cx:width/2-cameraX*scale
        readonly property real cy:height/2+cameraY*scale
        function path(points) { if (!points || !points.length) return "M0,0 Z";return points.map((p,i)=>(i ? "L" : "M")+p[0]+","+(-p[1])).join(" ")+" Z" }
        function prepareGeometry() {
            drawing=root.g.drawing || ({kind:"oval",bounds:[[-73,-37],[73,37]]})
            outerPath=drawing.outerPath || path(drawing.outer);innerPath=drawing.innerPath || path(drawing.inner)
        }
        onGeometryKeyChanged:Qt.callLater(prepareGeometry)
        Component.onCompleted:Qt.callLater(prepareGeometry)
        Rectangle {
            anchors.fill: parent
            radius: root.visual ? root.visual.radiusCard : 24
            color: root.visual ? root.visual.surface : "#202228"
            border.color: root.visual ? root.visual.border : "gray"
            border.width: 1
        }
        Rectangle {
            objectName: "gameOvalRoad"
            visible:arena.oval
            width:(2*(Number(arena.drawing.halfStraight || 36)+Number(arena.drawing.radius || 31))+Number(arena.drawing.roadWidth || 12))*arena.scale; height:(2*Number(arena.drawing.radius || 31)+Number(arena.drawing.roadWidth || 12))*arena.scale; radius:height/2
            anchors.centerIn: parent
            color: root.visual ? root.visual.background : "#11151b"
            border.color: root.muted; border.width:2
        }
        Rectangle {
            visible:arena.oval
            width:134*arena.scale; height:62*arena.scale; radius:height/2
            anchors.centerIn: parent; color:"transparent"
            border.color:root.muted; border.width:1; opacity:0.28
        }
        Rectangle {
            visible:arena.oval
            width:(2*(Number(arena.drawing.halfStraight || 36)+Number(arena.drawing.radius || 31))-Number(arena.drawing.roadWidth || 12))*arena.scale; height:(2*Number(arena.drawing.radius || 31)-Number(arena.drawing.roadWidth || 12))*arena.scale; radius:height/2
            anchors.centerIn: parent
            color:root.visual ? root.visual.surface : "#202228"
            border.color:root.muted; border.width:2
        }
        Repeater {
            model:Number(arena.drawing.roadWidth || 12)
            delegate: Rectangle {
                required property int index
                visible:arena.oval
                x:arena.cx-3; y:arena.cy+(Number(arena.drawing.radius || 31)-Number(arena.drawing.roadWidth || 12)/2)*arena.scale+index*arena.scale
                width:6; height:arena.scale
                color:index%2 ? root.muted : root.ink; opacity:0.65
            }
        }
        Shape {
            objectName:"gameTechnicalRoad"
            visible:!arena.oval
            x:arena.cx;y:arena.cy;width:1;height:1;scale:arena.scale;transformOrigin:Item.TopLeft
            ShapePath { fillColor:root.visual ? root.visual.background : "#11151b";strokeColor:root.muted;strokeWidth:2/arena.scale;PathSvg { path:arena.outerPath } }
            ShapePath { fillColor:root.visual ? root.visual.surface : "#202228";strokeColor:root.muted;strokeWidth:2/arena.scale;PathSvg { path:arena.innerPath } }
        }
        Item {
            visible:!arena.oval
            readonly property var start:arena.drawing.start || [0,0,0]
            x:arena.cx+start[0]*arena.scale;y:arena.cy-start[1]*arena.scale
            rotation:-start[2]*180/Math.PI
            Repeater {
                model:10
                delegate:Rectangle {
                    required property int index
                    x:-3;y:(index-5)*arena.scale;width:6;height:arena.scale
                    color:index%2 ? root.muted : root.ink;opacity:.65
                }
            }
        }
        GameTimingHud {
            id:timingHud
            property bool contentEnabled:true
            width:Math.min(480,arena.width-120);height:232*root.factor
            anchors.centerIn:parent
            timing:root.displayedTiming
            learning:root.meta.residual || ({})
            pilot:root.selectedName;factor:root.factor;ink:root.ink;muted:root.muted;accent:root.accent
            uiFont:root.uiFont;numberFont:root.numberFont
            readonly property bool safeGeometry:Math.hypot(Math.max(0,width/(2*arena.scale)-36),height/(2*arena.scale))+1 < 25
            readonly property bool occupied: {
                for (let i=0;i<root.cars.length;i++) {
                    const c=root.cars[i],pad=(3+Number(c.speed || 0)*0.2)*arena.scale
                    if (Math.abs(Number(c.x || 0))*arena.scale<width/2+pad && Math.abs(Number(c.y || 0))*arena.scale<height/2+pad) return true
                }
                return false
            }
            visible:contentEnabled && root.g.trackId === "oval-1" && !!root.observed.timing && root.g.display !== "sensori" && root.g.camera === "circuito" && safeGeometry && !occupied
        }
        Rectangle {
            id:learningPanel
            objectName:"gameLearningPanel"
            readonly property var r:root.meta.residual || ({})
            readonly property var terms:r.rewardTerms || ({})
            readonly property string panel:root.g.camera || ""
            readonly property bool safeGeometry:Math.hypot(Math.max(0,width/(2*arena.scale)-36),height/(2*arena.scale))+1<25
            readonly property bool occupied: {
                for (let i=0;i<root.cars.length;i++) {
                    const c=root.cars[i],pad=3*arena.scale
                    if (Math.abs(Number(c.x || 0))*arena.scale<width/2+pad && Math.abs(Number(c.y || 0))*arena.scale<height/2+pad) return true
                }
                return false
            }
            visible:["telemetria","premi","rete"].indexOf(panel)>=0 && !!root.meta.residual && root.g.trackId === "oval-1" && safeGeometry && !occupied
            anchors.centerIn:parent;width:Math.min(480,parent.width-80);height:252*root.factor
            color:root.visual ? root.visual.surface : "#202228";radius:16*root.factor;border.color:root.muted
            Text { x:16;y:12;width:parent.width-32;height:30*root.factor;text:learningPanel.panel === "premi" ? "Premi · episodio raccolto" : learningPanel.panel === "rete" ? "Rete · apprendimento" : (root.meta.controlMode === "direct" ? "Candidato · " : "Guida · ")+(root.meta.driverName || "Pilota");color:root.ink;font.family:root.uiFont;font.pixelSize:22*root.factor;elide:Text.ElideRight }
            Text { x:16;y:50*root.factor;width:parent.width-32;height:28*root.factor;text:learningPanel.panel === "premi" ? "Progresso  "+Number(learningPanel.terms.progress || 0).toFixed(3)+"     Tempo  "+Number(learningPanel.terms.time || 0).toFixed(3) : learningPanel.panel === "rete" ? (learningPanel.r.updates || 0)+" aggiornamenti · "+(learningPanel.r.decisions || 0)+" decisioni" : "Velocità  "+Math.round(Number(learningPanel.r.speedKmh || 0))+" km/h";color:root.ink;font.family:root.numberFont;font.pixelSize:20*root.factor;elide:Text.ElideRight }
            Text { x:16;y:88*root.factor;width:parent.width-32;height:28*root.factor;text:learningPanel.panel === "premi" ? "Segnale intermedio  "+Number(learningPanel.terms.shaping || 0).toFixed(3) : learningPanel.panel === "rete" ? (root.meta.controlMode === "direct" ? (learningPanel.r.championSeconds ? (learningPanel.r.timingProtocol ? "PB lanciato  " : "Campione  ")+Number(learningPanel.r.championSeconds).toFixed(3)+" s" : "Campione · rete preparata") : "Esplorazione laterale ≈ "+(100*Number(learningPanel.r.explorationMeters || 0)).toFixed(0)+" cm di bersaglio") : (root.meta.controlMode === "direct" ? "Gas  "+Math.round(Math.max(0,Number(learningPanel.r.pedal || 0))*100)+"%    Freno  "+Math.round(Math.max(0,-Number(learningPanel.r.pedal || 0))*100)+"%" : "Corsia richiesta  "+Number(learningPanel.r.requestedLine || 0).toFixed(2)+" m");color:root.ink;font.family:root.numberFont;font.pixelSize:20*root.factor;elide:Text.ElideRight }
            Text { x:16;y:126*root.factor;width:parent.width-32;height:28*root.factor;text:learningPanel.panel === "premi" ? "Uscite/contatti  "+Number(Number(learningPanel.terms.exit || 0)+Number(learningPanel.terms.offroad || 0)+Number(learningPanel.terms.contact || 0)+Number(learningPanel.terms.retirement || 0)).toFixed(3) : learningPanel.panel === "rete" ? (root.meta.controlMode === "direct" ? (learningPanel.r.candidateSeconds ? "Ultima verifica  "+Number(learningPanel.r.candidateSeconds).toFixed(3)+" s" : (learningPanel.r.timingProtocol ? "Prima verifica dei giri lanciati" : "Verifica dei fondamenti da eseguire")) : (learningPanel.r.episodes || 0)+" episodi · "+(learningPanel.r.verification || 0)+" verifiche") : (root.meta.controlMode === "direct" ? "Sterzo  "+Math.round(Number(learningPanel.r.steer || 0)*100)+"% · comandi della rete" : "Sterzo  "+Math.round(Number(learningPanel.r.steer || 0)*100)+"%    Pedale  "+Math.round(Number(learningPanel.r.pedal || 0)*100)+"%");color:root.ink;font.family:root.numberFont;font.pixelSize:20*root.factor;elide:Text.ElideRight }
            Text { x:16;y:166*root.factor;width:parent.width-32;height:48*root.factor;text:learningPanel.panel === "rete" ? (learningPanel.r.stage === "critic_preparation" ? "La rete guida. Si preparano i critic prima di aggiornarla." : (root.meta.controlMode === "direct" ? learningPanel.r.objectiveStage ? (learningPanel.r.attack && learningPanel.r.attack.opportunities ? "Raccolta: "+learningPanel.r.collectionLabel+" · "+learningPanel.r.attack.attacks+" attacchi · "+learningPanel.r.attack.passes+" passaggi" : learningPanel.r.objectiveStage+" · "+learningPanel.r.lastDecisionLabel+". "+learningPanel.r.raceStatus) : "Vedi il candidato. Raccolta: "+(learningPanel.r.schoolSkill || "giro")+". Gas esplorato per "+Number(learningPanel.r.pedalBlockSeconds || 0).toFixed(1)+" s." : "La prova usa la media della rete. Il rumore viene usato nella raccolta.")) : learningPanel.panel === "premi" ? "Somme dell'episodio in raccolta, distinto dal giro mostrato." : (root.meta.controlMode === "direct" ? "Rete in prova. Può peggiorare; il campione migliore resta conservato." : "Il controllore traduce corsia e passo in sterzo e pedali.");color:root.muted;font.family:root.uiFont;font.pixelSize:15*root.factor;wrapMode:Text.WordWrap }
            Text { x:16;y:222*root.factor;width:parent.width-32;height:24*root.factor;text:"4/6 · Guida / Premi / Rete";color:root.muted;font.family:root.uiFont;font.pixelSize:14*root.factor;elide:Text.ElideRight }
        }
        Repeater {
            id:vehicleItems
            model: root.cars.length
            onItemAdded:(index,item) => item.acceptSample(root.cars[index] || ({}),Number(root.scene.timestamp || root.renderNow/1000)*1000,true)
            delegate: Item {
                id: car
                objectName:"gameCar"+index
                required property int index
                property string carId: ""
                property string status: ""
                property bool completed: false
                property string number: ""
                property bool ghost: false
                property real vehicleLength: 4.4
                property real vehicleWidth: 1.8
                readonly property bool picked: carId === root.observed.id
                z: picked ? 1 : 0
                property real px: 0
                property real py: -31
                property real angle: 0
                property real previousProgress: 0
                property string resetKey: ""
                property var samples: []
                property real poseSampleMs: 0
                property real poseFromMs: 0
                property real poseToMs: 0
                property real poseAlpha: 0
                property string lastResetReason: "initial"
                function acceptSample(row,stamp,reset) {
                    const nx=Number(row.x || 0),ny=Number(row.y || 0),na=-Number(row.yaw || 0)*180/Math.PI
                    const identity=String(row.id || ""),progress=Number(row.progress || 0)
                    lastResetReason=reset ? root.sceneResetReason : carId !== identity ? "controller-identity" : resetKey !== String(row.resetKey || "") ? "attempt-revision" : progress<previousProgress-10 ? "progress-discontinuity" : root.g.runState !== "running" ? "paused" : ""
                    reset=reset || carId !== identity || resetKey !== String(row.resetKey || "") || progress<previousProgress-10 || root.g.runState !== "running" || root.ctx.motionPolicy.mode !== "normal"
                    resetKey=String(row.resetKey || "");carId=identity;status=String(row.status || "");completed=!!row.completed
                    number=String(row.number || "");ghost=!!row.ghost
                    vehicleLength=Number(row.vehicleLength || 4.4);vehicleWidth=Number(row.vehicleWidth || 1.8)
                    previousProgress=progress
                    const last=samples.length ? samples[samples.length-1] : null
                    if (reset || !last || stamp<last.t || stamp-last.t>500) {
                        samples=[{t:stamp,x:nx,y:ny,a:na}];px=nx;py=ny;angle=na
                    } else if (last.x !== nx || last.y !== ny || Math.abs(((na-last.a+180)%360+360)%360-180)>0.000001) {
                        // All points are actual samples; retain a short history.
                        samples.push({t:stamp,x:nx,y:ny,a:last.a+((na-last.a+180)%360+360)%360-180})
                        if (samples.length>16) samples.shift()
                    }
                }
                function advancePose(now) {
                    if (!samples.length || !visible) return
                    while (samples.length>2 && samples[1].t<=now) samples.shift()
                    const a=samples[0],b=samples.length>1 ? samples[1] : a
                    const alpha=b.t>a.t ? Math.max(0,Math.min(1,(now-a.t)/(b.t-a.t))) : 1
                    poseFromMs=a.t;poseToMs=b.t;poseAlpha=alpha;poseSampleMs=a.t+(b.t-a.t)*alpha
                    px=a.x+(b.x-a.x)*alpha;py=a.y+(b.y-a.y)*alpha;angle=a.a+(b.a-a.a)*alpha
                }
                visible:carId !== "" && (root.g.mode === "gara" || root.g.display === "tutte" || picked)
                opacity:status === "ritirato" ? 0.3 : completed ? 0.45 : 1
                x:arena.cx+px*arena.scale-width/2;y:arena.cy-py*arena.scale-height/2
                width:vehicleLength*arena.scale;height:vehicleWidth*arena.scale
                rotation:angle
                Rectangle { anchors.fill:parent; anchors.margins:-Math.min(2,.3*arena.scale); radius:parent.height*.3; color:"transparent";border.width:1;border.color:root.accent;visible:car.picked }
                Rectangle { anchors.fill:parent;radius:parent.height*.2;color:car.picked ? root.accent : root.ink; border.color:root.muted; border.width:Math.min(1,.08*arena.scale) }
                Rectangle { x:parent.width*0.58;y:parent.height*.12;width:parent.width*0.24;height:parent.height*.76;radius:parent.height*.1;color:root.visual ? root.visual.surface : "black" }
                Rectangle { x:parent.width*.15;y:-parent.height*.08;width:parent.width*.18;height:parent.height*.12;color:root.muted }
                Rectangle { x:parent.width*.15;y:parent.height*.96;width:parent.width*.18;height:parent.height*.12;color:root.muted }
                Text { visible:car.picked || root.g.mode !== "impara";x:-3;y:-25;width:parent.width+6;text:car.number+(car.ghost ? "×" : "");color:root.ink;font.family:root.numberFont;font.pixelSize:16;horizontalAlignment:Text.AlignHCenter;rotation:-car.rotation }
            }
        }
        Text { visible:root.meta.activityTotal>0;x:parent.width-260;y:12;width:244;height:18;text:"Scenari "+(root.meta.activityDone || 0)+"/"+root.meta.activityTotal;color:root.muted;font.family:root.uiFont;font.pixelSize:12*root.factor;horizontalAlignment:Text.AlignRight }
        Row {
            objectName: "gamePopulationAttempts"
            visible:root.meta.presentation === "population"
            x:16;y:12;spacing:4
            Text { text:"Tentativi";color:root.muted;font.family:root.uiFont;font.pixelSize:12*root.factor;rightPadding:4 }
            Repeater {
                model:root.meta.presentation === "population" ? root.meta.trainingCount : 0
                delegate:Rectangle {
                    required property int index
                    readonly property var attempt:vehicleItems.itemAt(index)
                    width:12;height:12;radius:6
                    color:index===root.selected ? root.accent : root.ink
                    opacity:index===root.selected ? 1 : attempt && attempt.completed ? 0.2 : 0.55
                }
            }
        }
        Rectangle {
            id: minimap
            objectName: "gameMinimap"
            visible:arena.following && root.g.mode !== "gara"
            x:parent.width-width-16;y:16;width:150;height:100;radius:12
            color:root.visual ? root.visual.surface : "#202228";border.color:root.muted;clip:true
            readonly property real mapScale:Math.min((width-16)/(arena.bounds[1][0]-arena.bounds[0][0]),(height-16)/(arena.bounds[1][1]-arena.bounds[0][1]))
            readonly property real mx:width/2-(arena.bounds[1][0]+arena.bounds[0][0])/2*mapScale
            readonly property real my:height/2+(arena.bounds[1][1]+arena.bounds[0][1])/2*mapScale
            Shape {
                x:minimap.mx;y:minimap.my;width:1;height:1;scale:minimap.mapScale;transformOrigin:Item.TopLeft
                ShapePath { fillColor:root.visual ? root.visual.background : "#11151b";strokeColor:root.muted;strokeWidth:1/minimap.mapScale;PathSvg { path:arena.outerPath } }
                ShapePath { fillColor:root.visual ? root.visual.surface : "#202228";strokeWidth:0;PathSvg { path:arena.innerPath } }
            }
            Repeater {
                model:root.cars.length
                delegate:Rectangle {
                    required property int index
                    readonly property var body:vehicleItems.itemAt(index)
                    visible:body !== null
                    width:body && body.picked ? 5 : 3;height:width;radius:width/2
                    x:minimap.mx+(body ? body.px : 0)*minimap.mapScale-width/2
                    y:minimap.my-(body ? body.py : 0)*minimap.mapScale-height/2
                    color:body && body.picked ? root.accent : root.ink
                }
            }
        }
        Item {
            id: sensors
            anchors.fill: parent
            visible:root.g.display === "sensori" && root.cars.length>0
            readonly property var distances:root.presentedSensors
            readonly property var angles:[-1.2,-0.6,0,0.6,1.2]
            Repeater {
                model:sensors.visible ? Math.min(5,sensors.distances.length) : 0
                delegate:Item {
                    required property int index
                    x:arena.cx+arena.selectedX*arena.scale
                    y:arena.cy-arena.selectedY*arena.scale
                    rotation:-(arena.selectedYaw+sensors.angles[index])*180/Math.PI
                    transformOrigin:Item.TopLeft
                    Rectangle {
                        y:-0.5;height:1
                        width:Number(sensors.distances[index])*Number(root.meta.sensorRange || 50)*arena.scale
                        color:root.accent;opacity:0.6
                    }
                }
            }
        }
        Text {
            anchors.centerIn:parent; width:350;height:100
            visible:root.cars.length===0
            text:root.g.available === false || root.g.runState === "error" ? root.g.message : root.g.selectedDriverName || "Scegli un pilota"
            color:root.muted;font.family:root.uiFont;font.pixelSize:28*root.factor
            horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter
        }
    }
    Rectangle {
        visible:root.track
        x:0;y:root.height-48;width:root.width;height:48
        radius:root.visual ? root.visual.radiusRow : 12
        color:root.visual ? root.visual.surface : "#202228"
        Text { x:16;y:0;width:180;height:root.meta.presentation === "population" || root.meta.presentation === "preview" ? 28 : 48;text:root.meta.presentation === "population" ? "Gen. "+(root.meta.evoTraining ? root.meta.evoTraining.stageGeneration+1 : root.meta.generation) : root.meta.presentation === "preview" || root.meta.presentation === "verification" ? root.meta.presentation === "preview" ? root.meta.residual ? "Agg. "+(root.meta.residual.updates || 0) : "Pilota" : root.meta.exercise || "Guida" : ({impara:"Impara",gara:"Gara",qualifica:"Qualifica",impara_infinito:"Giro infinito",impara_sorpasso:"Sorpasso",prova:"Prova",campione:"Campione"})[root.g.mode] || "Pronto";color:root.ink;font.family:root.uiFont;font.pixelSize:22*root.factor;verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight }
        Text { x:16;y:28;width:180;height:16;visible:root.meta.presentation === "population" || root.meta.presentation === "preview";text:root.meta.residual ? (root.meta.controlMode === "direct" ? "Candidato · prova "+(root.meta.residual.previewTrial || 1) : (root.meta.residual.episodes || 0)+" epis. · Verifica "+(root.meta.residual.verification || 0)) : root.meta.presentation === "preview" ? "Dimostrazione" : root.meta.evoTraining ? "Scen. "+root.meta.evoTraining.scenario+"/"+root.meta.evoTraining.scenarios+" · "+root.meta.evoTraining.label : root.meta.exercise || "";color:root.muted;font.family:root.uiFont;font.pixelSize:12*root.factor;elide:Text.ElideRight }
        Text { x:200;y:0;width:root.width-540;height:48;text:root.selectedTelemetry;color:root.ink;font.family:root.uiFont;font.pixelSize:21*root.factor;verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight }
        Text { x:root.width-330;y:0;width:185;height:48;text:root.g.runState === "paused" ? "In pausa" : root.g.runState === "error" ? "Interrotta" : root.g.runState === "starting" ? "Avvio" : root.g.runState === "pausing" ? "Attendi" : root.meta.countdown > 0 ? "Partenza "+Math.ceil(root.meta.countdown) : root.observed.lapValid === false ? "Giro non valido" : root.g.mode === "gara" ? "G"+Math.min(root.meta.laps || 3,(root.observed.lap || 0)+1)+" · P"+(root.observed.position || "—") : (root.g.mode || "").indexOf("impara")===0 ? root.meta.presentation === "preview" && root.meta.previewState !== "running" ? ({success:"Giro concluso",no_progress:"Stallo · riparte",contact:"Ritiro · riparte",road_boundary:"Fuori pista · riparte",vehicle_contact:"Collisione · riparte",geometry_guard:"Ritiro · geometria",retirement_unknown:"Ritiro · riparte",skill_failed:"Giro non valido",timeout:"Nuovo tentativo",blocked:"Traffico fermo"})[root.meta.previewState] || "Nuovo tentativo" : root.meta.phase === "verifica passaggio a PPO" ? "Verifica PPO "+(root.meta.activityDone || 0)+"/"+(root.meta.activityTotal || 45) : root.meta.phase === "confronto memoria" ? "Confronta base" : root.meta.phase === "familiarizzazione" ? "Base "+(root.meta.activityDone || 0)+"/"+(root.meta.activityTotal || 0) : root.meta.phase === "consolidamento" ? "Consolida "+(root.meta.activityDone || 0)+"/"+(root.meta.activityTotal || 0) : root.meta.phase === "ripasso" ? "Ripasso" : root.meta.phase === "valutazione" ? "Valuta "+(root.meta.activityDone || 0)+"/"+(root.meta.activityTotal || 0) : root.meta.phase === "aggiornamento" ? "Aggiorna rete" : root.meta.presentation === "population" ? root.meta.completedAttempts+"/"+root.meta.trainingCount+" conclusi" : root.meta.manoeuvre || root.meta.trainingExercise || root.meta.curriculumPhase || "Controllo" : root.g.mode === "qualifica" ? (root.observed.lap || 0)===0 ? "Giro di lancio" : "Giro "+Math.min(3,root.observed.lap)+"/3" : root.g.mode === "prova" ? (root.meta.evaluationIndex || 0)+"/"+(root.meta.evaluationTotal || 0) : root.g.runState === "finished" ? "Conclusa" : "";color:root.muted;font.family:root.numberFont;font.pixelSize:19*root.factor;verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight }
        Text { x:root.width-135;y:0;width:120;height:48;text:root.g.controlMode === "simulation" ? "5 Pausa" : "5 Start";color:root.accent;font.family:root.uiFont;font.pixelSize:21*root.factor;verticalAlignment:Text.AlignVCenter;horizontalAlignment:Text.AlignRight }
        MouseArea { anchors.fill:parent;onClicked:root.action(root.g.controlMode === "simulation" ? "game.pause" : "game.start") }
    }
    Item {
        visible:!root.track && !root.menu
        anchors.fill:parent
        anchors.margins:root.menu || root.ctx && root.ctx.contentId === "game.driver.details" ? 32 : 0
        Text { x:0;y:8;width:parent.width;height:44;text:root.menu ? "GIOCO" : root.leaderboard ? "CLASSIFICA" : root.progress ? "PROGRESSI" : "PILOTI";color:root.ink;font.family:root.uiFont;font.pixelSize:30*root.factor;verticalAlignment:Text.AlignVCenter }
        Text { x:0;y:56;width:parent.width;height:48;text:root.leaderboard ? (root.ctx.section === "qualification" ? "Qualifiche · " : root.ctx.section === "trial" ? "Prova standard · " : "Ultima gara · ")+((root.g.configuration || {}).track || {}).name+" · "+((root.g.leaderboard || {})[root.ctx.section === "trial" ? "trialPhysics" : "racePhysics"] || "") : root.g.selectedDriverName || "";color:root.muted;font.family:root.uiFont;font.pixelSize:22*root.factor;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter }
        Row {
            x:parent.width-470;y:22;spacing:20;visible:root.leaderboard
            Repeater { model:["Gare","Qualifica","Prove storiche"];delegate:Text {
                required property string modelData
                required property int index
                text:modelData;color:(root.ctx.section === ["race","qualification","trial"][index]) ? root.accent : root.muted;font.family:root.uiFont;font.pixelSize:22*root.factor
                MouseArea { anchors.fill:parent;onClicked:root.action("game.option.activate","category:"+["race","qualification","trial"][index]) }
            } }
        }
        Text {
            objectName:"gameTrackRecords"
            x:0;y:108;width:parent.width;height:36;visible:root.leaderboard
            readonly property var records:(root.g.leaderboard || {})[root.ctx.section === "qualification" ? "qualificationRecords" : root.ctx.section === "trial" ? "trialRecords" : "raceRecords"] || ({})
            text:"Giro "+root.lapTime(records.bestLap ? records.bestLap.value : null)+(records.bestLap ? " · "+records.bestLap.name : "")+"     V max "+(records.maxSpeed ? Math.round(records.maxSpeed.value*3.6)+" km/h · "+records.maxSpeed.name : "—")
            color:root.muted;font.family:root.numberFont;font.pixelSize:18*root.factor;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter
        }
        Repeater {
            model:5
            delegate:Rectangle {
                id:listRow
                required property int index
                readonly property int realIndex:Math.floor(root.ctx.selectedIndex/root.pageSize)*root.pageSize+index
                readonly property var row:root.rows[realIndex] || ({})
                objectName: "gameListRow"+realIndex
                x:0;y:(root.leaderboard ? 160 : root.menu ? 104 : 120)+index*(root.menu ? root.pageSize===4 ? 104 : 88 : 82);width:parent.width;height:root.menu ? root.pageSize===4 ? 94 : 80 : 72
                visible:!root.track && !root.menu && !root.progress && index<root.pageSize && row.id !== undefined
                radius:root.visual ? root.visual.radiusRow : 12
                color:root.visual ? root.visual.surface : "#202228"
                border.width:realIndex===root.ctx.selectedIndex ? 2 : 1
                border.color:realIndex===root.ctx.selectedIndex ? root.accent : root.visual ? root.visual.border : "gray"
                Text { x:18;y:6;width:parent.width-(root.menu ? 300 : 36);height:32;text:(root.leaderboard ? (listRow.row.position || listRow.realIndex+1)+"  " : "")+(listRow.row.title || listRow.row.name || "");color:root.ink;font.family:root.uiFont;font.pixelSize:24*root.factor;verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight }
                Text { objectName:"gameSettingValue"+listRow.realIndex;visible:root.menu;x:parent.width-280;y:6;width:262;height:32;text:listRow.row.value || listRow.row.detail || "";color:root.ink;font.family:root.numberFont;font.pixelSize:21*root.factor;horizontalAlignment:Text.AlignRight;verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight }
                Text { objectName:"gameSettingDescription"+listRow.realIndex;x:18;y:40;width:parent.width-36;height:root.menu ? parent.height-44 : 28;text:root.menu ? listRow.row.description || "" : root.detail(listRow.row);color:root.muted;font.family:root.uiFont;font.pixelSize:19*root.factor;verticalAlignment:Text.AlignVCenter;wrapMode:root.menu ? Text.Wrap : Text.NoWrap;elide:root.menu ? Text.ElideNone : Text.ElideRight }
                MouseArea { anchors.fill:parent;onClicked:root.action(root.menu || root.leaderboard ? "game.option.activate" : "game.driver.select",listRow.row.id) }
            }
        }
        Text { x:0;y:180;width:parent.width;height:70;visible:root.rows.length===0;text:root.leaderboard ? "Nessuna prova conclusa" : "Nessun pilota";color:root.muted;font.family:root.uiFont;font.pixelSize:26*root.factor;verticalAlignment:Text.AlignVCenter }
        Item {
            id: chart
            visible:root.progress
            x:0;y:120;width:parent.width;height:330
            readonly property var driver:(root.g.drivers || []).find(row=>row.id===root.g.selectedDriverId) || ({})
            readonly property var evaluations:(root.trainingProgress.evaluations || []).filter(row=>!root.trainingProgress.academy || row.phaseId===root.trainingProgress.phaseId).filter((row,_,all)=>!all.length || row.comparisonKey===all[all.length-1].comparisonKey)
            readonly property var latest:evaluations[evaluations.length-1] || ({})
            readonly property var champion:root.trainingProgress.champion || ({})
            readonly property var firstQualification:root.trainingProgress.baseline || ({})
            readonly property var points:evaluations.filter(row=>row.time!==null && row.retained && row.valid>=Math.ceil(.9*row.total)).map(row=>({x:row.round,y:row.time}))
            Text { x:0;y:0;width:parent.width;height:42;text:(root.trainingProgress.phase || "Da allenare")+" · "+(chart.driver.steps || 0)+" passi · "+Math.round((chart.driver.seconds || 0)/60)+" min";color:root.ink;font.family:root.numberFont;font.pixelSize:24*root.factor;verticalAlignment:Text.AlignVCenter }
            Rectangle { x:0;y:58;width:parent.width;height:260;radius:root.visual ? root.visual.radiusCard : 24;color:root.visual ? root.visual.surface : "#202228" }
            Canvas {
                id: plot
                x:24;y:94;width:parent.width-48;height:190
                Connections { target:chart;function onPointsChanged() { if (plot.visible) plot.requestPaint() } }
                onVisibleChanged:requestPaint()
                onPaint: {
                    if (!visible) return
                    const p=chart.points
                    const c=getContext("2d");c.clearRect(0,0,width,height)
                    if (p.length<2) return
                    let lo=Math.min(...p.map(v=>v.y)),hi=Math.max(...p.map(v=>v.y)),first=p[0].x,last=p[p.length-1].x
                    c.strokeStyle=root.accent;c.lineWidth=2;c.beginPath()
                    for (let i=0;i<p.length;i++) { const x=(p[i].x-first)/Math.max(1,last-first)*width,y=height-8-(p[i].y-lo)/Math.max(0.001,hi-lo)*(height-16);if(i)c.lineTo(x,y);else c.moveTo(x,y) }c.stroke()
                }
            }
            Text { x:24;y:62;width:parent.width-48;height:28;text:"Tempo mediano · stesso esercizio · almeno 90% valido";color:root.muted;font.family:root.uiFont;font.pixelSize:18*root.factor }
            Text { x:24;y:164;width:parent.width-48;visible:chart.points.length<2;text:chart.evaluations.length ? (chart.latest.summary || "Ultima verifica")+"\nVerifica complessiva "+(chart.latest.retained ? "superata" : "non superata") : "Le prove misurano tempi e validità dopo Start";color:root.muted;font.family:root.uiFont;font.pixelSize:21*root.factor;horizontalAlignment:Text.AlignHCenter;wrapMode:Text.Wrap }
            Text { x:0;y:340;width:parent.width;height:42;text:root.trainingProgress.verified ? "Campione · "+(chart.champion.valid || 0)+"/"+(chart.champion.total || 10)+" · mediana "+root.timeText(chart.champion.median)+" · migliore "+root.timeText(chart.champion.best) : chart.driver.verified ? "Versione qualificata disponibile" : chart.driver.hasCandidate ? "Candidato salvato · da qualificare" : chart.driver.hasPolicy ? "Modello salvato · da qualificare" : "Campione da qualificare · ultima prova "+(chart.latest.valid || 0)+"/"+(chart.latest.total || 10);color:root.ink;font.family:root.numberFont;font.pixelSize:21*root.factor;elide:Text.ElideRight }
            Text { x:0;y:390;width:parent.width;height:36;text:root.trainingProgress.verified && chart.firstQualification.median ? "Prima verifica "+root.timeText(chart.firstQualification.median)+(root.trainingProgress.promotionGain!==null ? " · guadagno ultima promozione "+Number(root.trainingProgress.promotionGain).toFixed(2)+" s" : "") : "Il candidato può cambiare; il campione richiede prove comparabili";color:root.muted;font.family:root.uiFont;font.pixelSize:19*root.factor;elide:Text.ElideRight }
        }
        Text { visible:!root.menu && !root.progress;x:0;y:parent.height-46;width:parent.width;height:42;text:root.leaderboard ? "5 Cambia classifica" : root.g.message || "";color:root.muted;font.family:root.uiFont;font.pixelSize:19*root.factor;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter }
    }
    Loader {
        anchors.fill:parent
        active:root.menu
        sourceComponent:Component { GameSettingsVisual { ctx:root.ctx } }
    }
}
