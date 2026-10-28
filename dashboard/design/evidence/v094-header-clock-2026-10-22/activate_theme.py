"""Apply the qualified Apple revision using actual Main readiness/frame/save.

Run as smartpc, kiosk stopped, production Qt settings, no provider polling.
Only the immutable bundle identity changes in the appearance configuration.
"""
from pathlib import Path
import json
import os
import sys
import time

sys.path.insert(0, '/opt/smartpc/dashboard')
from PySide6.QtCore import QSettings, QUrl
from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6
from account import AccountService
from state import DashboardState
from system_info import SystemInfo
from weather import WeatherService
from theme_test_support import wait_ready, wait_save

app = QGuiApplication([])
app.setOrganizationName('SmartPC')
app.setApplicationName('SmartPC')
from theme_bundle import BundleManager, validate_project
from PySide6.QtCore import qVersion
bundle = Path('/var/lib/smartpc-dashboard/v094-project/theme-projects/apple-calm/bundle')
cache = json.loads((bundle.parent / 'evidence/preflight-cache.json').read_text())
identity = json.loads(Path(sys.argv[1]).read_text())
assert cache['digest'] == identity['digest'] == validate_project(bundle)['digest']
assert cache['result']['qt'] == qVersion() and cache['result']['status'] == 'passed'
data = Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC')
revision = BundleManager(data).import_bundle(bundle, preflight=lambda *_: {
    **cache['result'], 'boardEglfs': 'passed'}, require_preflight=True)
assert {key: revision[key] for key in ('id', 'version', 'digest')} == identity
state = DashboardState(WeatherService(auto_refresh=False), SystemInfo(), AccountService())
service = state.appearance
previous = dict(service.draft)
assert previous['themeId'] == 'studio.applecalm'
engine = QQmlApplicationEngine()
engine.setInitialProperties({'dashboardState': state})
engine.load(QUrl.fromLocalFile('/opt/smartpc/dashboard/Main.qml'))
assert engine.rootObjects()
root = engine.rootObjects()[0]
window = shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0], QQuickWindow)
window.setVisibility(QWindow.Visibility.Windowed)
window.resize(960, 640)
wait_ready(app, root, timeout=15)
service.beginEdit()
assert service._change({**previous, 'bundleRevision': identity}), service.lastError
deadline = time.monotonic() + 25
while not service.readyToApply and time.monotonic() < deadline:
    app.processEvents()
    time.sleep(.01)
assert service.readyToApply, service.lastError
assert service.apply(), service.lastError
wait_save(app, service, timeout=15)
current = json.loads(QSettings('SmartPC', 'Dashboard').value('appearance/config'))
assert current == {**previous, 'bundleRevision': identity}, (previous, current)
assert service.lifecycle.read()['active'] == identity and service.lifecycle.read()['pending'] is None
print(json.dumps(dict(status='passed', before=previous['bundleRevision'], after=identity,
                      appearanceOptionsPreserved=True)), flush=True)
window.close()
