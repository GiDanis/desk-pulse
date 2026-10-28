"""Actual Apple chart components: hidden data work and visible pixel parity.

Synthetic 2x512-point data and 200 updates. This measures component work,
not provider frequencies, complete dashboard FPS or GPU execution time.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')
from PySide6.QtCore import QUrl,QCoreApplication,QEvent
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine,QQmlExpression
from PySide6.QtQuick import QQuickWindow
import shiboken6

p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
app=QGuiApplication([]);a.output.mkdir(parents=True,exist_ok=True);rows=[]
for name in ('MiniHistory','NetworkHistoryChart'):
    engine=QQmlApplicationEngine();warnings=[];engine.warnings.connect(lambda es:warnings.extend(str(e) for e in es))
    source='''import QtQuick
import "%s" as Apple
Window {
    id:root; width:960; height:640; visible:true; color:"#F3F4F6"
    property int epoch:0
    property var counts: ({reads:0})
    property var points: ({count:512,get:function(i) { root.counts.reads++;return {time:i,value:i%%17===0 ? null : 500+400*Math.sin(i/30),breakBefore:i===250} }})
    property var series: ({count:2,get:function(i) { return {points:root.points,label:i===0 ? "Download" : "Upload",unit:"bit/s",gaps:3} }})
    property var chart: { const revision=epoch;return {series:series,start:0,end:511,period:"1 ora",previous:false,unit:"bit/s",message:"Fixture"} }
    property var visualStyle: ({border:"#CDD2DA",accent:"#0066CC",textSecondary:"#5D626C",textPrimary:"#1D1D1F",font20:20,font22:22,uiFamily:"Sans Serif",bodyWeight:400})
    Apple.%s { id:graph;objectName:"graph";x:24;y:24;width:912;height:560;chart:root.chart;visualStyle:root.visualStyle }
}''' % (a.bundle.resolve().joinpath('qml').as_uri(),name)
    engine.loadData(source.encode(),QUrl.fromLocalFile(str(a.output/'Probe.qml')))
    assert engine.rootObjects(),warnings
    root=engine.rootObjects()[0];graph=root.findChild(__import__('PySide6.QtCore',fromlist=['QObject']).QObject,'graph')
    window=shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0],QQuickWindow)
    def pump(ms=80):
        end=time.monotonic()+ms/1000
        while time.monotonic()<end:app.processEvents();time.sleep(.001)
    def reads():
        e=QQmlExpression(engine.rootContext(),root,'counts.reads');r=e.evaluate();assert not e.hasError();return r[0]
    pump(150);img=window.grabWindow();assert not img.isNull()
    def digest(image):return hashlib.sha256(bytes(image.constBits())).hexdigest()
    first=digest(img);img.save(str(a.output/(name+'-before.png')))
    graph.setProperty('visible',False);pump();empty=digest(window.grabWindow());before=reads();started=time.perf_counter()
    for i in range(1,201):root.setProperty('epoch',i);app.processEvents()
    elapsed=(time.perf_counter()-started)*1000;hidden=reads()-before
    graph.setProperty('visible',True);pump(150);last=window.grabWindow();last.save(str(a.output/(name+'-after.png')))
    assert digest(last)==first,(name,'graph changed after hide/update/show')
    missing_cleared=None
    if name=='MiniHistory':
        root.setProperty('chart',None);pump(150)
        missing_cleared=digest(window.grabWindow())==empty
        assert missing_cleared,'Missing chart retained previous pixels'
    assert not warnings,warnings
    rows.append(dict(component=name,updates=200,pointsPerSeries=512,series=2,
                     hiddenPointReads=hidden,hiddenUpdateMs=elapsed,visibleSha256=first,
                     resumePixelParity=True,missingChartCleared=missing_cleared,qmlWarnings=warnings))
    window.close();engine.deleteLater();app.processEvents();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
report={'backend':os.environ['QT_QPA_PLATFORM'],'rows':rows,'scope':__doc__}
(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
