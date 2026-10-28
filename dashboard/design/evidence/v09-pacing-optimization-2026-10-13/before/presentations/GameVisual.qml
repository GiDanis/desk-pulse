import QtQuick
import QtQuick.Shapes

Item {
    id: root
    required property var ctx
    readonly property bool ready: !!ctx
    readonly property var visual: ctx ? ctx.style : null
    readonly property var g: ctx ? ctx.game : ({})
    readonly property var scene: ctx ? ctx.scene : ({})
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
    readonly property string selectedTelemetry: selectedName+(meta.presentation === "population" ? " · #"+(observed.attempt || 1) : "")+(observed.speed !== undefined ? " · "+Math.round(observed.speed*3.6)+" km/h" : "")
    function action(id,target,args) { if (ctx && ctx.lifecycle.interactive) ctx.requestAction(id,target || "",args || {}) }
    function timeText(value) { return value === null || value === undefined ? "—" : Number(value).toFixed(2)+" s" }
    function detail(row) {
        if (menu) return row.detail || ""
        if (leaderboard) return (row.valid !== undefined ? row.valid+"/"+(row.total || 5)+" · "+(row.laps || 1)+" giri · "+timeText(row.time) : row.status+" · "+timeText(row.finishTime))+(row.previous ? " · modello precedente" : "")
        return (row.algorithm || "")+" · "+(row.reference ? "Riferimento pronto" : row.verified ? "Campione verificato" : row.hasPolicy ? "Modello precedente" : row.hasCandidate ? "Allenamento salvato" : "Da allenare")+" · "+(row.steps || 0)+" passi"
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
        property var drawing: ({kind:"oval",bounds:[[-72,-36],[72,36]]})
        property string outerPath: "M0,0 Z"
        property string innerPath: "M0,0 Z"
        readonly property var trackSpec:root.g.configuration ? root.g.configuration.track || ({}) : ({})
        readonly property string geometryKey:(root.g.trackId || "oval-1")+":"+(trackSpec.revision || 0)+":"+(trackSpec.geometryHash || "")+":"+width+":"+height
        readonly property bool oval:drawing.kind!=="polygon"
        readonly property var bounds:drawing.bounds || [[-72,-36],[72,36]]
        readonly property bool following: !oval && Number(drawing.length || 0)>600 && root.cars.length>0 && root.g.camera !== "circuito"
        readonly property var rival: root.cars.filter(c => c.id !== root.observed.id && c.status === "in corsa").sort((a,b) => Math.hypot(a.x-root.observed.x,a.y-root.observed.y)-Math.hypot(b.x-root.observed.x,b.y-root.observed.y))[0] || root.observed
        readonly property bool groupCamera:following && root.g.mode === "gara"
        readonly property var groupBounds:root.cars.length ? [Math.min(...root.cars.map(c=>c.x)),Math.max(...root.cars.map(c=>c.x)),Math.min(...root.cars.map(c=>c.y)),Math.max(...root.cars.map(c=>c.y))] : [0,0,0,0]
        readonly property bool duel: !groupCamera && following && root.meta.presentation !== "population" && root.g.camera === "duello" && Math.hypot(Number(rival.x || 0)-Number(root.observed.x || 0),Number(rival.y || 0)-Number(root.observed.y || 0))<100
        property real cameraX: groupCamera ? (groupBounds[0]+groupBounds[1])/2 : following ? Number(root.observed.x || 0)+(duel ? Number(rival.x || 0)-Number(root.observed.x || 0) : Math.cos(Number(root.observed.yaw || 0))*12)/2 : (bounds[1][0]+bounds[0][0])/2
        property real cameraY: groupCamera ? (groupBounds[2]+groupBounds[3])/2 : following ? Number(root.observed.y || 0)+(duel ? Number(rival.y || 0)-Number(root.observed.y || 0) : Math.sin(Number(root.observed.yaw || 0))*12)/2 : (bounds[1][1]+bounds[0][1])/2
        property real scale: groupCamera ? Math.min(8,width/(groupBounds[1]-groupBounds[0]+80),height/(groupBounds[3]-groupBounds[2]+80)) : following ? Math.min(Math.max(5,8-Math.abs(Number(root.observed.speed || 0))/15),duel ? Math.min(width/(Math.abs(rival.x-root.observed.x)+60),height/(Math.abs(rival.y-root.observed.y)+60)) : 8) : oval ? Math.min(width/(root.g.mode === "gara" ? Math.max(152,...root.cars.map(c=>Math.abs(c.x)*2+12)) : 152),height/(root.g.mode === "gara" ? Math.max(82.6666667,...root.cars.map(c=>Math.abs(c.y)*2+12)) : 82.6666667)) : Math.min((width-24)/(bounds[1][0]-bounds[0][0]+24),(height-24)/(bounds[1][1]-bounds[0][1]+24))
        readonly property real cx:width/2-cameraX*scale
        readonly property real cy:height/2+cameraY*scale
        Behavior on cameraX { enabled: !arena.groupCamera && arena.following && root.ctx.motionPolicy.mode === "normal"; NumberAnimation { duration:80 } }
        Behavior on cameraY { enabled: !arena.groupCamera && arena.following && root.ctx.motionPolicy.mode === "normal"; NumberAnimation { duration:80 } }
        Behavior on scale { enabled: !arena.groupCamera && arena.following && root.ctx.motionPolicy.mode === "normal"; NumberAnimation { duration:180 } }
        function path(points) { if (!points || !points.length) return "M0,0 Z";return points.map((p,i)=>(i ? "L" : "M")+p[0]+","+(-p[1])).join(" ")+" Z" }
        function prepareGeometry() {
            drawing=root.g.drawing || ({kind:"oval",bounds:[[-72,-36],[72,36]]})
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
            width:144*arena.scale; height:72*arena.scale; radius:height/2
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
            width:124*arena.scale; height:52*arena.scale; radius:height/2
            anchors.centerIn: parent
            color:root.visual ? root.visual.surface : "#202228"
            border.color:root.muted; border.width:2
        }
        Repeater {
            model:10
            delegate: Rectangle {
                required property int index
                visible:arena.oval
                x:arena.cx-3; y:arena.cy+26*arena.scale+index*arena.scale
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
        Repeater {
            model: root.cars.length
            delegate: Item {
                id: car
                objectName:"gameCar"+index
                required property int index
                readonly property var row: root.cars[index] || ({})
                readonly property bool picked: row.id === root.observed.id
                z: picked ? 1 : 0
                property real px: 0
                property real py: -31
                property real angle: 0
                property real previousProgress: 0
                property string previousId: ""
                property bool smooth: false
                onRowChanged: {
                    smooth=previousId===String(row.id || "") && Number(row.progress || 0)>=previousProgress-10
                    px=Number(row.x || 0)
                    py=Number(row.y || 0)
                    const target=-Number(row.yaw || 0)*180/Math.PI
                    angle=smooth ? angle+((target-angle+180)%360+360)%360-180 : target
                    previousProgress=Number(row.progress || 0);previousId=String(row.id || "")
                }
                visible: row.id !== undefined && (root.g.mode === "gara" || root.g.display === "tutte" || picked)
                opacity: row.status === "ritirato" ? 0.3 : row.completed ? 0.45 : 1
                x:arena.cx+px*arena.scale-width/2; y:arena.cy-py*arena.scale-height/2; width:Number(row.vehicleLength || 4.4)*arena.scale; height:Number(row.vehicleWidth || 1.8)*arena.scale
                rotation:angle
                Behavior on px { enabled:car.visible && car.smooth && root.g.runState === "running" && root.ctx.motionPolicy.mode === "normal"; NumberAnimation { duration:40; easing.type:Easing.Linear } }
                Behavior on py { enabled:car.visible && car.smooth && root.g.runState === "running" && root.ctx.motionPolicy.mode === "normal"; NumberAnimation { duration:40; easing.type:Easing.Linear } }
                Behavior on angle { enabled:car.visible && car.smooth && root.g.runState === "running" && root.ctx.motionPolicy.mode === "normal"; NumberAnimation { duration:40; easing.type:Easing.Linear } }
                Rectangle { anchors.fill:parent; anchors.margins:-Math.min(2,.3*arena.scale); radius:parent.height*.3; color:"transparent";border.width:1;border.color:root.accent;visible:car.picked }
                Rectangle { anchors.fill:parent;radius:parent.height*.2;color:car.picked ? root.accent : root.ink; border.color:root.muted; border.width:Math.min(1,.08*arena.scale) }
                Rectangle { x:parent.width*0.58;y:parent.height*.12;width:parent.width*0.24;height:parent.height*.76;radius:parent.height*.1;color:root.visual ? root.visual.surface : "black" }
                Rectangle { x:parent.width*.15;y:-parent.height*.08;width:parent.width*.18;height:parent.height*.12;color:root.muted }
                Rectangle { x:parent.width*.15;y:parent.height*.96;width:parent.width*.18;height:parent.height*.12;color:root.muted }
                Text { visible:car.picked || root.g.mode !== "impara";x:-3;y:-25;width:parent.width+6;text:String(car.row.number || "")+(car.row.ghost ? "×" : "");color:root.ink;font.family:root.numberFont;font.pixelSize:16;horizontalAlignment:Text.AlignHCenter;rotation:-car.rotation }
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
                    readonly property var attempt:root.cars[index] || ({})
                    width:12;height:12;radius:6
                    color:index===root.selected ? root.accent : root.ink
                    opacity:index===root.selected ? 1 : attempt.completed ? 0.2 : 0.55
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
                    readonly property var modelData:root.cars[index] || ({})
                    visible:modelData.id !== undefined
                    width:modelData.id===root.observed.id ? 5 : 3;height:width;radius:width/2
                    x:minimap.mx+Number(modelData.x || 0)*minimap.mapScale-width/2
                    y:minimap.my-Number(modelData.y || 0)*minimap.mapScale-height/2
                    color:modelData.id===root.observed.id ? root.accent : root.ink
                }
            }
        }
        Item {
            id: sensors
            anchors.fill: parent
            visible:root.g.display === "sensori" && root.cars.length>0
            readonly property var distances:root.scene.sensors || []
            readonly property var angles:[-1.2,-0.6,0,0.6,1.2]
            Repeater {
                model:sensors.visible ? Math.min(5,sensors.distances.length) : 0
                delegate:Item {
                    required property int index
                    x:arena.cx+Number(root.observed.x || 0)*arena.scale
                    y:arena.cy-Number(root.observed.y || 0)*arena.scale
                    rotation:-(Number(root.observed.yaw || 0)+sensors.angles[index])*180/Math.PI
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
        Text { x:16;y:0;width:180;height:root.meta.presentation === "population" ? 28 : 48;text:root.meta.presentation === "population" ? "Gen. "+root.meta.generation : root.meta.presentation === "preview" || root.meta.presentation === "verification" ? root.meta.exercise || "Guida" : ({impara:"Impara",gara:"Gara",prova:"Prova",campione:"Campione"})[root.g.mode] || "Pronto";color:root.ink;font.family:root.uiFont;font.pixelSize:22*root.factor;verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight }
        Text { x:16;y:28;width:180;height:16;visible:root.meta.presentation === "population";text:root.meta.exercise || "";color:root.muted;font.family:root.uiFont;font.pixelSize:12*root.factor;elide:Text.ElideRight }
        Text { x:200;y:0;width:root.width-540;height:48;text:root.selectedTelemetry;color:root.ink;font.family:root.uiFont;font.pixelSize:21*root.factor;verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight }
        Text { x:root.width-330;y:0;width:185;height:48;text:root.g.runState === "paused" ? "In pausa" : root.g.runState === "error" ? "Interrotta" : root.g.runState === "starting" ? "Avvio" : root.g.runState === "pausing" ? "Attendi" : root.meta.countdown > 0 ? "Partenza "+Math.ceil(root.meta.countdown) : root.g.mode === "gara" ? "G"+Math.min(root.meta.laps || 3,(root.observed.lap || 0)+1)+" · P"+(root.observed.position || "—") : root.g.mode === "impara" ? root.meta.presentation === "preview" && root.meta.previewState !== "running" ? root.meta.previewState : root.meta.phase === "familiarizzazione" ? "Verifica base" : root.meta.phase === "consolidamento" ? "Consolida base" : root.meta.phase === "ripasso" ? "Ripasso" : root.meta.phase === "valutazione" ? "Valutazione" : root.meta.phase === "aggiornamento" ? "Aggiorna rete" : root.meta.presentation === "population" ? root.meta.completedAttempts+"/"+root.meta.trainingCount+" conclusi" : root.meta.curriculumPhase || "Controllo" : root.g.mode === "prova" ? (root.meta.evaluationIndex || 0)+"/"+(root.meta.evaluationTotal || 0) : root.g.runState === "finished" ? "Conclusa" : "";color:root.muted;font.family:root.numberFont;font.pixelSize:19*root.factor;verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight }
        Text { x:root.width-135;y:0;width:120;height:48;text:root.g.controlMode === "simulation" ? "5 Pausa" : "5 Start";color:root.accent;font.family:root.uiFont;font.pixelSize:21*root.factor;verticalAlignment:Text.AlignVCenter;horizontalAlignment:Text.AlignRight }
        MouseArea { anchors.fill:parent;onClicked:root.action(root.g.controlMode === "simulation" ? "game.pause" : "game.start") }
    }
    Item {
        visible:!root.track && !root.menu
        anchors.fill:parent
        anchors.margins:root.menu || root.ctx && root.ctx.contentId === "game.driver.details" ? 32 : 0
        Text { x:0;y:8;width:parent.width;height:44;text:root.menu ? "GIOCO" : root.leaderboard ? "CLASSIFICA" : root.progress ? "PROGRESSI" : "PILOTI";color:root.ink;font.family:root.uiFont;font.pixelSize:30*root.factor;verticalAlignment:Text.AlignVCenter }
        Text { x:0;y:56;width:parent.width;height:48;text:root.leaderboard ? (root.ctx.section === "trial" ? "Prova standard · " : "Ultima gara · ")+((root.g.configuration || {}).track || {}).name+" · "+((root.g.leaderboard || {})[root.ctx.section === "trial" ? "trialPhysics" : "racePhysics"] || "") : root.g.selectedDriverName || "";color:root.muted;font.family:root.uiFont;font.pixelSize:22*root.factor;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter }
        Row {
            x:parent.width-300;y:22;spacing:24;visible:root.leaderboard
            Repeater { model:["Gare","Prova standard"];delegate:Text {
                required property string modelData
                required property int index
                text:modelData;color:(index===0 ? root.ctx.section === "race" : root.ctx.section === "trial") ? root.accent : root.muted;font.family:root.uiFont;font.pixelSize:22*root.factor
                MouseArea { anchors.fill:parent;onClicked:root.action("game.option.activate",index===0 ? "category:race" : "category:trial") }
            } }
        }
        Text {
            objectName:"gameTrackRecords"
            x:0;y:108;width:parent.width;height:36;visible:root.leaderboard
            readonly property var records:(root.g.leaderboard || {})[root.ctx.section === "trial" ? "trialRecords" : "raceRecords"] || ({})
            text:"Giro "+root.timeText(records.bestLap ? records.bestLap.value : null)+(records.bestLap ? " · "+records.bestLap.name : "")+"     V max "+(records.maxSpeed ? Math.round(records.maxSpeed.value*3.6)+" km/h · "+records.maxSpeed.name : "—")
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
            readonly property var evaluations:(root.trainingProgress.evaluations || []).filter(row=>!root.trainingProgress.academy || row.phaseId===root.trainingProgress.phaseId)
            readonly property var latest:evaluations[evaluations.length-1] || ({})
            readonly property var champion:root.trainingProgress.champion || ({})
            readonly property var firstQualification:root.trainingProgress.baseline || ({})
            readonly property var points:evaluations.filter(row=>row.time!==null && row.valid>=Math.ceil(.9*row.total)).map(row=>({x:row.round,y:row.time}))
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
            Text { x:24;y:164;width:parent.width-48;visible:chart.points.length<2;text:chart.evaluations.length ? "Ultima prova: "+(chart.latest.valid || 0)+"/"+(chart.latest.total || 10)+" valide\nServono due prove affidabili per il grafico" : "Le prove misurano tempi e validità dopo Start";color:root.muted;font.family:root.uiFont;font.pixelSize:21*root.factor;horizontalAlignment:Text.AlignHCenter;wrapMode:Text.Wrap }
            Text { x:0;y:340;width:parent.width;height:42;text:root.trainingProgress.verified ? "Campione · "+(chart.champion.valid || 0)+"/"+(chart.champion.total || 10)+" · mediana "+root.timeText(chart.champion.median)+" · migliore "+root.timeText(chart.champion.best) : chart.driver.hasPolicy ? "Modello precedente · qualifica del campione da completare" : "Campione da qualificare · ultima prova "+(chart.latest.valid || 0)+"/"+(chart.latest.total || 10);color:root.ink;font.family:root.numberFont;font.pixelSize:21*root.factor;elide:Text.ElideRight }
            Text { x:0;y:390;width:parent.width;height:36;text:root.trainingProgress.verified && chart.firstQualification.median ? "Prima qualifica "+root.timeText(chart.firstQualification.median)+(root.trainingProgress.promotionGain!==null ? " · guadagno ultima promozione "+Number(root.trainingProgress.promotionGain).toFixed(2)+" s" : "") : "Il candidato può cambiare; il campione richiede prove comparabili";color:root.muted;font.family:root.uiFont;font.pixelSize:19*root.factor;elide:Text.ElideRight }
        }
        Text { visible:!root.menu && !root.progress;x:0;y:parent.height-46;width:parent.width;height:42;text:root.g.message || "";color:root.muted;font.family:root.uiFont;font.pixelSize:19*root.factor;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter }
    }
    Loader {
        anchors.fill:parent
        active:root.menu
        sourceComponent:Component { GameSettingsVisual { ctx:root.ctx } }
    }
}
