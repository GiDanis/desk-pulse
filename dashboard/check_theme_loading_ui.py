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

wait_ready(app,root);pump(100)
project=base/'delayed-project';shutil.copytree(ROOT/'examples/bundles/studio-ambient',project)
page=project/'qml/Home.qml';text=page.read_text().replace('readonly property bool ready:', 'property bool injectedReady: false\n    readonly property bool ready: injectedReady &&');page.write_text(text)
# Deliberate test-only bypass reaches the independent runtime waiting state.
# Normal preflight rejects ready=false, covered by check_theme_layout_contract.
manager=BundleManager(service.store.parent)
revision=manager.import_bundle(project,preflight=lambda *_:{'status':'passed','testOnly':True})
assert service.reloadCatalog();service.beginEdit();assert service.selectDraft(revision['id'])
home=root.findChild(QObject,'homeNow');loading=root.findChild(QObject,'themeLoading')
until(lambda:as_value(home.property('pendingLoader')) is not None and as_value(home.property('pendingLoader')).property('item') is not None)
until(lambda:loading.property('visible'))
assert service.activeThemeId=='base' and not service.readyToApply
assert window.activeFocusItem().objectName()=='inputOwner'
family=root.property('familyId');press(Qt.Key_Right);assert root.property('familyId')==family
press(Qt.Key_9);assert root.property('overlay')=='menu' and not loading.property('visible')
assert service.candidateAppearance, 'Opening Menu must not cancel the candidate'
press(Qt.Key_Escape);assert root.property('overlay')==''
until(lambda:loading.property('visible'))
if args.capture_dir:
    args.capture_dir.mkdir(parents=True,exist_ok=True);assert window.grabWindow().save(str(args.capture_dir/'theme-loading.png'))
events.set_demo_scenario('urgente');until(lambda:bool(as_value(root.property('urgentEvent')).get('id')))
assert not loading.property('visible')
urgent=root.findChild(QObject,'eventUrgent');assert urgent.property('show') and urgent.property('currentReady')
identifier=as_value(root.property('urgentEvent'))['id'];press(Qt.Key_7)
until(lambda:not as_value(root.property('urgentEvent')).get('id'))
assert loading.property('visible') and service.candidateAppearance
press(Qt.Key_7);wait_ready(app,root)
assert not loading.property('visible') and not service.candidateAppearance
assert service.activeThemeId=='base' and service.lifecycle.read()['pending'] is None
# A delayed valid renderer can complete instead of cancellation.
service.beginEdit();assert service.selectDraft(revision['id'])
until(lambda:as_value(home.property('pendingLoader')) is not None and as_value(home.property('pendingLoader')).property('item') is not None)
pending=as_value(home.property('pendingLoader'));item=as_value(pending.property('item'))
assert item.setProperty('injectedReady',True)
wait_ready(app,root);until(lambda:service.readyToApply)
assert not loading.property('visible')
assert service.apply();wait_save(app,service)
assert service.lifecycle.read()['active']['digest']==revision['digest']
# The direct chooser covers the whole automatic transaction. Deliberately
# delayed test bundle exercises cancellation and urgent priority independently
# of normal preflight (which correctly rejects this bundle).
assert service.activateTheme('base')
until(lambda:not service.themeOperation['busy']);wait_ready(app,root)
from PySide6.QtQml import QQmlExpression,QQmlEngine
def expression(code):
    expr=QQmlExpression(QQmlEngine.contextForObject(root),root,code);expr.evaluate()
    assert not expr.hasError(),expr.error().toString()
def open_delayed():
    expression('pushOverlay("appearance");openThemeChooser()')
    root.setProperty('themeChoiceIndex',[row['id'] for row in service.themes].index(revision['id']))
    press(Qt.Key_5)
    until(lambda:service.themeOperation['busy'] and as_value(home.property('pendingLoader')) is not None)
    until(lambda:loading.property('visible'))
    assert service.savedThemeId=='base' and service.lifecycle.read()['pending']
    generation=service.candidateAppearance['generation']
    press(Qt.Key_5);press(Qt.Key_8)
    assert service.candidateAppearance['generation']==generation,'duplicate input restarted candidate'
    return generation
for key,route in ((Qt.Key_7,'themeChooser'),(Qt.Key_1,''),(Qt.Key_9,'menu')):
    generation=open_delayed();press(key);wait_ready(app,root)
    assert root.property('overlay')==route
    assert not service.themeOperation['busy'] and service.savedThemeId=='base'
    assert service.lifecycle.read()['pending'] is None and not service.candidateAppearance
    service.reportCandidate(generation,'home.now',True,'')
    assert service.activeThemeId=='base','late confirmation changed cancelled selection'
    expression('home()');wait_ready(app,root)
open_delayed()
events.set_demo_scenario('urgente');until(lambda:bool(as_value(root.property('urgentEvent')).get('id')))
assert not loading.property('visible') and service.themeOperation['busy']
press(Qt.Key_7);until(lambda:not as_value(root.property('urgentEvent')).get('id'))
assert service.themeOperation['busy'],'urgent dismiss must not cancel activation'
press(Qt.Key_7);wait_ready(app,root)
expression('home()');wait_ready(app,root)
open_delayed()
until(lambda:not service.themeOperation['busy'],timeout=7)
assert service.themeOperation['phase']=='failed' and service.savedThemeId=='base'
assert service.lifecycle.read()['pending'] is None
wait_ready(app,root)
# Exit requests arriving while a real settings worker is running are deferred.
from unittest.mock import patch
from theme_service import SaveJob
original_save=SaveJob.run
def slow_save(job):
    time.sleep(.25);return original_save(job)
expression('home();pushOverlay("appearance");openThemeChooser()')
root.setProperty('themeChoiceIndex',[row['id'] for row in service.themes].index('functional'))
with patch.object(SaveJob,'run',slow_save):
    press(Qt.Key_5)
    until(lambda:service._pending is not None)
    press(Qt.Key_9)
    assert service.themeOperation['busy'] and root.property('overlay')=='themeChooser'
    assert root.property('themeExitRequested')=='menu'
    service._theme_operation_timeout();service.heartbeat(True)
    assert json.loads(service.lifecycle.health_path.read_text())['ready'] is False
    until(lambda:not service.themeOperation['busy'])
assert root.property('overlay')=='menu' and service.savedThemeId=='functional'
wait_ready(app,root)
assert not messages,messages
report={'status':'passed','qt':__import__('PySide6.QtCore',fromlist=['qVersion']).qVersion(),'backend':os.environ['QT_QPA_PLATFORM'],'checks':['application-owned-loading-feedback','delay-avoids-flash','old-theme-retained-until-ready','focus-preserved','navigation-held-while-loading','menu-remains-available-without-cancelling','urgent-preempts-loading','urgent-dismiss-does-not-cancel-theme','cancel-returns-committed-theme','ready-removes-loading-before-frame-apply','chooser-auto-cancel-home-menu','duplicate-input-and-late-confirmation','auto-urgent-priority','auto-renderer-timeout-rolls-back','menu-deferred-during-save','slow-save-withdraws-readiness-without-racing-worker'],'qmlWarnings':messages,'testOnlyPreflightBypass':True}
if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report));window.close();engine.deleteLater();app.processEvents();events.close();private.cleanup()
