"""Create private source copies; only the experimental visual is replaced."""
import argparse,shutil,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);a=p.parse_args();HERE=Path(__file__).resolve().parent
a.stage.mkdir(exist_ok=True,parents=True)
for name in ('source2d','source3d'):
 dest=a.stage/name/'dashboard';shutil.copytree(a.baseline,dest,ignore=shutil.ignore_patterns('__pycache__','.git'))
m=json.loads((a.baseline/'release-manifest.json').read_text());assert m['version']=='0.10.0-rc.2'
assert all(hashlib.sha256((a.baseline/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
q=a.stage/'source3d/dashboard/presentations/aquarium';s=(q/'AquariumVisual.qml').read_text().replace('import QtQuick\n','import QtQuick\nimport QtQuick3D\nimport AquariumBench 1.0\n',1).replace('const item=fishItems.itemAt(i) as FishRig','const item=fishItems.itemAt(i)')
start=s.index('        delegate:FishRig {');end=s.index('    FrameAnimation',start)
s=s[:start]+'''        delegate:Item {
            required property var modelData
            required property int index
            readonly property var species:root.speciesRows.find(row=>row.id===modelData.speciesId) || ({})
            property real phase:0
            property real facing:1
            property real tilt:0
            property int tickCount:0
            readonly property bool partsReady:true
            readonly property bool partsFailed:false
            width:(species.referenceSize || 100)*(modelData.depth===0 ? .82:modelData.depth===2 ? 1.12:1)
            height:width*.64
        }
    }
    property int benchmarkAA:0
    property real benchmarkResolution:1
    readonly property var sceneStats:scene.renderStats
    View3D {
        id:scene;objectName:"aquariumView3D";anchors.fill:parent
        explicitTextureWidth:Math.round(root.width*root.benchmarkResolution)
        explicitTextureHeight:Math.round(root.height*root.benchmarkResolution)
        renderMode:View3D.Offscreen
        environment:SceneEnvironment {
            backgroundMode:SceneEnvironment.Transparent
            antialiasingMode:root.benchmarkAA ? SceneEnvironment.MSAA:SceneEnvironment.NoAA
            antialiasingQuality:SceneEnvironment.High
            tonemapMode:SceneEnvironment.TonemapModeLinear
        }
        camera:camera
        PerspectiveCamera {id:camera;z:1000;clipNear:1;clipFar:4000;fieldOfView:2*Math.atan(root.height/2000)*180/Math.PI;fieldOfViewOrientation:PerspectiveCamera.Vertical}
        DirectionalLight {eulerRotation:Qt.vector3d(-35,-30,0);brightness:1;ambientColor:"#69848a";castsShadow:false}
        DirectionalLight {eulerRotation:Qt.vector3d(35,150,0);brightness:.45;castsShadow:false}
        Node {
            BodyGeometry {id:bodyShape}
            EyeGeometry {id:eyeShape}
            TailGeometry {id:tailShape}
            FinGeometry {id:finShape}
            PrincipledMaterial {id:goldBody;baseColor:"#edb15f";roughness:.7;metalness:0;specularAmount:.2}
            PrincipledMaterial {id:tealBody;baseColor:"#52a9b5";roughness:.7;metalness:0;specularAmount:.2}
            PrincipledMaterial {id:goldFin;baseColor:"#f4c883";roughness:.8;metalness:0}
            PrincipledMaterial {id:tealFin;baseColor:"#b0cba1";roughness:.8;metalness:0}
            PrincipledMaterial {id:eyeMat;baseColor:"#fff7df";roughness:.5;metalness:0}
            PrincipledMaterial {id:pupilMat;baseColor:"#14262b";roughness:.35;metalness:0}
            Repeater3D {
                model:root.rows
                delegate:Fish3D {
                    required property var modelData
                    required property int index
                    readonly property var pose:{root.readinessRevision;return fishItems.itemAt(index)}
                    readonly property real depthZ:(modelData.depth-1)*50
                    readonly property real perspectiveScale:(1000-depthZ)/1000
                    x:pose ? (pose.x+pose.width/2-root.width/2)*perspectiveScale:0
                    y:pose ? (root.height/2-pose.y-pose.height/2)*perspectiveScale:0
                    z:depthZ
                    scale:Qt.vector3d(1,1,1).times((pose ? pose.width:100)/109*perspectiveScale)
                    eulerRotation:Qt.vector3d(0,pose ? Math.acos(Math.max(-1,Math.min(1,pose.facing)))*180/Math.PI+Math.sin(pose.phase*.3)*12:0,pose ? -pose.tilt:0)
                    phase:pose ? pose.phase:0
                    bodyGeometry:bodyShape;eyeGeometry:eyeShape;tailGeometry:tailShape;finGeometry:finShape
                    bodyMaterial:modelData.speciesId==="gold" ? goldBody:tealBody
                    finMaterial:modelData.speciesId==="gold" ? goldFin:tealFin
                    eyeMaterial:eyeMat;pupilMaterial:pupilMat
                }
            }
        }
    }
''' +s[end:]
(q/'AquariumVisual.qml').write_text(s);shutil.copy2(HERE/'Fish3D.qml',q/'Fish3D.qml')
(a.stage/'source-proof.json').write_text(json.dumps({'baselineVersion':m['version'],'baselineFiles':len(m['sha256']),'baselineManifestSha256':hashlib.sha256((a.baseline/'release-manifest.json').read_bytes()).hexdigest(),'experimentalDelta':['presentations/aquarium/AquariumVisual.qml','presentations/aquarium/Fish3D.qml'],'source3dVisualSha256':hashlib.sha256((q/'AquariumVisual.qml').read_bytes()).hexdigest(),'productionModified':False},indent=2)+'\n')
print('PREPARED',a.stage)
