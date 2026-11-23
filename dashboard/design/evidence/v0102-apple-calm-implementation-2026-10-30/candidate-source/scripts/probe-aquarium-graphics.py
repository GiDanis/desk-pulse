#!/usr/bin/env python3
"""Bounded display diagnostic. Run only while the kiosk is stopped externally."""
import argparse
import json
import os
from pathlib import Path
import time

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--surface', choices=('baseline', 'es3'), required=True)
p.add_argument('--seconds', type=float, default=8)
p.add_argument('--label', default='A')
p.add_argument('--scene', choices=('pattern', 'cube'), default='pattern')
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

app = QGuiApplication([])
if a.surface == 'es3':
    fmt = QSurfaceFormat()
    fmt.setRenderableType(QSurfaceFormat.OpenGLES)
    fmt.setVersion(3, 0)
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setSamples(0)
    QSurfaceFormat.setDefaultFormat(fmt)
qml = '''import QtQuick
Window {
 width:960;height:640;visible:true;color:"#172e37"
 Row { y:100;width:960;height:400
  Repeater { model:["#d94040","#46c46a","#427cdd","#f0cb42"]
   Rectangle { required property string modelData;width:240;height:400;color:modelData
    Rectangle {x:20;y:20;width:200;height:360;color:"transparent";border.width:3;border.color:"white"}
   }
  }
 }
 Text {x:32;y:20;text:"CASE_LABEL · Qt Quick · 960×640";color:"white";font.pixelSize:36}
 Rectangle {y:535;width:70;height:70;color:"white";radius:8
  SequentialAnimation on x {loops:Animation.Infinite;NumberAnimation{from:20;to:870;duration:1500}NumberAnimation{from:870;to:20;duration:1500}}
 }
 SCENE
}'''.replace('CASE_LABEL', a.label)
if a.scene == 'cube':
    qml = qml.replace('import QtQuick', 'import QtQuick\nimport QtQuick3D', 1)
    scene = '''View3D {anchors.fill:parent
      environment:SceneEnvironment {backgroundMode:SceneEnvironment.Transparent;antialiasingMode:SceneEnvironment.NoAA}
      PerspectiveCamera {id:cam;z:500} camera:cam
      DirectionalLight {eulerRotation.x:-30;eulerRotation.y:-30}
      Model {source:"#Cube";materials:PrincipledMaterial{baseColor:"#e89346"}
       NumberAnimation on eulerRotation.y {from:0;to:360;duration:4000;loops:Animation.Infinite}
      }
    }'''
else:
    scene = ''
qml = qml.replace('SCENE', scene)
engine = QQmlApplicationEngine()
engine.loadData(qml.encode(), QUrl('file:///smartpc-graphics-probe.qml'))
if not engine.rootObjects():
    raise SystemExit('Probe QML failed')
window = engine.rootObjects()[0]
started = time.monotonic()
QTimer.singleShot(int(a.seconds * 1000), app.quit)
app.exec()
fmt = window.format()
report = {'label': a.label, 'scene': a.scene, 'surface': a.surface,
          'seconds': time.monotonic() - started,
          'requestedDefault': [QSurfaceFormat.defaultFormat().majorVersion(), QSurfaceFormat.defaultFormat().minorVersion()],
          'windowFormat': {'version': [fmt.majorVersion(), fmt.minorVersion()],
                           'type': str(fmt.renderableType()), 'depth': fmt.depthBufferSize(),
                           'stencil': fmt.stencilBufferSize(), 'samples': fmt.samples()},
          'rhi': str(window.rendererInterface().graphicsApi()),
          'nativeProbeExpected': os.environ.get('SMARTPC_GL_PROBE_FILE')}
(a.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
window.close()
