"""Real Main: immutable external bundle preview/apply/cancel/update and notifications."""
import argparse
import json
import os
from pathlib import Path
import shutil
import time

from theme_fixture_support import isolate_process
private,base=isolate_process()
from PySide6.QtCore import QObject,QUrl,qInstallMessageHandler,QCoreApplication,QEvent,Qt
from PySide6.QtGui import QGuiApplication,QWindow,QKeyEvent
from PySide6.QtQml import QQmlApplicationEngine
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

parser=argparse.ArgumentParser();parser.add_argument('--capture-dir',type=Path);args=parser.parse_args()
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

wait_ready(app,root);pump(180)
manager=BundleManager(service.store.parent)
revision=manager.import_bundle(ROOT/'examples/bundles/studio-ambient',preflight=preflight,require_preflight=True)
assert service.reloadCatalog(),service.lastError
service.beginEdit();assert service.selectDraft(revision['id']),service.lastError
wait_ready(app,root);until(lambda:service.readyToApply)
home=root.findChild(QObject,'homeNow');item=as_value(home.property('currentItem'))
assert home.property('loadedPresentationId')=='studio.ambient.home'
context=as_value(as_value(home.property('currentLoader')).findChild(QObject,'publicContextAdapter').property('publicContext'));assert context.metaObject().className()=='PageContext'
assert context.property('contentId')=='home.now'
assert context.metaObject().indexOfProperty('controller')<0
assert context.metaObject().indexOfProperty('model')<0
assert window.activeFocusItem().objectName()=='inputOwner'
assert service.lifecycle.read()['pending']['candidate']['digest']==revision['digest']
assert service.apply(),service.lastError;wait_save(app,service);assert service.lifecycle.read()['active']['digest']==revision['digest']
if args.capture_dir:
    args.capture_dir.mkdir(parents=True,exist_ok=True);assert window.grabWindow().save(str(args.capture_dir/'bundle-home.png'))
# Author-defined small and large loaded through stable host names; timer/priority stay app-owned.
small=root.findChild(QObject,'eventBanner');large=root.findChild(QObject,'eventLargeBanner')
assert small.property('loadedPresentationId')=='studio.ambient.small'
assert large.property('loadedPresentationId')=='studio.ambient.large'
for scenario in ('banner','banner grande'):
    events.set_demo_scenario(scenario);pump(240)
    if as_value(root.property('bannerEvent')).get('id'):
        host=large if as_value(root.property('bannerEvent')).get('bannerSize')=='large' else small
        assert host.property('visible') and host.property('readiness')=='ready'
        context=as_value(as_value(host.property('currentLoader')).findChild(QObject,'publicContextAdapter').property('publicContext'))
        assert context.metaObject().indexOfProperty('actionHandler')<0
        assert context.property('eventData').property('id')==as_value(root.property('bannerEvent'))['id']
# Cancel preview changes no committed appearance or domain state.
service.beginEdit();assert service.selectDraft('base');wait_ready(app,root);service.cancel();wait_ready(app,root)
assert service.activeThemeId==revision['id']
# Same semantic renderer ID with a new immutable source must reload.
project=base/'updated';shutil.copytree(ROOT/'examples/bundles/studio-ambient',project)
for name in ('bundle.json','theme.json'):
    value=json.loads((project/name).read_text());value['version']='1.0.1';(project/name).write_text(json.dumps(value))
qml=project/'qml/Home.qml';qml.write_text(qml.read_text()+'\n// independent revision\n')
updated=manager.import_bundle(project,preflight=preflight,require_preflight=True)
assert service.reloadCatalog();before=as_value(home.property('currentItem'))
service.beginEdit();assert service.stepRevision(1),service.lastError
wait_ready(app,root);until(lambda:service.readyToApply)
assert as_value(home.property('currentItem')) is not before
assert service.resolvedAppearance['bundleRevision']['digest']==updated['digest']
assert service.apply();wait_save(app,service)
# Nine-key navigation remains owned by inputOwner while external renderers are alive.
press(Qt.Key_9);assert root.property('overlay')=='menu';press(Qt.Key_Escape)
press(Qt.Key_Right);assert root.property('familyId')=='meteo';press(Qt.Key_1)
assert window.activeFocusItem().objectName()=='inputOwner'
assert not messages,messages
print(json.dumps({'status':'passed','qt':__import__('PySide6.QtCore',fromlist=['qVersion']).qVersion(),'backend':os.environ['QT_QPA_PLATFORM'],'checks':['public-context','external-home','small-large','frame-ack','apply','cancel','immutable-update','nine-key-focus'],'qmlWarnings':messages,'boardPerformance':'notVerified'}))
window.close();engine.deleteLater();app.processEvents();events.close();private.cleanup()
