"""B0 vertical: real menu import/select/apply and six notification hosts, isolated."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time

parser=argparse.ArgumentParser()
parser.add_argument('--capture-dir',type=Path)
args=parser.parse_args()
private=tempfile.TemporaryDirectory(prefix='smartpc-authoring-ui-');directory=Path(private.name)
for key,name in [('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_CACHE_HOME','cache')]:os.environ[key]=str(directory/name)
os.environ['SMARTPC_THEME_STORE']=str(directory/'themes')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')

from PySide6.QtCore import QObject,QCoreApplication,QEvent,QSettings,QUrl,Qt,qInstallMessageHandler
from PySide6.QtGui import QGuiApplication,QKeyEvent,QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6
from account import AccountService
from events import EventService
from state import DashboardState
from system_info import SystemInfo
from theme_authoring import check_project
from theme_core import ROOT
from theme_service import ThemeService
from theme_test_support import as_value,wait_ready,wait_save
from theme_transfer import install_local
from weather import WeatherService

app=QGuiApplication([]);app.setOrganizationName('SmartPC');app.setApplicationName('Authoring proof')
messages=[];qInstallMessageHandler(lambda kind,context,message:messages.append(message))
source=ROOT/'examples/themes/braun-rams';store=Path(os.environ['SMARTPC_THEME_STORE'])
checked=check_project(source,store=store);assert checked['status']=='valid',checked
received=install_local(source,store,ROOT);assert received['status']=='received'
events=EventService(path=':memory:',auto_refresh=False)
state=DashboardState(WeatherService(auto_refresh=False),SystemInfo(),AccountService(path=directory/'missing'),events,demo=True)
state.markCommandsSeen();events.set_quiet(False,0,1)
state._brightness_mode='manual';state._manual_brightness=100
engine=QQmlApplicationEngine();engine.setInitialProperties({'dashboardState':state})
engine.load(QUrl.fromLocalFile(str(ROOT/'Main.qml')));assert engine.rootObjects(),messages
root=engine.rootObjects()[0];window=shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0],QQuickWindow)
if os.environ['QT_QPA_PLATFORM']=='offscreen':window.setVisibility(QWindow.Visibility.Windowed);window.resize(960,640)
service=state.appearance

def wait(ms=50):
    end=time.monotonic()+ms/1000
    while time.monotonic()<end:app.processEvents();time.sleep(.002)

def until(predicate,timeout=8):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        app.processEvents()
        if predicate():return
        time.sleep(.003)
    raise AssertionError('timeout: '+str(messages))

def key(value):
    for kind in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease):QCoreApplication.sendEvent(window,QKeyEvent(kind,value,Qt.KeyboardModifier.NoModifier))
    wait(25)

def capture(name):
    if args.capture_dir:
        args.capture_dir.mkdir(parents=True,exist_ok=True);wait(100)
        image=window.grabWindow();assert image.width()==960 and image.height()==640
        assert image.save(str(args.capture_dir/(name+'.png')))

wait_ready(app,root);wait(100)
baseline=service.activeThemeId
assert 'braun-rams' not in service.catalog.packs
preferences=QSettings('SmartPC','Dashboard');preferences.sync()
prefs=Path(preferences.fileName());before=hashlib.sha256(prefs.read_bytes()).hexdigest() if prefs.exists() else None
# Navigate the ordinary menu with real QKeyEvent; no private visual object IDs.
key(Qt.Key_9);assert root.property('overlay')=='menu'
key(Qt.Key_Down);key(Qt.Key_5);assert root.property('overlay')=='settings'
key(Qt.Key_5);assert root.property('overlay')=='appearance'
for _ in range(17):key(Qt.Key_Down)
assert root.property('optionIndex')==17
key(Qt.Key_5);until(lambda:service.status!='working')
assert 'braun-rams' in service.catalog.packs,service.lastError
assert service.activeThemeId==baseline,'Import applied the theme'
preferences.sync();after=hashlib.sha256(prefs.read_bytes()).hexdigest() if prefs.exists() else None
assert before==after,'Import wrote preferences'
for _ in range(15):key(Qt.Key_Up)
assert root.property('optionIndex')==2
for _ in range(len(service.catalog.packs)+1):
    if service.activeThemeId=='braun-rams':break
    key(Qt.Key_Right);wait_ready(app,root)
assert service.activeThemeId=='braun-rams',service.lastError
assert window.activeFocusItem().objectName()=='inputOwner'
for _ in range(10):key(Qt.Key_Down)
key(Qt.Key_5);wait_save(app,service)
assert not service.editing
assert ThemeService(store=store).activeThemeId=='braun-rams'
key(Qt.Key_1);wait_ready(app,root);capture('home-day')
hosts={mode:root.findChild(QObject,name) for mode,name in [('small','eventBanner'),('large','eventLargeBanner'),('urgent','eventUrgent'),('badge','unreadAlertsBadge'),('inbox','alertsInbox'),('detail','alertDetail')]}
assert hosts['small'].property('loadedPresentationId')=='builtin.alerts.small-rail'
assert hosts['large'].property('loadedPresentationId')=='builtin.alerts.large-split'
cases=[]
for variant in ('day','night'):
    for motion in ('normal','reduced','off'):
        service.beginEdit();assert service.setSection('paletteMode',variant);assert service.setSection('motionMode',motion)
        wait_ready(app,root);assert service.apply();wait_save(app,service)
        for host in hosts.values():
            assert host.property('readiness')=='ready',host.property('lastError')
            assert as_value(host.property('currentItem')) is not None
        assert service.resolvedAppearance['tokens']['colors.accent']=='#ff8c42','Night inherited the Base accent'
        for scenario,mode in [('banner','small'),('banner grande','large'),('urgente','urgent')]:
            events.set_demo_scenario(scenario);wait(200);assert hosts[mode].property('visible'),(variant,motion,mode)
            loader=as_value(hosts[mode].property('currentLoader'))
            assert abs(loader.property('opacity')-1)<.001,(variant,motion,mode,'unsettled opacity',loader.property('opacity'))
            assert window.activeFocusItem().objectName()=='inputOwner'
            if mode in ('small','large'):
                until(lambda:events._banner_timer.isActive())
                deadline=events._banner_until
                service.beginEdit();assert service.setToken('shape.radiusRow',4);wait_ready(app,root)
                assert events._banner_until==deadline,'Theme change reset banner deadline'
                service.cancel();wait_ready(app,root)
                assert abs(as_value(hosts[mode].property('currentLoader')).property('opacity')-1)<.001
            capture(variant+'-'+motion+'-'+mode)
            if mode=='urgent':key(Qt.Key_Escape)
            events.set_demo_scenario('nessuno');wait(100)
        events.set_demo_scenario('banner');wait(150);events._finish_banner();wait(50)
        key(Qt.Key_3);wait(100);assert root.property('overlay')=='alerts'
        capture(variant+'-'+motion+'-inbox')
        key(Qt.Key_5);wait(80);assert root.property('overlay')=='alertDetail'
        capture(variant+'-'+motion+'-detail')
        key(Qt.Key_Escape);key(Qt.Key_Escape)
        events.set_demo_scenario('nessuno');wait(80)
        cases.append({'variant':variant,'motion':motion,'sixHostsReady':True,'focusPreserved':True,'bannerDeadlinePreserved':True})
assert not messages,messages
report={'status':'passed','theme':'braun-rams','backend':os.environ['QT_QPA_PLATFORM'],
        'receivedDigest':received['digest'],'ordinaryMenuImportSelectApply':True,'importPreservedPreferences':True,
        'savedSelectionReloaded':True,'cases':cases,'qmlWarnings':messages,
        'scope':'Synthetic isolated preferences/SQLite/providers. QKeyEvent, not a human physical keypad press; no performance measurement.'}
if args.capture_dir:(args.capture_dir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
events.close()
print(json.dumps(report,indent=2))
