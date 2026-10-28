from pathlib import Path
import json,hashlib
H=Path('/var/lib/smartpc-dashboard');baseline=H/'smartpc-overtake-baseline/dashboard';source=H/'smartpc-overtake-project/dashboard'
# Diagnostic additions only: old control/physics/presenter kept verbatim.
p=baseline/'presentations/GameVisual.qml';s=p.read_text().replace('    id: root\n','    id: root\n    objectName: "gameVisual"\n    signal posePresented(var sample)\n',1)
s=s.replace('    property var presentationTrace: []','    property var presentationTrace: []\n    property bool tracing: false')
s=s.replace('        const sample={presentedMs:','        const sample={poseSampleMs:selectedCar ? selectedCar.poseSampleMs : 0,poseFromMs:selectedCar ? selectedCar.poseFromMs : 0,poseToMs:selectedCar ? selectedCar.poseToMs : 0,poseAlpha:selectedCar ? selectedCar.poseAlpha : 0,receivedMs:Number(scene.receivedMs || 0),consumedMs:consumedMs,presentedMs:')
s=s.replace('        presentationTrace.push(sample)','        if (tracing) posePresented(sample)\n        presentationTrace.push(sample)')
s=s.replace('    property real renderNow: 0','    property real renderNow: 0\n    property real consumedMs: 0').replace('            consumedScene=next','            consumedScene=next\n            consumedMs=now')
s=s.replace('                property var samples: []','                property var samples: []\n                property real poseSampleMs: 0\n                property real poseFromMs: 0\n                property real poseToMs: 0\n                property real poseAlpha: 0')
s=s.replace('                    px=a.x+(b.x-a.x)*alpha;', '                    poseFromMs=a.t;poseToMs=b.t;poseAlpha=alpha;poseSampleMs=a.t+(b.t-a.t)*alpha\n                    px=a.x+(b.x-a.x)*alpha;')
p.write_text(s)
p=baseline/'game.py';s=p.read_text().replace('            self._scene=newest;',"            newest['receivedMs']=time.monotonic()*1000\n            self._scene=newest;");p.write_text(s)
# Fresh diagnostic harness is shared; old source is identified by hashes.
for root in (source,baseline):
 m=root/'release-manifest.json';data=json.loads(m.read_text())
 data['sha256']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='release-manifest.json'}
 m.write_text(json.dumps(data,indent=2)+'\n')
(H/'v09-overtake-proof/baseline-instrumentation.json').write_text(json.dumps(dict(version='rc21 + diagnostic hooks only',changed=['presentations/GameVisual.qml','game.py'],sourceHashes={f:hashlib.sha256((baseline/f).read_bytes()).hexdigest() for f in ('game.py','presentations/GameVisual.qml','game_control.py','game_academy.py','game_rewards.py','game_presentation.py')}),indent=2))
