import QtQuick

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
    function action(id,target,args) { if (ctx && ctx.lifecycle.interactive) ctx.requestAction(id,target || "",args || {}) }
    function timeText(value) { return value === null || value === undefined ? "—" : Number(value).toFixed(2)+" s" }
    function detail(row) {
        if (menu) return row.detail || ""
        if (leaderboard) return (row.valid !== undefined ? row.valid+"/5 · "+timeText(row.time) : row.status+" · "+timeText(row.finishTime))+(row.previous ? " · modello precedente" : "")
        return (row.algorithm || "")+" · "+(row.verified ? "Campione verificato" : row.hasPolicy ? "Modello precedente" : row.hasCandidate ? "Allenamento salvato" : "Da allenare")+" · "+(row.steps || 0)+" passi"
    }

    Rectangle {
        anchors.fill:parent
        visible:root.menu || root.ctx && root.ctx.contentId === "game.driver.details"
        color:root.visual ? root.visual.background : "#101820"
    }

    Item {
        id: arena
        visible: root.track
        width: root.width; height: root.height-56
        clip: true
        readonly property real scale: Math.min(width/152,height/82.6666667)
        readonly property real cx: width/2
        readonly property real cy: height/2
        Rectangle {
            anchors.fill: parent
            radius: root.visual ? root.visual.radiusCard : 24
            color: root.visual ? root.visual.surface : "#202228"
            border.color: root.visual ? root.visual.border : "gray"
            border.width: 1
        }
        Rectangle {
            objectName: "gameOvalRoad"
            width:144*arena.scale; height:72*arena.scale; radius:height/2
            anchors.centerIn: parent
            color: root.visual ? root.visual.background : "#11151b"
            border.color: root.muted; border.width:2
        }
        Rectangle {
            width:134*arena.scale; height:62*arena.scale; radius:height/2
            anchors.centerIn: parent; color:"transparent"
            border.color:root.muted; border.width:1; opacity:0.28
        }
        Rectangle {
            width:124*arena.scale; height:52*arena.scale; radius:height/2
            anchors.centerIn: parent
            color:root.visual ? root.visual.surface : "#202228"
            border.color:root.muted; border.width:2
        }
        Repeater {
            model: 10
            delegate: Rectangle {
                required property int index
                x:arena.cx-3; y:arena.cy+26*arena.scale+index*arena.scale
                width:6; height:arena.scale
                color:index%2 ? root.muted : root.ink; opacity:0.65
            }
        }
        Repeater {
            model: 8
            delegate: Item {
                id: car
                required property int index
                readonly property var row: root.cars[index] || ({})
                readonly property bool picked: row.id === root.observed.id
                property real px: arena.cx
                property real py: arena.cy+31*arena.scale
                property real angle: 0
                property real previousProgress: 0
                property string previousId: ""
                property bool smooth: false
                onRowChanged: {
                    smooth=previousId===String(row.id || "") && Number(row.progress || 0)>=previousProgress-10
                    px=arena.cx+Number(row.x || 0)*arena.scale
                    py=arena.cy-Number(row.y || 0)*arena.scale
                    angle=-Number(row.yaw || 0)*180/Math.PI
                    previousProgress=Number(row.progress || 0);previousId=String(row.id || "")
                }
                visible: row.id !== undefined && (root.g.display === "tutte" || picked)
                opacity: row.status === "ritirato" ? 0.3 : 1
                x:px-width/2; y:py-height/2; width:4.4*arena.scale; height:1.8*arena.scale
                rotation:angle
                Behavior on px { enabled:car.smooth && root.g.runState === "running" && root.ctx.motionPolicy.mode === "normal"; NumberAnimation { duration:40; easing.type:Easing.Linear } }
                Behavior on py { enabled:car.smooth && root.g.runState === "running" && root.ctx.motionPolicy.mode === "normal"; NumberAnimation { duration:40; easing.type:Easing.Linear } }
                Behavior on angle { enabled:car.smooth && root.g.runState === "running" && root.ctx.motionPolicy.mode === "normal"; NumberAnimation { duration:40; easing.type:Easing.Linear } }
                Rectangle { anchors.fill:parent; anchors.margins:-5; radius:9; color:"transparent";border.width:2;border.color:root.accent;visible:car.picked }
                Rectangle { anchors.fill:parent;radius:3;color:car.picked ? root.accent : root.ink; border.color:root.muted; border.width:1 }
                Rectangle { x:parent.width*0.58;y:1;width:parent.width*0.24;height:parent.height-2;radius:2;color:root.visual ? root.visual.surface : "black" }
                Rectangle { x:4;y:-1;width:7;height:2;color:root.muted }
                Rectangle { x:4;y:parent.height-1;width:7;height:2;color:root.muted }
                Text { visible:car.picked || root.g.mode !== "impara";x:-3;y:-25;width:parent.width+6;text:String(car.row.number || "");color:root.ink;font.family:root.numberFont;font.pixelSize:16;horizontalAlignment:Text.AlignHCenter;rotation:-car.rotation }
            }
        }
        Canvas {
            id: sensors
            anchors.fill: parent
            visible:root.g.display === "sensori" && root.cars.length>0
            onVisibleChanged:requestPaint()
            Connections { target: root; function onSceneChanged() { sensors.requestPaint() } }
            onPaint: {
                const c=getContext("2d");c.clearRect(0,0,width,height)
                if (!visible) return
                const row=root.observed,dist=root.scene.sensors || [],angles=[-1.2,-0.6,0,0.6,1.2]
                const x=arena.cx+Number(row.x || 0)*arena.scale,y=arena.cy-Number(row.y || 0)*arena.scale
                c.strokeStyle=root.accent;c.lineWidth=1;c.globalAlpha=0.6
                for (let i=0;i<Math.min(5,dist.length);i++) { const a=Number(row.yaw || 0)+angles[i],r=dist[i]*50*arena.scale;c.beginPath();c.moveTo(x,y);c.lineTo(x+Math.cos(a)*r,y-Math.sin(a)*r);c.stroke() }
            }
        }
        Text {
            anchors.centerIn:parent; width:350;height:100
            visible:root.cars.length===0
            text:root.g.available === false ? root.g.message : root.g.selectedDriverName || "Scegli un pilota"
            color:root.muted;font.family:root.uiFont;font.pixelSize:28*root.factor
            horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter
        }
    }
    Rectangle {
        visible:root.track
        x:0;y:root.height-48;width:root.width;height:48
        radius:root.visual ? root.visual.radiusRow : 12
        color:root.visual ? root.visual.surface : "#202228"
        Text { x:16;y:0;width:180;height:48;text:({impara:"Impara",gara:"Gara",prova:"Prova",campione:"Campione"})[root.g.mode] || "Pronto";color:root.ink;font.family:root.uiFont;font.pixelSize:22*root.factor;verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight }
        Text { x:200;y:0;width:root.width-540;height:48;text:root.selectedName;color:root.ink;font.family:root.uiFont;font.pixelSize:21*root.factor;verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight }
        Text { x:root.width-330;y:0;width:185;height:48;text:root.g.runState === "paused" ? "In pausa" : root.g.runState === "error" ? "Interrotta" : root.g.runState === "starting" ? "Avvio" : root.g.runState === "pausing" ? "Attendi" : root.meta.countdown > 0 ? "Partenza "+Math.ceil(root.meta.countdown) : root.g.mode === "gara" ? "G"+Math.min(3,(root.observed.lap || 0)+1)+" · P"+(root.observed.position || "—") : root.g.mode === "impara" ? root.meta.phase === "valutazione" ? "Valutazione" : root.meta.curriculumPhase || "Controllo" : root.g.mode === "prova" ? (root.meta.evaluationIndex || 0)+"/"+(root.meta.evaluationTotal || 0) : root.g.runState === "finished" ? "Conclusa" : "";color:root.muted;font.family:root.numberFont;font.pixelSize:19*root.factor;verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight }
        Text { x:root.width-135;y:0;width:120;height:48;text:root.g.controlMode === "simulation" ? "5 Pausa" : "5 Start";color:root.accent;font.family:root.uiFont;font.pixelSize:21*root.factor;verticalAlignment:Text.AlignVCenter;horizontalAlignment:Text.AlignRight }
        MouseArea { anchors.fill:parent;onClicked:root.action(root.g.controlMode === "simulation" ? "game.pause" : "game.start") }
    }
    Item {
        visible:!root.track
        anchors.fill:parent
        anchors.margins:root.menu || root.ctx && root.ctx.contentId === "game.driver.details" ? 32 : 0
        Text { x:0;y:8;width:parent.width;height:44;text:root.menu ? "GIOCO" : root.leaderboard ? "CLASSIFICA" : root.progress ? "PROGRESSI" : "PILOTI";color:root.ink;font.family:root.uiFont;font.pixelSize:30*root.factor;verticalAlignment:Text.AlignVCenter }
        Text { x:0;y:56;width:parent.width;height:48;text:root.menu ? root.g.message || "Configura da fermo" : root.leaderboard ? (root.ctx.section === "trial" ? "Prova standard · ovale asciutto" : "Ultima gara · ovale asciutto") : root.g.selectedDriverName || "";color:root.muted;font.family:root.uiFont;font.pixelSize:22*root.factor;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter }
        Row {
            x:0;y:110;spacing:24;visible:root.leaderboard
            Repeater { model:["Gare","Prova standard"];delegate:Text {
                required property string modelData
                required property int index
                text:modelData;color:(index===0 ? root.ctx.section === "race" : root.ctx.section === "trial") ? root.accent : root.muted;font.family:root.uiFont;font.pixelSize:22*root.factor
                MouseArea { anchors.fill:parent;onClicked:root.action("game.option.activate",index===0 ? "category:race" : "category:trial") }
            } }
        }
        Repeater {
            model:root.progress ? 0 : Math.min(root.pageSize,root.rows.length)
            delegate:Rectangle {
                id:listRow
                required property int index
                readonly property int realIndex:Math.floor(root.ctx.selectedIndex/root.pageSize)*root.pageSize+index
                readonly property var row:root.rows[realIndex] || ({})
                objectName: "gameListRow"+realIndex
                x:0;y:(root.leaderboard ? 160 : root.menu ? 104 : 120)+index*(root.menu ? root.pageSize===4 ? 104 : 88 : 82);width:parent.width;height:root.menu ? root.pageSize===4 ? 94 : 80 : 72
                visible:row.id !== undefined
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
            readonly property var evaluations:root.trainingProgress.evaluations || []
            readonly property var latest:evaluations[evaluations.length-1] || ({})
            readonly property var champion:root.trainingProgress.champion || ({})
            readonly property var firstQualification:root.trainingProgress.baseline || ({})
            readonly property var points:evaluations.filter(row=>row.time!==null && row.valid>=9).map(row=>({x:row.round,y:row.time}))
            Text { x:0;y:0;width:parent.width;height:42;text:(root.trainingProgress.phase || "Da allenare")+" · "+(chart.driver.steps || 0)+" passi · "+Math.round((chart.driver.seconds || 0)/60)+" min";color:root.ink;font.family:root.numberFont;font.pixelSize:24*root.factor;verticalAlignment:Text.AlignVCenter }
            Rectangle { x:0;y:58;width:parent.width;height:260;radius:root.visual ? root.visual.radiusCard : 24;color:root.visual ? root.visual.surface : "#202228" }
            Canvas {
                id: plot
                x:24;y:94;width:parent.width-48;height:190
                Connections { target:chart;function onPointsChanged() { plot.requestPaint() } }
                onVisibleChanged:requestPaint()
                onPaint: {
                    const c=getContext("2d"),p=chart.points;c.clearRect(0,0,width,height)
                    if (p.length<2) return
                    let lo=Math.min(...p.map(v=>v.y)),hi=Math.max(...p.map(v=>v.y)),first=p[0].x,last=p[p.length-1].x
                    c.strokeStyle=root.accent;c.lineWidth=2;c.beginPath()
                    for (let i=0;i<p.length;i++) { const x=(p[i].x-first)/Math.max(1,last-first)*width,y=height-8-(p[i].y-lo)/Math.max(0.001,hi-lo)*(height-16);if(i)c.lineTo(x,y);else c.moveTo(x,y) }c.stroke()
                }
            }
            Text { x:24;y:62;width:parent.width-48;height:28;text:"Tempo mediano · prove con almeno 9/10 giri validi";color:root.muted;font.family:root.uiFont;font.pixelSize:18*root.factor }
            Text { x:24;y:164;width:parent.width-48;visible:chart.points.length<2;text:chart.evaluations.length ? "Ultima prova: "+(chart.latest.valid || 0)+"/10 giri validi\nServono due prove affidabili per il grafico" : "Le prove misurano tempi e giri validi dopo Start";color:root.muted;font.family:root.uiFont;font.pixelSize:21*root.factor;horizontalAlignment:Text.AlignHCenter;wrapMode:Text.Wrap }
            Text { x:0;y:340;width:parent.width;height:42;text:root.trainingProgress.verified ? "Campione · "+(chart.champion.valid || 0)+"/10 · mediana "+root.timeText(chart.champion.median)+" · migliore "+root.timeText(chart.champion.best) : chart.driver.hasPolicy ? "Modello precedente · qualifica del campione da completare" : "Campione da qualificare · ultima prova "+(chart.latest.valid || 0)+"/10";color:root.ink;font.family:root.numberFont;font.pixelSize:21*root.factor;elide:Text.ElideRight }
            Text { x:0;y:390;width:parent.width;height:36;text:root.trainingProgress.verified && chart.firstQualification.median ? "Prima qualifica "+root.timeText(chart.firstQualification.median)+(root.trainingProgress.promotionGain!==null ? " · guadagno ultima promozione "+Number(root.trainingProgress.promotionGain).toFixed(2)+" s" : "") : "Il candidato può cambiare; il campione richiede prove comparabili";color:root.muted;font.family:root.uiFont;font.pixelSize:19*root.factor;elide:Text.ElideRight }
        }
        Text { visible:!root.menu && !root.progress;x:0;y:parent.height-46;width:parent.width;height:42;text:root.g.message || "";color:root.muted;font.family:root.uiFont;font.pixelSize:19*root.factor;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter }
    }
}
