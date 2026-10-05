"""Real Main: immutable external bundle preview/apply/cancel/update and notifications."""
import argparse
import json
import os
from pathlib import Path
import shutil
import time

from theme_fixture_support import isolate_process
private,base=isolate_process()
from PySide6.QtCore import QObject,QUrl,QSettings,qInstallMessageHandler,QCoreApplication,QEvent,Qt
from PySide6.QtGui import QGuiApplication,QWindow,QKeyEvent
from PySide6.QtQml import QQmlApplicationEngine,QQmlExpression
from PySide6.QtQuick import QQuickWindow
import shiboken6
from account import AccountService
from events import EventService
from state import DashboardState
from system_info import SystemInfo
from weather import WeatherService
from theme_core import ROOT
from theme_bundle import BundleManager
from theme_runtime import preflight
from theme_test_support import wait_ready,wait_save,as_value

parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);parser.add_argument('--capture-dir',type=Path);args=parser.parse_args()
app=QGuiApplication([]);app.setOrganizationName('SmartPC');app.setApplicationName('SmartPC')
messages=[];qInstallMessageHandler(lambda kind,context,message:messages.append(message))
events=EventService(path=':memory:',auto_refresh=False)
state=DashboardState(WeatherService(auto_refresh=False),SystemInfo(),AccountService(path=base/'missing'),events,demo=True)
state.markCommandsSeen();state._brightness_mode='manual';state._manual_brightness=100
engine=QQmlApplicationEngine();engine.setInitialProperties({'dashboardState':state});engine.load(QUrl.fromLocalFile(str(ROOT/'Main.qml')))
assert engine.rootObjects(),messages
root=engine.rootObjects()[0];window=shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0],QQuickWindow)
if os.environ['QT_QPA_PLATFORM']=='offscreen':window.setVisibility(QWindow.Visibility.Windowed);window.resize(960,640)
service=state.appearance
service.apiFactory.diagnostic.connect(lambda code,message: print('API diagnostic:',code,message,flush=True))

def pump(ms=80):
    end=time.monotonic()+ms/1000
    while time.monotonic()<end:app.processEvents();time.sleep(.002)

def until(predicate,timeout=10):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        app.processEvents()
        if predicate():return
        time.sleep(.003)
    raise AssertionError({'error':service.lastError,'candidate':service.candidateAppearance,'warnings':messages})

def press(key):
    for kind in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease):QCoreApplication.sendEvent(window,QKeyEvent(kind,key,Qt.KeyboardModifier.NoModifier))
    pump()

wait_ready(app,root);pump(120)
project=base/'layout-project';shutil.copytree(ROOT/'examples/bundles/studio-ambient',project)
layout={'header':{'x':0,'y':0,'width':960,'height':64},
        'content':{'x':120,'y':64,'width':720,'height':520},
        'guide':{'x':0,'y':584,'width':960,'height':56},
        'sceneSafeRegions':[{'x':0,'y':64,'width':100,'height':520},{'x':840,'y':64,'width':120,'height':520}]}
manifest=json.loads((project/'bundle.json').read_text());manifest['layout']=layout
(project/'bundle.json').write_text(json.dumps(manifest))
(project/'qml/Home.qml').write_text("""import QtQuick
import SmartPC.ThemeApi 2.0
Rectangle {
    required property PageContext context
    readonly property bool ready: width > 0 && height > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    function settleMotion() { }
    color: "#445566"
    Text { anchors.centerIn: parent; text: "Layout personalizzato"; color: "white"; font.pixelSize: 32 }
    Rectangle { x: -16; y: 0; width: 16; height: parent.height; color: "red" }
}
""")
(project/'qml/Shell.qml').write_text("""import QtQuick
import SmartPC.ThemeApi 2.0
Rectangle {
    required property ShellContext context
    readonly property bool ready: true
    readonly property bool contentReady: ready
    readonly property string error: ""
    function settleMotion() { }
    color: "#112233"
}
""")
pack=json.loads((project/'theme.json').read_text());pack['scene']['enabled']=True
(project/'theme.json').write_text(json.dumps(pack))
manager=BundleManager(service.store.parent)
revision=manager.import_bundle(project,preflight=preflight,require_preflight=True)
assert service.reloadCatalog();service.beginEdit();assert service.selectDraft(revision['id']),service.lastError
wait_ready(app,root);until(lambda:service.readyToApply);pump(100)

def evaluate(expression):
    e=QQmlExpression(engine.rootContext(),root,expression);result,undefined=e.evaluate()
    assert not e.hasError(),e.error().toString();assert not undefined,expression
    return as_value(result)

def context(host):
    return as_value(as_value(host.property('currentLoader')).findChild(QObject,'publicContextAdapter').property('publicContext'))

home=root.findChild(QObject,'homeNow');shell=root.findChild(QObject,'shellHost');scene=root.findChild(QObject,'sceneHost')
assert [home.property(k) for k in ('x','y','width','height')]==[120,-26,720,520]
assert evaluate('pageGeometry("home.now").y')==64
assert home.property('clip') is True
viewport=context(home).property('viewport')
assert viewport.property('width')==720 and viewport.property('height')==520
shell_layout=context(shell).property('layout')
assert shell_layout.property('content').property('x')==120
assert shell_layout.property('content').property('height')==520
assert shell_layout.property('header').property('height')==64
assert scene.property('enforceSafeRegions') is True
anchor=scene.property('desiredAnchor');area=scene.property('actorSafeArea')
assert area.contains(anchor) and area.width()>=scene.property('actorWidth')
image=window.grabWindow();assert not image.isNull()
assert image.pixelColor(110,70).name()=='#112233','public page must clip overflowing red child'
assert image.pixelColor(122,70).name()=='#445566'
if args.capture_dir:
    args.capture_dir.mkdir(parents=True,exist_ok=True);assert image.save(str(args.capture_dir/'custom-layout.png'))
assert service.apply(),service.lastError;wait_save(app,service)
assert service.status == 'ready', {'status':service.status,'error':service.lastError,'journal':service.lifecycle.read()}
# A legacy fallback keeps its calibrated geometry and Shell advertises that area.
press(Qt.Key_Right);assert root.property('familyId')=='meteo';wait_ready(app,root)
weather=root.findChild(QObject,'weatherNow')
assert [weather.property(k) for k in ('x','y','width','height')]==[44,0,872,455]
assert context(shell).property('layout').property('content').property('x')==44
assert context(shell).property('layout').property('content').property('height')==455
assert window.activeFocusItem().objectName()=='inputOwner'
press(Qt.Key_1);wait_ready(app,root)
# Preview cancellation returns the committed layout, not the Base viewport.
service.beginEdit();assert service.selectDraft('base');wait_ready(app,root)
assert home.property('width')==872
service.cancel();wait_ready(app,root)
assert home.property('width')==720
# A revision may integrate header/guide into a full-canvas public page.
for name in ('bundle.json','theme.json'):
    value=json.loads((project/name).read_text());value['version']='1.0.1'
    if name=='bundle.json':
        value['layout']={'header':{'x':0,'y':0,'width':0,'height':0},'content':{'x':0,'y':0,'width':960,'height':640},'guide':{'x':0,'y':0,'width':0,'height':0},'sceneSafeRegions':[]}
    (project/name).write_text(json.dumps(value))
updated=manager.import_bundle(project,preflight=preflight,require_preflight=True)
assert service.reloadCatalog();service.beginEdit();assert service.stepRevision(1),service.lastError
wait_ready(app,root);until(lambda:service.readyToApply)
assert [home.property(k) for k in ('x','y','width','height')]==[0,-90,960,640]
assert context(home).property('viewport').property('height')==640
assert scene.property('regionBlocked') and not scene.property('visible')
assert as_value(scene.property('actorState')).property('paused')
assert service.apply();wait_save(app,service)
assert service.status == 'ready', {'status':service.status,'error':service.lastError,'journal':service.lifecycle.read()}
assert service.lifecycle.read()['active']['digest']==updated['digest'], {'journal':service.lifecycle.read(),'expected':updated['digest'],'draft':service.draft}
assert not messages,messages
report={'status':'passed','qt':__import__('PySide6.QtCore',fromlist=['qVersion']).qVersion(),'backend':os.environ['QT_QPA_PLATFORM'],'checks':['bounded-custom-viewport','typed-page-and-shell-layout','overflow-clipped','actor-safe-region','legacy-fallback-geometry','nine-key-focus','cancel-restores-layout','full-canvas-revision','empty-safe-regions-pause-actor','coherent-frame-apply'],'qmlWarnings':messages}
if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
window.close();engine.deleteLater();app.processEvents();events.close();private.cleanup()
