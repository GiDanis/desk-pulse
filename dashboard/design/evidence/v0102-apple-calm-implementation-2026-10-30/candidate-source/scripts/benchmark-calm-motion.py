#!/usr/bin/env python3
"""Isolated Qt Quick A/B/BA motion benchmark, never an optical FPS proof.

Uses synthetic cards/banner and local fonts. Run on the target graphics backend.
No providers, configuration or user data are touched.
"""
import argparse,json,os,platform,statistics,time
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=float,default=7);a=p.parse_args()
from PySide6.QtCore import QUrl,QTimer,Qt,qVersion
from PySide6.QtGui import QGuiApplication,QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
app=QGuiApplication([]);engine=QQmlApplicationEngine()
for font in (Path(__file__).resolve().parents[1]/'theme-projects/apple-calm/bundle/fonts').glob('*tf'):QFontDatabase.addApplicationFont(str(font))
qml='''import QtQuick
import QtQuick.Window
Window {
 id:root;width:960;height:640;visible:true;color:"#F3F4F6"
 property string recipe:"property"
 readonly property bool animating:prop.running || anim.running
 property bool rising:false
 property real progress:0
 Repeater { model:6;delegate:Rectangle { required property int index;x:24+(index%3)*310;y:72+Math.floor(index/3)*244;width:292;height:224;radius:24;color:"#FFFFFF"
 Text {x:20;y:20;text:"Temperatura · dati sintetici";font.pixelSize:24;font.family:"Cantarell";color:"#5D626C"}
 Text {x:20;y:68;text:parent.index===0 ? "21,4 °C" : "Dato di esempio";font.pixelSize:parent.index===0 ? 52 : 30;font.family:"Cantarell";color:"#1D1D1F"}
 }}
 Rectangle { id:banner;x:32;y:472;width:896;height:152;radius:24;color:"#FFFFFF";opacity:1
 Text {x:24;y:14;text:"Meteo · esempio · 18:40";font.pixelSize:22;font.family:"Cantarell";color:"#5D626C"}
 Text {x:24;y:48;text:"Aggiornamento della fonte";font.pixelSize:30;font.family:"Cantarell";color:"#1D1D1F"}
 Text {x:24;y:98;text:"Avviso sintetico per la misura del movimento";font.pixelSize:24;font.family:"Cantarell";color:"#5D626C"}
 }
 NumberAnimation {id:prop;target:banner;property:"opacity";duration:120;to:root.rising ? 1 : 0.35;easing.type:Easing.OutCubic}
 OpacityAnimator {id:anim;target:banner;duration:120;to:root.rising ? 1 : 0.35;easing.type:Easing.OutCubic}
 Timer {interval:160;running:true;repeat:true;onTriggered:{root.rising=!root.rising;if(root.recipe==="property")prop.restart();else anim.restart()}}
}'''
engine.loadData(qml.encode(),QUrl('file:///calm-motion-benchmark.qml'));assert engine.rootObjects();window=engine.rootObjects()[0]
blocks=[];samples=[];last=None;began=time.monotonic();index=-1;cpu_start=time.process_time();sequence=['property','animator','animator','property']
def swap():
 global index,last,began,samples,cpu_start
 if index>=0:
  ordered=sorted(samples)
  blocks.append({'recipe':sequence[index],'intervals':len(samples),'meanMs':statistics.mean(samples) if samples else None,'p95Ms':ordered[int(.95*(len(ordered)-1))] if samples else None,'p99Ms':ordered[int(.99*(len(ordered)-1))] if samples else None,'maxMs':max(samples) if samples else None,'cpuSeconds':time.process_time()-cpu_start})
 index+=1
 if index==len(sequence):app.quit();return
 samples=[];last=None;began=time.monotonic();cpu_start=time.process_time();window.setProperty('recipe',sequence[index]);QTimer.singleShot(int(a.seconds*1000),swap)
def frame():
 global last
 now=time.monotonic()
 if index<0 or now-began<1 or not window.property('animating'):last=None;return
 if last is not None:samples.append((now-last)*1000)
 last=now
window.frameSwapped.connect(frame,Qt.QueuedConnection);QTimer.singleShot(500,swap);app.exec()
report={'scope':'Synthetic Qt Quick window; queued frame-swapped callback intervals during animation, not optical frames/GPU execution time/USB latency/full dashboard qualification','qt':qVersion(),'machine':platform.machine(),'platform':os.environ.get('QT_QPA_PLATFORM','default'),'requestedBackend':os.environ.get('QSG_RHI_BACKEND','default'),'graphicsApi':str(QQuickWindow.graphicsApi()),'sequence':'ABBA','secondsPerBlock':a.seconds,'blocks':blocks,'decision':'Retain existing NumberAnimation pending benefit and semantic equivalence in the actual dashboard; this microbenchmark alone does not authorize a global change.'}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
