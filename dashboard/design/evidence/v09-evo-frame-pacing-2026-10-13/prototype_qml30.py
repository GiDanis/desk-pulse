"""Diagnostic renderer only: coalesce source scenes and interpolate within QML."""
from pathlib import Path
import sys
source=Path(sys.argv[1]);target=Path(sys.argv[2]);s=source.read_text()
s=s.replace('readonly property var scene: ctx ? ctx.scene : ({})','property var scene: ({})',1)
s=s.replace('    function action(id,target,args)', '''    property real renderNow:Date.now()
    function syncScene() {
        const next=ctx ? ctx.scene : ({})
        if (!scene.sequence || next.sequence !== scene.sequence) scene=next
    }
    onCtxChanged:Qt.callLater(function() { if (!frameClock.running) root.syncScene() })
    Component.onCompleted:syncScene()
    Timer {
        id:frameClock;interval:33;repeat:true
        running:root.track && root.g.runState === "running"
        onRunningChanged:if (!running) root.syncScene()
        onTriggered: {
            root.renderNow=Date.now()
            root.syncScene()
            for (let i=0;i<vehicleItems.count;i++) {
                const car=vehicleItems.itemAt(i)
                if (car) car.advancePose(root.renderNow)
            }
        }
    }
    function action(id,target,args)''',1)
s=s.replace('        Repeater {\n            model: root.cars.length','        Repeater {\n            id:vehicleItems\n            model: root.cars.length',1)
a=s.index('                onRowChanged: {');b=s.index('                visible: row.id',a)
s=s[:a]+'''                property real targetX:0
                property real targetY:-31
                property real targetAngle:0
                property real startX:0
                property real startY:-31
                property real startAngle:0
                property real sampleAt:0
                property real sampleDuration:33
                function advancePose(now) {
                    const alpha=Math.max(0,Math.min(1,(now-sampleAt)/sampleDuration))
                    px=startX+(targetX-startX)*alpha
                    py=startY+(targetY-startY)*alpha
                    angle=startAngle+(targetAngle-startAngle)*alpha
                }
                onRowChanged: {
                    const nx=Number(row.x || 0),ny=Number(row.y || 0)
                    const na=-Number(row.yaw || 0)*180/Math.PI,now=root.renderNow
                    smooth=previousId===String(row.id || "") && Number(row.progress || 0)>=previousProgress-10
                    if (!smooth || root.g.runState !== "running") {
                        startX=targetX=px=nx;startY=targetY=py=ny;startAngle=targetAngle=angle=na
                        sampleAt=now;sampleDuration=33
                    } else if (nx !== targetX || ny !== targetY || Math.abs(((na-targetAngle+180)%360+360)%360-180)>0.000001) {
                        advancePose(now)
                        startX=px;startY=py;startAngle=angle
                        targetX=nx;targetY=ny;targetAngle=angle+((na-angle+180)%360+360)%360-180
                        sampleDuration=Math.max(33,Math.min(500,now-sampleAt));sampleAt=now
                    }
                    previousProgress=Number(row.progress || 0);previousId=String(row.id || "")
                }
'''+s[b:]
# The display clock owns camera/body poses; remove free-running 60 Hz animations.
for name in ('px','py','angle'):
 a=s.index('                Behavior on '+name);b=s.index('\n',a);s=s[:a]+s[b+1:]
for name in ('cameraX','cameraY','scale'):
 a=s.index('        Behavior on '+name);b=s.index('\n',a);s=s[:a]+s[b+1:]
target.write_text(s)
