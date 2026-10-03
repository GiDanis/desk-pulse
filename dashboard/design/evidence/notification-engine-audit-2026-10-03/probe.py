"""Read-only runtime audit with isolated preferences, providers and demo events.

Run with the target runtime's Python: probe.py --runtime /path/dashboard --output /path/results.
The probe reports missing capabilities; it does not implement notification hosts.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--runtime', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
runtime = args.runtime.resolve()
args.output.mkdir(parents=True, exist_ok=True)
isolation = tempfile.TemporaryDirectory(prefix='smartpc-notification-audit-')
private = Path(isolation.name)
for key, folder in [('XDG_CONFIG_HOME', 'config'), ('XDG_CACHE_HOME', 'cache'), ('XDG_DATA_HOME', 'data')]:
    os.environ[key] = str(private / folder)
os.environ['SMARTPC_THEME_STORE'] = str(private / 'themes')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
sys.path.insert(0, str(runtime))

from PySide6 import __version__ as qt_binding_version
from PySide6.QtCore import QObject, QUrl, Qt, QEvent, QCoreApplication, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtQuick import QQuickWindow
import shiboken6
from account import AccountService
from events import EventService
from state import DashboardState
from system_info import SystemInfo
from weather import WeatherService
from theme_core import ThemeCatalog, ThemeError
from theme_test_support import as_value, wait_ready

app = QGuiApplication([])
app.setOrganizationName('SmartPC')
app.setApplicationName('Notification audit')
messages = []
qInstallMessageHandler(lambda kind, context, message: messages.append(message))
events = EventService(path=':memory:', auto_refresh=False)
state = DashboardState(WeatherService(auto_refresh=False), SystemInfo(),
                       AccountService(path=private / 'missing-account.json'), events, demo=True)
state.markCommandsSeen()
# Fixtures must be independent of the actual hour of execution.
events.set_quiet(False, 22 * 60, 7 * 60)
engine = QQmlApplicationEngine()
engine.setInitialProperties({'dashboardState': state})
engine.load(QUrl.fromLocalFile(str(runtime / 'Main.qml')))
assert engine.rootObjects(), messages
root = engine.rootObjects()[0]
window = shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0], QQuickWindow)
window.setVisibility(QQuickWindow.Visibility.Windowed)
window.resize(960, 640)
wait_ready(app, root)

def wait(ms=60):
    deadline = time.monotonic() + ms / 1000
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.002)

def expression(text, target=root):
    result, undefined = QQmlExpression(engine.rootContext(), target, text).evaluate()
    assert not undefined, text
    return as_value(result)

def key(value):
    for kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
        QCoreApplication.sendEvent(window, QKeyEvent(kind, value, Qt.KeyboardModifier.NoModifier))
    wait()

def event_rows():
    return [tuple(row) for row in events._engine.db.execute(
        'SELECT id,notified_level,dismissed_level,seen FROM events ORDER BY id')]

def bounds(item):
    return {name: item.property(name) for name in ('x', 'y', 'width', 'height')}

report = {'runtime': str(runtime), 'pyside': qt_binding_version,
          'rendering': 'offscreen/software: functional audit, not EGLFS performance', 'profiles': []}
slots = ['alerts.banner.small', 'alerts.banner.large', 'alerts.urgent',
         'alerts.badge', 'alerts.inbox', 'alerts.detail']
catalog = ThemeCatalog(private / 'themes')
report['registered_notification_slots'] = sorted(set(slots).intersection(
    content for row in catalog.presentations.values() for content in row['contentIds']))
try:
    catalog.resolve('base', {'presentations': {'alerts.banner.small': 'builtin.home.left'}})
    raise AssertionError('Incompatible notification presentation accepted')
except ThemeError as error:
    report['unregistered_slot_error'] = str(error)

service = state.appearance
service.beginEdit()
assert service.setSection('motionMode', 'off')
for scenario, name in [('banner', 'eventBanner'), ('banner grande', 'eventLargeBanner'), ('urgente', 'eventUrgent')]:
    events.set_demo_scenario(scenario)
    wait()
    before_rows = event_rows()
    deadline = events._banner_until
    before_id = (events.eventState['urgent'] if scenario == 'urgente' else events.eventState['visibleBanner'])['id']
    for theme, palette in [('base', 'day'), ('functional', 'day'), ('functional', 'night')]:
        with patch.object(state, 'dismissEvent', wraps=state.dismissEvent) as dismiss, \
             patch.object(state, 'markEventSeen', wraps=state.markEventSeen) as seen:
            assert service.selectDraft(theme), service.lastError
            wait_ready(app, root)
            assert service.setSection('paletteMode', palette), service.lastError
            wait()
            assert not dismiss.called and not seen.called
        assert events._banner_until == deadline, 'Theme reset the banner deadline'
        assert event_rows() == before_rows, 'Theme changed delivery or read state'
        item = root.findChild(QObject, name)
        assert item.property('visible')
        assert window.activeFocusItem().objectName() == 'inputOwner'
        report['profiles'].append({'scenario': scenario, 'theme': theme, 'palette': palette,
                                   'bounds': bounds(item), 'accent': expression('style.accent', item).name(),
                                   'event_id_preserved': before_id == (events.eventState['urgent'] if scenario == 'urgente' else events.eventState['visibleBanner'])['id'],
                                   'delivery_and_deadline_preserved': True, 'focus': 'inputOwner'})
    key(Qt.Key_Escape) if scenario == 'urgente' else None
    events.set_demo_scenario('nessuno')
    wait()

# A registered extension passes catalog validation but is not consumed by Main.
copy = private / 'runtime'
shutil.copytree(runtime, copy, ignore=shutil.ignore_patterns('design', '__pycache__'))
extension = copy / 'extensions/notification-audit'
extension.mkdir()
(extension / 'visual.qml').write_text('import QtQuick\nItem { required property var context }\n')
(extension / 'manifest.json').write_text(json.dumps({'apiVersion': 1, 'presentations': [
    {'id': 'audit.notification', 'file': 'extensions/notification-audit/visual.qml',
     'contentIds': slots, 'apiVersion': 1}]}))
service.catalog = ThemeCatalog(private / 'themes', root=copy)
service._resolved_cache.clear()
assert service.setSection('presentations', {slot: 'audit.notification' for slot in slots}), service.lastError
wait_ready(app, root)
events.set_demo_scenario('banner')
wait()
report['extension_probe'] = {'catalog_accepts_registered_slots': all(
    service.resolvedAppearance['presentations'][slot] == 'audit.notification' for slot in slots),
    'legacy_banner_still_used': root.findChild(QObject, 'eventBanner').property('visible'),
    'notification_host_count': sum(child.metaObject().indexOfProperty('contentId') >= 0 and
        child.property('contentId') in slots for child in root.findChildren(QObject))}
assert report['extension_probe']['legacy_banner_still_used']
assert report['extension_probe']['notification_host_count'] == 0

# Maximum legal text exposes fixed-coordinate detail collisions without inventing data.
assert service.selectDraft('base')
assert service.setTokens({'typography.textScale': 1.1})
wait_ready(app, root)
event = dict(events.eventState['visibleBanner'])
event.update(title=('Allerta importante per maltempo intenso nelle prossime ore e situazioni di rischio sul territorio ' * 2)[:100],
             detail='descrizione ' * 20)
events.publish_snapshot('demo', [event])
key(Qt.Key_3)
key(Qt.Key_Return)
assert root.property('overlay') == 'alertDetail'
wait()
title = next(child for child in root.findChildren(QObject)
             if child.metaObject().indexOfProperty('text') >= 0 and child.property('text') == event['title']
             and child.property('visible'))
detail = next(child for child in root.findChildren(QObject)
              if child.metaObject().indexOfProperty('text') >= 0 and child.property('text') == event['detail']
              and child.property('visible'))
source = next(child for child in root.findChildren(QObject)
              if child.metaObject().indexOfProperty('text') >= 0 and isinstance(child.property('text'), str)
              and child.property('text').startswith('Fonte: Demo') and 'Valido fino' in child.property('text')
              and child.property('visible'))
report['long_detail'] = {'title': bounds(title), 'detail': bounds(detail), 'source': bounds(source),
                        'title_detail_overlap_px': max(0, title.property('y') + title.property('height') - detail.property('y')),
                        'detail_source_overlap_px': max(0, detail.property('y') + detail.property('height') - source.property('y'))}
assert window.grabWindow().save(str(args.output / 'long-detail.png'))
report['warnings'] = messages
assert not messages, messages
(args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
events.close()
print(json.dumps({'profiles': len(report['profiles']), 'notification_hosts': 0,
                  'fixed_title_overlap_px': report['long_detail']['title_detail_overlap_px'],
                  'fixed_source_overlap_px': report['long_detail']['detail_source_overlap_px'], 'warnings': len(messages)}))
