"""Supplemental T05/T11/T12 real Main checks, isolated before importing Qt.

All six external notification modes use typed public contexts. The never-ready
case deliberately bypasses import preflight with a testOnly marker to exercise
the independent runtime readiness watchdog; this is not normal installation.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import time

from theme_fixture_support import isolate_process
PRIVATE, BASE = isolate_process()
from PySide6.QtCore import QObject, QUrl, QSettings, qInstallMessageHandler, qVersion
from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtQuick import QQuickWindow
import shiboken6
from account import AccountService
from events import EventService
from state import DashboardState
from system_info import SystemInfo
from weather import WeatherService
from theme_core import ROOT
from theme_runtime import preflight
from theme_test_support import wait_ready, wait_save, as_value

parser = argparse.ArgumentParser()
parser.add_argument('--case', choices=('notifications', 'scene-error', 'scene-neverready', 'scene-frame', 'overlay'), required=True)
parser.add_argument('--output', type=Path)
ARGS = parser.parse_args()
APP = QGuiApplication([]); APP.setOrganizationName('SmartPC'); APP.setApplicationName('Dashboard')
MESSAGES = []; qInstallMessageHandler(lambda kind, context, message: MESSAGES.append(message))
EVENTS = EventService(path=':memory:', auto_refresh=False)
STATE = DashboardState(WeatherService(auto_refresh=False), SystemInfo(), AccountService(path=BASE/'missing'), EVENTS, demo=True)
STATE.markCommandsSeen(); STATE._brightness_mode='manual'; STATE._manual_brightness=100
EVENTS.set_quiet(False, 0, 1)
ENGINE = QQmlApplicationEngine(); ENGINE.setInitialProperties({'dashboardState':STATE})
ENGINE.load(QUrl.fromLocalFile(str(ROOT/'Main.qml'))); assert ENGINE.rootObjects(), MESSAGES
ROOT_ITEM = ENGINE.rootObjects()[0]
WINDOW = shiboken6.wrapInstance(shiboken6.getCppPointer(ROOT_ITEM)[0], QQuickWindow)
if os.environ['QT_QPA_PLATFORM']=='offscreen':
    WINDOW.setVisibility(QWindow.Visibility.Windowed); WINDOW.resize(960, 640)
SERVICE = STATE.appearance


def pump(ms=80):
    end=time.monotonic()+ms/1000
    while time.monotonic()<end: APP.processEvents(); time.sleep(.002)


def until(predicate, timeout=8):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        APP.processEvents()
        if predicate(): return
        time.sleep(.003)
    raise AssertionError({'error':SERVICE.lastError, 'status':SERVICE.status, 'candidate':SERVICE.candidateAppearance,
                          'activeTheme':SERVICE.activeThemeId, 'messages':MESSAGES})


def evaluate(expression):
    evaluation = QQmlExpression(ENGINE.rootContext(), ROOT_ITEM, expression)
    result, undefined = evaluation.evaluate()
    assert not evaluation.hasError(), evaluation.error().toString()
    assert not undefined, expression
    return as_value(result)


def public_context(host):
    loader = as_value(host.property('currentLoader'))
    assert loader is not None
    adapter = loader.findChild(QObject, 'publicContextAdapter')
    assert adapter is not None
    context = as_value(adapter.property('publicContext'))
    assert context is not None
    return context


def document(project, name, mutation):
    path = project/name; value=json.loads(path.read_text()); mutation(value)
    path.write_text(json.dumps(value, indent=2)+'\n')


def make_project():
    project = BASE/'project'
    shutil.copytree(ROOT/'examples/bundles/studio-ambient', project)
    if ARGS.case == 'notifications':
        surfaces = ['alerts.badge', 'alerts.inbox', 'alerts.detail', 'alerts.urgent']
        def coverage(value):
            for surface in surfaces:
                value['coverage']['surfaces'].append(surface)
                value['coverage']['fallbacks'].remove(surface)
                value['resources'].append({'id':surface.replace('.', '-'), 'path':'qml/'+surface.split('.')[-1]+'.qml', 'type':'qml'})
        document(project, 'bundle.json', coverage)
        def presentations(value):
            for surface in surfaces:
                value['presentations'].append({'id':'studio.ambient.'+surface.split('.')[-1], 'contentIds':[surface],
                    'file':'qml/'+surface.split('.')[-1]+'.qml', 'apiVersion':2, 'contextApi':'notification1', 'name':surface})
        document(project, 'visual-registry.json', presentations)
        document(project, 'theme.json', lambda value:value['presentations'].update({surface:'studio.ambient.'+surface.split('.')[-1] for surface in surfaces}))
        for surface in surfaces:
            (project/'qml'/(surface.split('.')[-1]+'.qml')).write_text('''import QtQuick
import SmartPC.ThemeApi 2.0
Rectangle {
    id: root
    required property NotificationContext context
    property bool injectedReady: true
    readonly property bool ready: injectedReady && title.width > 0 && body.width > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var mandatoryRegions: [{role:"title",x:16,y:12,width:title.width,height:title.height}, {role:"body",x:16,y:52,width:body.width,height:body.height}]
    implicitHeight: body.y + body.height + 12
    function settleMotion() { }
    color: context.visualStyle.surfaceColor
    Text { id:title; x:16; y:12; width:Math.max(1,root.width-32); height:32; text:root.context.eventData ? root.context.eventData.title : root.context.mode; color:root.context.visualStyle.titleColor; font.pixelSize:24; elide:Text.ElideRight }
    Text { id:body; x:16; y:52; width:Math.max(1,root.width-32); height:32; text:root.context.eventData ? root.context.eventData.body : root.context.sourceStatus; color:root.context.visualStyle.bodyColor; font.pixelSize:20; elide:Text.ElideRight }
}
''')
    elif ARGS.case == 'overlay':
        def overlay_coverage(value):
            value['coverage']['surfaces'].append('overlay.menu')
            value['coverage']['fallbacks'].remove('overlay.menu')
            value['resources'].append({'id':'menu','path':'qml/Menu.qml','type':'qml'})
        document(project,'bundle.json',overlay_coverage)
        document(project,'visual-registry.json',lambda value:value['presentations'].append({
            'id':'studio.ambient.menu','contentIds':['overlay.menu'],'file':'qml/Menu.qml',
            'apiVersion':2,'contextApi':'overlay1','name':'Menu'}))
        document(project,'theme.json',lambda value:value['presentations'].update({'overlay.menu':'studio.ambient.menu'}))
        (project/'qml/Menu.qml').write_text('''import QtQuick
import SmartPC.ThemeApi 2.0
Rectangle {
    id:root
    required property MenuContext context
    property bool ready: true
    readonly property string error: ""
    function settleMotion() { }
    color: context.style.backgroundOverlay
    Column { x:44; y:110; spacing:16
        Repeater { model:root.context.rows
            delegate: Text { required property string title; required property string id; text:title; font.pixelSize:30; color:id === root.context.selection.selectedId ? root.context.style.semantic.accentTextOnOverlay : root.context.style.textPrimary }
        }
    }
}
''')
    else:
        document(project, 'theme.json', lambda value:value['scene'].update(enabled=True))
        def scene_coverage(value):
            value['coverage']['surfaces'].append('scene.main')
            value['coverage']['fallbacks'].remove('scene.main')
        document(project, 'bundle.json', scene_coverage)
        scene = project/'qml/Scene.qml'
        text=scene.read_text().replace('readonly property string error: ""',
                                      'property bool injectedFault: false\n    readonly property string error: injectedFault ? "injected runtime scene failure" : ""')
        text=text.replace('readonly property bool ready: true', 'property bool injectedReady: true\n    readonly property bool ready: injectedReady')
        if ARGS.case == 'scene-neverready': text=text.replace('property bool injectedReady: true','property bool injectedReady: false')
        scene.write_text(text)
    return project


def apply_bundle(revision):
    assert SERVICE.reloadCatalog(), SERVICE.lastError
    SERVICE.beginEdit(); assert SERVICE.selectDraft(revision['id']), SERVICE.lastError
    wait_ready(APP, ROOT_ITEM, timeout=8)
    until(lambda:SERVICE.readyToApply)
    assert SERVICE.apply(), SERVICE.lastError
    wait_save(APP, SERVICE)
    assert SERVICE.status == 'ready', SERVICE.lastError


def test_notifications(revision):
    apply_bundle(revision)
    names={'small':'eventBanner', 'large':'eventLargeBanner', 'badge':'unreadAlertsBadge',
           'inbox':'alertsInbox', 'detail':'alertDetail', 'urgent':'eventUrgent'}
    hosts={mode:ROOT_ITEM.findChild(QObject, name) for mode,name in names.items()}
    for mode, host in hosts.items():
        assert host is not None and host.property('currentReady'), (mode, MESSAGES)
        assert host.property('loadedPresentationId')=='studio.ambient.'+mode
        context=public_context(host)
        assert context.metaObject().className()=='NotificationContext'
        assert context.property('mode')==mode
        assert context.metaObject().indexOfProperty('controller') < 0
        assert context.metaObject().indexOfProperty('actionHandler') < 0
    for scenario, mode in [('banner','small'), ('banner grande','large')]:
        EVENTS.set_demo_scenario(scenario)
        until(lambda:bool(as_value(ROOT_ITEM.property('bannerEvent')).get('id')) and hosts[mode].property('show'))
        until(lambda:not EVENTS.eventState['bannerPending'])
        identifier=as_value(ROOT_ITEM.property('bannerEvent'))['id']
        assert public_context(hosts[mode]).property('eventData').property('id')==identifier
        deadline=EVENTS._banner_until
        SERVICE.beginEdit(); assert SERVICE.setToken('shape.radiusCard',7)
        wait_ready(APP, ROOT_ITEM); pump(50)
        assert EVENTS._banner_until==deadline, 'appearance preview must not restart an 8-second notification timer'
        SERVICE.cancel(); wait_ready(APP, ROOT_ITEM)
        EVENTS.dismiss(identifier); pump()
    # A future event is unread but has no interruptive banner, so the badge shows.
    EVENTS.set_demo_scenario('prossimo'); until(lambda:hosts['badge'].property('show'))
    assert public_context(hosts['badge']).property('unreadCount')>0
    ROOT_ITEM.setProperty('overlay','alerts'); until(lambda:hosts['inbox'].property('show'))
    inbox=public_context(hosts['inbox'])
    assert len(as_value(inbox.property('items')))>0
    assert inbox.property('itemModel').rowCount()>0
    identifier=as_value(ROOT_ITEM.property('alertItems'))[0]['id']
    evaluate('openSelectedAlert(); true')
    until(lambda:hosts['detail'].property('show'))
    assert public_context(hosts['detail']).property('eventData').property('id')==identifier
    # Urgent preemption remains app-owned while an unapplied appearance preview is open.
    SERVICE.beginEdit(); assert SERVICE.setToken('shape.radiusCard',8)
    wait_ready(APP, ROOT_ITEM); until(lambda:SERVICE.readyToApply)
    EVENTS.set_demo_scenario('urgente'); until(lambda:hosts['urgent'].property('show'))
    assert SERVICE.editing and SERVICE.draft['overrides']['tokens']['shape.radiusCard']==8
    assert hosts['detail'].property('preempted') and not hosts['detail'].property('show')
    assert public_context(hosts['urgent']).property('eventData').property('id')==as_value(ROOT_ITEM.property('urgentEvent'))['id']
    # A committed renderer can lose readiness without disappearing. The built-in
    # urgent visual must become available immediately, before supervisor recovery.
    urgent_item=as_value(hosts['urgent'].property('currentItem'))
    urgent_identity=as_value(ROOT_ITEM.property('urgentEvent'))['id']
    deadline=EVENTS._banner_until
    assert urgent_item.setProperty('injectedReady',False)
    APP.processEvents()
    assert not hosts['urgent'].property('currentReady')
    assert hosts['urgent'].property('urgentFallbackActive')
    assert as_value(hosts['urgent'].property('currentItem')) is urgent_item
    assert as_value(ROOT_ITEM.property('urgentEvent'))['id']==urgent_identity
    assert EVENTS._banner_until==deadline
    assert urgent_item.setProperty('injectedReady',True)
    APP.processEvents()
    assert not hosts['urgent'].property('urgentFallbackActive')
    assert not evaluate('notificationAction("detail", "scrollDetails", selectedAlert.id, {offset:100})')
    assert WINDOW.activeFocusItem().objectName()=='inputOwner'
    EVENTS.set_demo_scenario('nessuno'); SERVICE.cancel(); pump()
    ROOT_ITEM.setProperty('overlay',''); wait_ready(APP, ROOT_ITEM)
    return ['six-api2-contexts','small-large-event-identities','timer-deadline-retained','badge-unread','inbox-model','detail-identity','urgent-during-preview','urgent-readiness-loss-immediate-fallback','urgent-identity-deadline-retained','nonurgent-action-preempted','input-focus']


def test_scene(revision):
    settings=QSettings('SmartPC','Dashboard'); settings.setValue('functional/sentinel','retained'); settings.sync()
    EVENTS.set_demo_scenario('prossimo'); pump()
    event_ids={row['id'] for row in EVENTS.eventState['inbox']}
    if ARGS.case=='scene-neverready':
        assert SERVICE.reloadCatalog()
        SERVICE.beginEdit(); assert SERVICE.selectDraft(revision['id'])
        until(lambda:not SERVICE.candidateAppearance and not SERVICE.readyToApply, timeout=8)
        assert SERVICE.activeThemeId=='base'
        assert 'scena' in SERVICE.lastError.lower() or 'preparazione' in SERVICE.lastError.lower() or 'timeout' in SERVICE.lastError.lower(), SERVICE.lastError
        assert not SERVICE.lifecycle.read()['pending']
        checks=['never-ready-watchdog','previous-appearance-retained','journal-cancelled']
    elif ARGS.case=='scene-frame':
        WINDOW.hide(); pump(100)
        assert SERVICE.reloadCatalog()
        SERVICE.beginEdit(); assert SERVICE.selectDraft(revision['id'])
        until(lambda:not SERVICE.candidateAppearance)
        scene_host=ROOT_ITEM.findChild(QObject,'sceneHost')
        views=[child for child in scene_host.findChildren(QObject) if child.metaObject().indexOfProperty('contentId')>=0 and child.property('contentId')=='scene.main' and child.metaObject().indexOfProperty('currentItem')>=0]
        assert len(views)==1
        until(lambda:as_value(views[0].property('currentItem')) is not None)
        item=as_value(views[0].property('currentItem'))
        assert item.setProperty('injectedReady',False)
        assert not views[0].property('currentReady')
        WINDOW.show(); pump(250)
        assert not SERVICE.readyToApply, 'scene ready=false must hold first-frame acknowledgement after staging'
        assert not SERVICE.apply(), 'a scene that became unready must not be persisted'
        assert item.setProperty('injectedReady',True)
        until(lambda:SERVICE.readyToApply)
        assert SERVICE.apply(), SERVICE.lastError; wait_save(APP,SERVICE)
        assert SERVICE.status=='ready', SERVICE.lastError
        checks=['unready-scene-first-frame-blocks-apply','ready-scene-frame-enables-apply']
    else:
        apply_bundle(revision)
        scene_host=ROOT_ITEM.findChild(QObject,'sceneHost')
        views=[child for child in scene_host.findChildren(QObject) if child.metaObject().indexOfProperty('contentId')>=0 and child.property('contentId')=='scene.main' and child.metaObject().indexOfProperty('currentItem')>=0]
        assert len(views)==1
        item=as_value(views[0].property('currentItem')); assert item is not None
        assert item.setProperty('injectedFault',True)
        until(lambda:SERVICE.status=='recovery' and SERVICE.activeThemeId=='base')
        assert (SERVICE.store.parent/'theme-quarantine'/(revision['digest']+'.json')).is_file()
        assert SERVICE.lifecycle.read()['failureCounts'][revision['key']]>=1
        assert not SERVICE.lifecycle.read()['pending']
        checks=['runtime-scene-error','base-recovered','revision-quarantined']
    assert {row['id'] for row in EVENTS.eventState['inbox']}==event_ids
    assert settings.value('functional/sentinel')=='retained'
    assert WINDOW.activeFocusItem().objectName()=='inputOwner'
    return checks+['event-state-preserved','functional-preferences-preserved','input-focus']


def test_overlay(revision):
    ROOT_ITEM.setProperty('overlay','menu'); wait_ready(APP,ROOT_ITEM); pump(100)
    WINDOW.hide(); pump(100)
    assert SERVICE.reloadCatalog(), SERVICE.lastError
    SERVICE.beginEdit(); assert SERVICE.selectDraft(revision['id']), SERVICE.lastError
    until(lambda:not SERVICE.candidateAppearance)
    overlay=ROOT_ITEM.findChild(QObject,'overlayHost')
    until(lambda:overlay.property('loadedPresentationId')=='studio.ambient.menu')
    context=public_context(overlay); assert context.metaObject().className()=='MenuContext'
    assert context.rows.rowCount()==4
    assert [context.rows.get(i).title for i in range(4)]==as_value(ROOT_ITEM.property('menuItems'))
    item=as_value(overlay.property('currentItem')); assert item.setProperty('ready',False)
    assert not overlay.property('currentReady')
    WINDOW.show(); pump(250)
    assert not SERVICE.readyToApply, 'readiness=false after publish must hold first-frame acknowledgement'
    assert not SERVICE.apply(), 'unready visible overlay must not be persisted'
    assert item.setProperty('ready',True)
    until(lambda:SERVICE.readyToApply)
    assert SERVICE.apply(), SERVICE.lastError; wait_save(APP,SERVICE)
    assert SERVICE.status=='ready', SERVICE.lastError
    move=context.requestAction('selection.move','',{'direction':1})
    assert move.accepted and move.status=='completed', (move.status,move.errorCode)
    assert ROOT_ITEM.property('menuIndex')==1
    assert context.selection.selectedId==context.rows.get(1).id
    selection=context.requestAction('selection.select',context.rows.get(2).id,{})
    assert selection.accepted and selection.status=='completed', (selection.status,selection.errorCode)
    assert ROOT_ITEM.property('menuIndex')==2
    activation=context.requestAction('menu.activate',context.rows.get(1).id,{})
    assert activation.accepted and activation.status=='completed', (activation.status,activation.errorCode)
    assert ROOT_ITEM.property('overlay')=='settings'
    until(lambda:WINDOW.activeFocusItem() is not None and WINDOW.activeFocusItem().objectName()=='inputOwner')
    return ['external-menu-renderer','typed-menu-model','unready-first-frame-blocks-apply','ready-frame-enables-apply',
            'selection-move-broker','selection-select-broker','menu-activate-broker','protected-focus-after-route']


try:
    wait_ready(APP, ROOT_ITEM); pump(100)
    project=make_project()
    callback = (lambda *_:{'status':'passed','testOnly':True,'purpose':'independent-runtime-readiness-watchdog'}) if ARGS.case=='scene-neverready' else preflight
    revision=SERVICE.bundles.import_bundle(project, preflight=callback, require_preflight=True)
    checks = test_notifications(revision) if ARGS.case=='notifications' else test_overlay(revision) if ARGS.case=='overlay' else test_scene(revision)
    pump(60); assert not MESSAGES, MESSAGES
    result={'status':'passed','case':ARGS.case,'qt':qVersion(),'backend':os.environ['QT_QPA_PLATFORM'],'checks':checks,
            'qmlWarnings':MESSAGES,'physicalKeys':'notVerified','boardPerformance':'notVerified'}
    if ARGS.output:
        ARGS.output.parent.mkdir(parents=True,exist_ok=True)
        ARGS.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
finally:
    SERVICE.cancel(); WINDOW.close(); ENGINE.deleteLater(); APP.processEvents(); EVENTS.close(); PRIVATE.cleanup()
