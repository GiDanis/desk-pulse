"""Real Main: bounded candidate marshalling, coherent hosts and pending cancel.

Count Python property calls while real QML loaders prepare/commit. The count
does not depend on the number of hosts; no frame or readiness is manufactured.
"""
import json
from pathlib import Path
import sys
import time

from theme_fixture_support import isolate_process

private, base = isolate_process()

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from account import AccountService
from events import EventService
from state import DashboardState
from system_info import SystemInfo
from theme_test_support import as_value
from weather import WeatherService

app = QGuiApplication([])
state = DashboardState(WeatherService(auto_refresh=False), SystemInfo(),
    AccountService(path=base / 'missing'),
    EventService(path=':memory:', auto_refresh=False), demo=True)
state.markCommandsSeen()
service = state.appearance
engine = QQmlApplicationEngine()
warnings = []
engine.warnings.connect(lambda rows: warnings.extend(str(row) for row in rows))
engine.setInitialProperties({'dashboardState': state})
engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('Main.qml'))))
assert engine.rootObjects(), warnings
root = engine.rootObjects()[0]


def pump():
    end = time.monotonic() + 8
    while time.monotonic() < end:
        app.processEvents()
        if (service._candidate is None
                and root.findChild(QObject, 'homeNow').property('readiness') == 'ready'):
            return
        time.sleep(.001)
    raise AssertionError((service.lastError, warnings))


pump()
service.beginEdit()
getter_calls = 0
counts = []


def profile(frame, event, argument):
    global getter_calls
    if (event == 'call' and frame.f_code.co_name == 'candidateAppearance'
            and frame.f_code.co_filename.endswith('theme_service.py')):
        getter_calls += 1


previous_profile = sys.getprofile()
sys.setprofile(profile)
try:
    for target in ['functional', 'base', 'functional', 'base']:
        getter_calls = 0
        assert service.selectDraft(target), service.lastError
        pump()
        counts.append({'target': target, 'getterCalls': getter_calls})
        assert getter_calls <= 4, counts[-1]
        assert as_value(root.property('themeCandidate')) == {}
        for name in ['homeNow', 'eventBanner', 'eventLargeBanner']:
            host = root.findChild(QObject, name)
            assert host.property('loadedRevision') == service.revision, (name, service.revision)
            assert as_value(host.property('candidateSnapshot')) == {}
    getter_calls = 0
    assert service.selectDraft('functional')
    assert service._candidate is not None
    service.cancel()
    pump()
    counts.append({'target': 'cancelPending', 'getterCalls': getter_calls})
    assert getter_calls <= 5, counts[-1]
    assert service.activeThemeId == 'base'
    assert as_value(root.property('themeCandidate')) == {}
    assert not warnings, warnings
finally:
    sys.setprofile(previous_profile)

print(json.dumps({'passed': True, 'snapshotGetterCalls': counts,
    'warnings': warnings}, indent=2))
state._events.close()
root.close()
app.processEvents()
