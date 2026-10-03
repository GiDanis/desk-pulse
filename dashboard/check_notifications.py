"""Notification contracts, presentation swaps, delivery, focus and long-text UX.

Uses real QML, native Qt keyboard events and isolated SQLite/preferences. No network.
Optional --capture-dir stores synthetic-data captures and a verification report.
"""
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--capture-dir', type=Path)
parser.add_argument('--motion', choices=('normal','reduced','off'), default='normal')
parser.add_argument('--variant', choices=('day','night'), default='day')
args = parser.parse_args()
private = Path(tempfile.mkdtemp(prefix='smartpc-notifications-'))
for key, folder in [('XDG_CONFIG_HOME','config'),('XDG_CACHE_HOME','cache'),('XDG_DATA_HOME','data')]:
    os.environ[key] = str(private/folder)
os.environ['SMARTPC_THEME_STORE'] = str(private/'themes')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM'] == 'offscreen': os.environ.setdefault('QT_QUICK_BACKEND','software')

from PySide6.QtCore import QObject, QCoreApplication, QEvent, QUrl, Qt, qInstallMessageHandler
from PySide6.QtGui import QFontDatabase, QGuiApplication, QKeyEvent, QWindow
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtQuick import QQuickWindow
import shiboken6
from account import AccountService
from events import EventService
from state import DashboardState
from system_info import SystemInfo
from theme_pack import import_pack
from theme_test_support import as_value, current_item, wait_ready, wait_save
from weather import WeatherService

app = QGuiApplication([])
app.setOrganizationName('SmartPC'); app.setApplicationName('Notifications check')
messages = []
qInstallMessageHandler(lambda kind,context,message: messages.append(message))
runtime = Path(__file__).parent
report = {'cases':[], 'captures':[], 'expected_loader_errors':[]}

def wait(ms=80):
    deadline = time.monotonic()+ms/1000
    while time.monotonic() < deadline: app.processEvents(); time.sleep(.002)

def until(predicate, timeout=4):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate(): return
        time.sleep(.002)
    raise AssertionError('Notification readiness timeout: '+str(messages))

def event(identifier='probe', priority=2, **values):
    now = time.time()
    return dict(version=1,id=identifier,source='probe',sourceLabel='Demo',category='demo',priority=priority,
                title='Avviso di prova',detail='Evento simulato, nessuna fonte esterna.',issuedAt=now,startsAt=now-1,
                expiresAt=now+3600,revision='1',**values)

# Service delivery is deferred until an acknowledgement for the still-valid ID.
service_only = EventService(path=':memory:',auto_refresh=False)
service_only.set_quiet(False,0,1); service_only.setPresentationAcknowledgement(True); service_only.setBannerAvailable(True)
service_only.publish_snapshot('probe',[event()])
assert service_only.eventState['bannerPending'] and not service_only._banner_timer.isActive()
assert not service_only.markBannerPresented('stale')
replacement = event(); replacement.update(revision='2',notificationRank=3)
service_only.publish_snapshot('probe',[replacement])
assert not service_only.markBannerPresented('probe','1',2), 'A frame from an old revision delivered the replacement'
assert service_only.markBannerPresented('probe','2',3)
deadline = service_only._banner_until
assert 7.8 < deadline-time.monotonic() <= 8
assert not service_only.markBannerPresented('probe') and service_only._banner_until == deadline
service_only._finish_banner(); assert not service_only.eventState['visibleBanner']
service_only.publish_snapshot('probe',[])
service_only.publish_snapshot('probe',[event('cancelled')]); service_only.setBannerAvailable(False)
assert not service_only.eventState['visibleBanner'] and not service_only.markBannerPresented('cancelled')
service_only.setBannerAvailable(True); assert service_only.eventState['bannerPending']
service_only.publish_snapshot('probe',[]); assert not service_only.markBannerPresented('cancelled')
service_only.publish_snapshot('probe',[event('interrupted')]); service_only.publish_snapshot('probe',[event('urgent',3)])
assert service_only.eventState['urgent'] and not service_only.eventState['visibleBanner']
service_only.close(); report['cases'].append('delivery_acknowledgement_and_cancellation')

def create(root=runtime, urgent=False, before_load=None):
    events = EventService(path=':memory:',auto_refresh=False)
    state = DashboardState(WeatherService(auto_refresh=False),SystemInfo(),AccountService(path=private/'missing'),events,demo=True)
    state.markCommandsSeen(); events.set_quiet(False,0,1)
    state._night_mode = args.variant
    state._brightness_mode='manual'; state._manual_brightness=100
    if root != runtime:
        from theme_service import ThemeService
        state._appearance = ThemeService(state,store=private/'themes',root=root)
        state._appearance.changed.connect(state.settingsChanged)
    state.appearance.beginEdit()
    assert state.appearance.setSection('paletteMode',args.variant)
    assert state.appearance.setSection('motionMode',args.motion)
    assert state.appearance.apply(); wait_save(app,state.appearance)
    if before_load: before_load(state.appearance)
    if urgent: events.set_demo_scenario('urgente')
    engine = QQmlApplicationEngine(); engine.setInitialProperties({'dashboardState':state})
    engine.load(QUrl.fromLocalFile(str(root/'Main.qml'))); assert engine.rootObjects(),messages
    window = engine.rootObjects()[0]
    quick = shiboken6.wrapInstance(shiboken6.getCppPointer(window)[0],QQuickWindow)
    if os.environ['QT_QPA_PLATFORM'] == 'offscreen':
        quick.setVisibility(QWindow.Visibility.Windowed); quick.resize(960,640)
    return engine,state,events,window,quick

engine,state,events,root,window = create()
wait_ready(app,root); service = state.appearance
hosts = {mode:root.findChild(QObject,name) for mode,name in [('small','eventBanner'),('large','eventLargeBanner'),('urgent','eventUrgent'),('badge','unreadAlertsBadge'),('inbox','alertsInbox'),('detail','alertDetail')]}
assert all(host and as_value(host.property('currentItem')) for host in hosts.values())
assert all(as_value(host.property('context')).property('ready') for host in hosts.values())

def execute(code, target=root, owner=engine):
    expression = QQmlExpression(owner.rootContext(),target,code)
    result = expression.evaluate(); assert not expression.hasError(),expression.error().toString()
    return as_value(result[0])

def key(value, target=window):
    for kind in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease):
        QCoreApplication.sendEvent(target,QKeyEvent(kind,value,Qt.KeyboardModifier.NoModifier))
    wait(40)

def select(identifier):
    if not service.editing: service.beginEdit()
    assert service.selectDraft(identifier),service.lastError
    wait_ready(app,root); wait(30)

def rows():
    return [tuple(row) for row in events._engine.db.execute('SELECT id,notified_level,dismissed_level,seen FROM events ORDER BY id')]

def capture(name):
    if args.capture_dir:
        args.capture_dir.mkdir(parents=True,exist_ok=True); wait(180)
        shot = window.grabWindow(); assert shot.width()==960 and shot.height()==640
        assert shot.save(str(args.capture_dir/(name+'.png')))
        report['captures'].append(name)

service.beginEdit(); assert service.setSection('paletteMode',args.variant)
import_pack(runtime/'examples/themes/personal-sample',service.store)
assert service.reloadCatalog()
for scenario,mode in [('banner','small'),('banner grande','large'),('urgente','urgent')]:
    events.set_demo_scenario(scenario); wait()
    if mode != 'urgent': until(lambda:not events.eventState['bannerPending'])
    previous_rows,deadline = rows(),events._banner_until
    before_id = as_value(root.property('urgentEvent' if mode=='urgent' else 'bannerEvent'))['id']
    with ExitStack() as stack:
        spies=[stack.enter_context(patch.object(state,name,wraps=getattr(state,name))) for name in ('dismissEvent','markEventSeen','markBannerPresented')]
        for identifier in ('functional','personal.sample','base'):
            old_item = as_value(hosts[mode].property('currentItem'))
            select(identifier)
            assert hosts[mode].property('show') and hosts[mode].property('visible')
            if mode != 'urgent': assert as_value(hosts[mode].property('currentItem')) is not old_item
            assert rows()==previous_rows and events._banner_until==deadline
            assert as_value(root.property('urgentEvent' if mode=='urgent' else 'bannerEvent'))['id']==before_id
            assert window.activeFocusItem().objectName()=='inputOwner'
            capture(identifier+'-'+mode)
        assert all(spy.call_count==0 for spy in spies),'Theme restarted delivery or changed read/dismiss state'
    if mode == 'urgent': key(Qt.Key_Escape)
    events.set_demo_scenario('nessuno'); wait(180)
report['cases'].append('three_themes_visible_notifications_preserve_delivery_focus_deadline')

# A transparent entry frame cannot deliver the event; the native tween survives
# the appearance revision and ends with exactly the original delivery deadline.
service.beginEdit();assert service.setSection('motion',{'banner.small.enter':{'recipe':'builtin.fade','durationMs':200,'distancePx':20,'easing':'outCubic','opacityFrom':0}})
events.set_demo_scenario('banner')
loader=as_value(hosts['small'].property('currentLoader'))
assert events.eventState['bannerPending']
if args.motion != 'off': assert loader.property('opacity')==0
until(lambda:not events.eventState['bannerPending'])
deadline=events._banner_until
wait(240);assert loader.property('opacity')==1 and events._banner_until==deadline
events.set_demo_scenario('nessuno');wait(120);service.cancel();wait_ready(app,root)
report['cases'].append('transparent_entry_native_motion_and_frame_acknowledgement')

# Notification footprints pause locomotion without overwriting an actor action.
service.beginEdit();assert service.setSection('scene',{'enabled':True});wait()
scene=root.findChild(QObject,'sceneHost');actor_state=as_value(scene.property('actorState'))
actor_state.setProperty('pose','playing');actor_state.setProperty('locomotion','moving')
events.set_demo_scenario('banner grande');wait(100)
assert scene.property('regionBlocked') and actor_state.property('paused')
assert actor_state.property('pose')=='playing' and actor_state.property('locomotion')=='idle'
events.set_demo_scenario('nessuno');wait(250);service.cancel();wait_ready(app,root)
report['cases'].append('scene_occupied_regions_pause_locomotion_preserve_action')

# Local roles do not change Home typography; font registrations remain shared.
service.beginEdit()
assert service.setTokens({'notifications.large.titleSize':60,'notifications.inbox.rows':2})
assert service.resolvedAppearance['tokens']['typography.size44']==44
families = [family for family in QFontDatabase.families() if 'Mono' in family]
if families:
    assert service.setToken('notifications.large.titleFamily',families[0])
    assert service.resolvedAppearance['tokens']['notifications.large.titleFamily']==families[0]
    assert service.resolvedAppearance['tokens']['typography.uiFamily']==app.font().family()
service.cancel(); wait_ready(app,root)

# The shipped cards reserve body/source/commands even with maximum title/body
# roles and a long title. Incompatible combined geometry is rejected beforehand.
for mode in ('large','urgent'):
    service.beginEdit()
    assert service.setTokens({'typography.textScale':1.1,'notifications.'+mode+'.titleSize':72,'notifications.'+mode+'.bodySize':44})
    large_text=event('maximum-'+mode,3 if mode=='urgent' else 2)
    large_text.update(bannerSize='large',title=('Allerta importante sul territorio nelle prossime ore '*3)[:100],detail='descrizione '*20)
    events.publish_snapshot('probe',[large_text]); wait(100)
    if mode=='large': until(lambda:not events.eventState['bannerPending'])
    visual=as_value(hosts[mode].property('currentItem'))
    title=visual.findChild(QObject,'notificationTitle'); body=visual.findChild(QObject,'notificationBody'); source=visual.findChild(QObject,'notificationSource')
    assert title.property('height')>0 and body.property('height')>0
    assert title.property('y')+title.property('height') <= body.property('y')
    assert body.property('y')+body.property('height') <= source.property('y')
    capture('maximum-roles-'+mode)
    events.publish_snapshot('probe',[]); service.cancel(); wait_ready(app,root); wait()
report['cases'].append('maximum_card_roles_reserve_text_source_and_commands')

# All text remains accessible with legal maximum strings and large type.
service.beginEdit(); assert service.setSection('paletteMode','day'); assert service.setToken('typography.textScale',1.1)
long = event('long')
long.update(title=('Allerta importante per maltempo intenso nelle prossime ore e situazioni di rischio sul territorio '*2)[:100],detail='descrizione '*20)
events.publish_snapshot('probe',[long]); wait(); until(lambda:not events.eventState['bannerPending'])
key(Qt.Key_3); key(Qt.Key_Return); assert root.property('overlay')=='alertDetail'
detail = current_item(app,root,'alertDetail')
title = detail.findChild(QObject,'notificationTitle'); body = detail.findChild(QObject,'notificationBody'); source = detail.findChild(QObject,'notificationSource')
assert title.property('y')+title.property('height') <= body.property('y')
assert body.property('y')+body.property('height') <= source.property('y')
assert as_value(hosts['detail'].property('context')).property('scrollMaximum') > 0
capture('long-detail-top')
for _ in range(6): key(Qt.Key_Down)
scroll = detail.findChild(QObject,'notificationScroll')
assert abs(scroll.property('contentY')-as_value(hosts['detail'].property('context')).property('scrollMaximum')) < 1
capture('long-detail-bottom')
key(Qt.Key_Escape); key(Qt.Key_Escape); events.publish_snapshot('probe',[]); service.cancel(); wait_ready(app,root)
report['cases'].append('maximum_text_no_overlap_keyboard_scroll_to_source')

# Stable event selection survives insertions and different list densities.
listing = [event('row'+str(index)) for index in range(5)]
for index,value in enumerate(listing): value['issuedAt'] += index
events.publish_snapshot('probe',listing); key(Qt.Key_3); key(Qt.Key_Down)
focused = root.property('alertFocusedId')
newer = event('new'); newer['issuedAt'] += 20
events.publish_snapshot('probe',[newer]+listing); wait()
assert root.property('alertFocusedId')==focused
service.beginEdit(); assert service.setToken('notifications.inbox.rows',1); wait_ready(app,root)
assert root.property('alertFocusedId')==focused
inbox = current_item(app,root,'alertsInbox'); assert inbox.property('pageStart')==inbox.property('selectedIndex')
key(Qt.Key_Escape); service.cancel(); events.publish_snapshot('probe',[]); wait()
report['cases'].append('inbox_selection_identity_during_refresh_and_density_change')

# Guided editor and previews never touch real notification delivery or database.
execute('pushOverlay("appearance")'); root.setProperty('optionIndex',19); key(Qt.Key_Return)
assert root.property('overlay')=='appearanceNotifications' and service.editing
root.setProperty('optionIndex',9); old = service.resolvedAppearance['tokens']['notifications.small.titleSize']; key(Qt.Key_Right)
assert service.resolvedAppearance['tokens']['notifications.small.titleSize']==old+2
before = rows()
root.setProperty('optionIndex',7); key(Qt.Key_Return)
assert root.property('notificationPreviewMode')=='small'
for _ in range(6):
    key(Qt.Key_Right); assert window.activeFocusItem().objectName()=='inputOwner'
    assert rows()==before and not events.eventState['visibleBanner'] and not events.eventState['urgent']
key(Qt.Key_Escape); assert root.property('notificationPreviewMode')==''
key(Qt.Key_Escape); assert root.property('overlay')=='appearance' and service.editing
assert root.property('optionIndex')==19
key(Qt.Key_Escape); assert not service.editing
report['cases'].append('editor_and_six_isolated_previews')

# Use a private application checkout for delayed, invalid and cold urgent renderers.
copy = private/'application'
shutil.copytree(runtime,copy,ignore=shutil.ignore_patterns('design','__pycache__'))
extension = copy/'extensions/check-notifications'; extension.mkdir()
def delayed(name, delay):
    (extension/(name+'.qml')).write_text('''import QtQuick
import "../../components"
Rectangle { required property var context; property bool presentationReady: false
    color: context.visualStyle.surfaceColor
    NotificationText { style: context.visualStyle; role: "title"; width: parent.width; text: context.event.title || "" }
    Timer { interval: '''+str(delay)+'''; running: true; onTriggered: parent.presentationReady = true }
}
''')
delayed('Small',80); delayed('Large',240); delayed('Urgent',1000)
(extension/'Broken.qml').write_text('import QtQuick\nItem { required property var context; invalid syntax! }\n')
(extension/'Never.qml').write_text('import QtQuick\nItem { required property var context; property bool presentationReady: false }\n')
descriptors=[]
for name,mode in [('Small','small'),('Large','large'),('Urgent','urgent'),('Broken','small'),('Never','large')]:
    descriptors.append({'id':'check.alerts.'+name.lower(),'contentIds':['alerts.banner.'+mode if mode in ('small','large') else 'alerts.'+mode],
                        'file':'extensions/check-notifications/'+name+'.qml','apiVersion':1,'contextApi':'notification1'})
(extension/'manifest.json').write_text(json.dumps({'apiVersion':1,'presentations':descriptors}))
if os.environ['QT_QPA_PLATFORM'] == 'eglfs':
    engine.deleteLater(); QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
engine2,state2,events2,root2,window2 = create(copy)
wait_ready(app,root2); service2 = state2.appearance
service2.beginEdit(); revision = service2.revision
assert service2.setSection('presentations',{'alerts.banner.small':'check.alerts.small','alerts.banner.large':'check.alerts.large'})
generation = service2.candidateAppearance['generation']
wait(140); assert service2.revision==revision and not service2.readyToApply,'Partial layout published before all surfaces were ready'
events2.set_demo_scenario('urgente'); wait(20)
assert root2.findChild(QObject,'eventUrgent').property('visible') and window2.activeFocusItem().objectName()=='inputOwner'
until(lambda:service2.revision > revision); wait_ready(app,root2)
key(Qt.Key_Escape,window2)
revision = service2.revision; service2.reportCandidate(generation,'alerts.banner.large',True,'')
assert service2.revision==revision,'Stale candidate callback was accepted'
service2.cancel(); wait_ready(app,root2)
start_errors = len(messages); service2.beginEdit(); previous = service2.revision
assert service2.setSection('presentations',{'alerts.banner.small':'check.alerts.broken'})
until(lambda:bool(service2.lastError)); assert service2.revision==previous and not service2.readyToApply
assert messages[start_errors:] and all('Broken.qml' in message for message in messages[start_errors:]),messages[start_errors:]
report['expected_loader_errors'] = messages[start_errors:]; del messages[start_errors:]
service2.cancel(); wait_ready(app,root2); service2.beginEdit(); previous=service2.revision
assert service2.setSection('presentations',{'alerts.banner.large':'check.alerts.never'})
until(lambda:bool(service2.lastError)); assert service2.revision==previous and not service2.readyToApply
service2.cancel(); wait_ready(app,root2)
service2.beginEdit(); assert service2.setSection('presentations',{'alerts.banner.small':'check.alerts.small'})
service2.cancel(); wait(300); assert not service2.candidateAppearance and not service2.editing
report['cases'].append('coordinated_staging_urgent_preemption_stale_error_timeout_cancel')

def cold(service):
    service.beginEdit(); assert service.setSection('presentations',{'alerts.urgent':'check.alerts.urgent'})
if os.environ['QT_QPA_PLATFORM'] == 'eglfs':
    engine2.deleteLater(); QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
engine3,state3,events3,root3,window3 = create(copy,urgent=True,before_load=cold)
wait(100)
urgent = root3.findChild(QObject,'eventUrgent'); fallback = urgent.findChild(QObject,'urgentFallback')
assert not as_value(urgent.property('currentItem')) and fallback.property('active') and as_value(fallback.property('item'))
assert window3.activeFocusItem().objectName()=='inputOwner'
key(Qt.Key_Escape,window3); assert not events3.eventState['urgent'],'Emergency urgent commands were blocked by the Loader'
wait_ready(app,root3)
report['cases'].append('cold_urgent_emergency_immediate_and_keyboard_dismissal')

assert not messages,messages
for value in (events,events2,events3): value.close()
if args.capture_dir:
    report['platform'] = os.environ['QT_QPA_PLATFORM']
    report['motionMode'] = args.motion; report['variant'] = args.variant
    (args.capture_dir/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Notifications: six slots, three themes, delivery acknowledgement, coherent swaps, Qt focus, emergency urgent, long text/scroll, selected IDs and isolated editor preview PASS')
