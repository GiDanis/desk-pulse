"""Settings regression and optional 960×640 captures; isolated, no network."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument("--capture-dir", type=Path)
args = parser.parse_args()
directory = Path(tempfile.mkdtemp(prefix="smartpc-settings-"))
os.environ["XDG_CONFIG_HOME"] = str(directory / "config")
os.environ["XDG_CACHE_HOME"] = str(directory / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.environ["QT_QPA_PLATFORM"] == "offscreen":
    os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject, Property, QEventLoop, QTimer, QUrl, Signal, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6

from account import AccountService
from events import EventService
from state import DashboardState
from system_info import SystemInfo, wifi_quality
from weather import WeatherService
from sport import SportService
from motorsport import MotorsportService


class Keypad(QObject):
    keyPressed = Signal(int)
    changed = Signal()
    plugged = True

    @Property(bool, notify=changed)
    def connected(self):
        return self.plugged


application = QGuiApplication([])
application.setOrganizationName("SmartPC")
application.setApplicationName("Settings verification")
messages = []
qInstallMessageHandler(lambda _, __, message: messages.append(message))
engine = QQmlApplicationEngine()
keypad = Keypad()
system = SystemInfo()
weather = WeatherService(auto_refresh=False)
account = AccountService(path=directory / "account.json")
events = EventService(path=":memory:", auto_refresh=False)
sport = SportService(auto_refresh=False, cache_path=directory / "sport.json", state_path=directory / "goals.json")
racing = {kind: MotorsportService(kind, auto_refresh=False, cache_directory=directory) for kind in ("f1", "motogp")}
state = DashboardState(weather, system, account, events, demo=True, sport=sport, racing=racing)
state.markCommandsSeen()
engine.setInitialProperties({"keypad": keypad, "dashboardState": state})
engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
assert engine.rootObjects(), messages
window = engine.rootObjects()[0]
quick = shiboken6.wrapInstance(shiboken6.getCppPointer(window)[0], QQuickWindow)
if os.environ["QT_QPA_PLATFORM"] == "offscreen":
    quick.setVisibility(QWindow.Visibility.Windowed)
    quick.resize(960, 640)


def value(name):
    item = window.property(name)
    return item.toVariant() if hasattr(item, "toVariant") else item


def wait(milliseconds=100):
    # Do not quit the application between screenshots: EGLFS releases its
    # render resources on application shutdown, unlike the offscreen backend.
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def press(position):
    keypad.keyPressed.emit(position)
    application.processEvents()


def capture(name):
    if args.capture_dir:
        args.capture_dir.mkdir(parents=True, exist_ok=True)
        wait(140)
        shot = quick.grabWindow()
        assert shot.width() == 960 and shot.height() == 640, (shot.width(), shot.height(), quick.size())
        assert shot.save(str(args.capture_dir / (name + ".png")))


def setting(title):
    press(1)
    press(9)
    window.setProperty("menuIndex", 1)
    press(5)
    window.setProperty("settingsIndex", value("settingsItems").index(title))
    press(5)


press(9)
capture("menu")
window.setProperty("menuIndex", 1)
press(5)
capture("settings")
press(2)
assert value("settingsIndex") == 0, "focus wrapped at the top"
press(5)
assert value("overlay") == "appearance"
capture("appearance")
press(8)
press(5)
assert not state.animationsEnabled
press(1)
press(6)
assert window.findChild(QObject, "contentLayer").property("x") == 0
assert not DashboardState(weather, system, account, demo=True).animationsEnabled
state.toggleAnimations()

setting("Luminosità")
assert value("overlay") == "system"
capture("brightness-auto")
press(8)
before = state.manualBrightness
press(4)
assert state.manualBrightness == before, "inactive manual row changed brightness"
press(2)
press(5)
assert state.brightnessMode == "manual"
press(8)
press(4)
assert state.manualBrightness == 95
capture("brightness-manual")
window.setProperty("systemIndex", 5)
capture("brightness-hours")
press(8)
assert value("systemIndex") == 5, "focus wrapped at the bottom"
press(7)
assert value("overlay") == "settings" and value("settingsIndex") == 1

setting("Moduli visibili")
capture("modules")
press(2)
assert value("modulesIndex") == 1
press(5)
assert "meteo" not in state.visibleModules and "oggi" in state.visibleModules
press(5)

setting("Notifiche")
capture("notifications")
press(6)
assert value("overlay") == "notifications", "a menu should open only with 5"
press(5)
assert value("overlay") == "notificationQuiet"
capture("notification-quiet")
old_start = state.quietStartMinute
press(8)
press(4)
assert state.quietStartMinute == (old_start - 15) % 1440
press(6)
press(2)
press(5)
assert not state.quietHoursEnabled
press(8)
press(6)
assert state.quietStartMinute == old_start, "disabled quiet hours were editable"
capture("notification-quiet-disabled")
press(2)
press(5)
press(7)
assert value("overlay") == "notifications" and value("notificationIndex") == 0
press(8)
press(5)
assert value("overlay") == "notificationCategories"
capture("notification-categories")
press(8)
press(5)
assert not state.accountInterruptions
capture("notification-account-hidden")
assert state.quietHoursEnabled, "category selection changed the quiet schedule"
assert not DashboardState(weather, system, account, demo=True).accountInterruptions
press(5)
press(8)
with patch.object(state, "adjustSportSetting") as adjust:
    press(5)
    adjust.assert_not_called()  # Keep the live-verification gate on goal banners.
assert value("overlay") == "notificationCategories" and value("categoryIndex") == 2
press(7)
assert value("overlay") == "notifications" and value("notificationIndex") == 1

setting("Account ChatGPT")
capture("account-settings")
press(4)
assert state.accountWarningPercent == 75
press(8)
press(6)
assert state.accountCriticalPercent == 100
for _ in range(30):
    press(4)
assert state.accountCriticalPercent > state.accountWarningPercent
restored = DashboardState(weather, system, account, demo=True)
assert restored.accountWarningPercent == state.accountWarningPercent
assert restored.accountCriticalPercent == state.accountCriticalPercent

setting("Sport")
assert value("overlay") == "integrations"
capture("sport-settings-menu")
press(8)
press(5)
assert value("overlay") == "racingSettings" and value("racingSettingsKind") == "f1"
window.setProperty("racingSettingsIndex", 2)
with patch.object(state, "adjustRacingSetting") as refresh:
    press(6)
    refresh.assert_not_called()
    press(5)
    assert value("overlay") == "sources" and value("sourceIndex") == 4
    refresh.assert_not_called()
press(7)
assert value("overlay") == "racingSettings" and value("racingSettingsIndex") == 2
press(7)
assert value("overlay") == "integrations" and value("optionIndex") == 1
press(8)
press(5)
assert value("overlay") == "racingSettings" and value("racingSettingsKind") == "motogp"
setting("Sport")
press(5)
window.setProperty("sportSettingsIndex", 2)
press(5)
assert value("overlay") == "notificationCategories" and value("categoryIndex") == 2
press(7)
assert value("overlay") == "sportSettings" and value("sportSettingsIndex") == 2
window.setProperty("sportSettingsIndex", 4)
with patch.object(state, "adjustSportSetting") as refresh:
    press(4)
    refresh.assert_not_called()
    press(5)
    assert value("overlay") == "sources" and value("sourceIndex") == 3
    refresh.assert_not_called()
press(7)
assert value("overlay") == "sportSettings" and value("sportSettingsIndex") == 4

setting("Dati e aggiornamenti")
capture("sources")
with patch.object(weather, "refresh") as refresh:
    press(5)
    refresh.assert_not_called()  # Demo actions must not contact external sources.
live_state = DashboardState(weather, system, account, racing=racing)
with patch.object(weather, "refresh") as refresh:
    assert live_state.refreshSource("meteo")
    assert not live_state.refreshSource("meteo")
    assert refresh.call_count == 1
with patch.object(racing["f1"], "adjust") as refresh:
    assert live_state.refreshSource("f1")
    assert not live_state.refreshSource("f1")
    refresh.assert_called_once_with(2, 1)  # Preserve the provider's full/manual path.

press(1)
press(9)
window.setProperty("menuIndex", 2)
press(5)
assert value("overlay") == "info" and system._timer.isActive()
capture("info-device")
changes = []
system.changed.connect(lambda: changes.append(True))
with patch.object(system, "refresh", side_effect=AssertionError("getter performed I/O")):
    for _ in range(100):
        assert state.systemState["data"] == system.data
        assert system.cpuTemperature
        assert system.memoryUsage
        assert system.uptimeText
assert not changes, "reading information emitted notifications"
for _ in range(6):
    keypad.plugged = not keypad.plugged
    keypad.changed.emit()
    application.processEvents()
capture("info-device-keypad")
press(6)
wait(5200)
assert changes, "visible information did not update on its timer"
capture("info-resources")
window.setProperty("infoIndex", 5)
capture("info-resources-uptime")
press(6)
capture("info-network")
press(6)
capture("info-data")
with patch.object(state, "refreshSource") as refresh:
    press(5)
    refresh.assert_not_called()  # Info must be read-only.
press(6)
assert value("infoPage") == 3
press(7)
assert value("overlay") == "menu" and not system._timer.isActive()
press(1)
assert value("overlay") == ""

# Validate the asynchronous NetworkManager fallback, including failures, without
# changing networking or requiring a Wi-Fi interface on the development PC.
assert wifi_quality("no:80\nyes:55\n") == "55%"
for output in ("yes:101", "yes:-50", "yes:garbage", "no:80", "", "yes:NaN"):
    assert wifi_quality(output) == "N/D"
probe = SystemInfo()
helper = directory / "fake-nmcli"
helper.write_text("#!/bin/sh\nsleep 0.15\nprintf 'yes:55\\n'\n")
helper.chmod(0o700)
probe._nmcli = str(helper)
probe._monitoring = True
probe._data["interface"] = "testwifi"
probe._request_wifi("testwifi")
assert probe._wifi_process.state() != probe._wifi_process.ProcessState.NotRunning
ticks = []
heartbeat = QTimer()
heartbeat.setInterval(10)
heartbeat.timeout.connect(lambda: ticks.append(True))
heartbeat.start()
wait(350)
heartbeat.stop()
assert len(ticks) >= 5 and probe.data["wifiSignal"] == "55%", "Wi-Fi collection blocked Qt or failed"
helper.write_text("#!/bin/sh\nexit 1\n")
probe._wifi_checked = 0
probe._request_wifi("testwifi")
wait(100)
assert probe.data["wifiSignal"] == "N/D", "failed read kept an old signal"
helper.write_text("#!/bin/sh\nexec sleep 5\n")
probe._wifi_checked = 0
probe._wifi_timeout.setInterval(50)
probe._request_wifi("testwifi")
wait(150)
assert probe._wifi_process.state() == probe._wifi_process.ProcessState.NotRunning
assert probe.data["wifiSignal"] == "N/D"
probe.setMonitoring(False)

warnings = [message for message in messages if "Binding loop" in message or "file:" in message or "TypeError" in message or "ReferenceError" in message]
assert not warnings, warnings
result = {"passed": True, "qmlWarnings": warnings, "renderer": str(quick.rendererInterface().graphicsApi()), "system": system.data,
          "scope": "isolated preferences, simulated keypad changes, no external network; snapshots describe the verification process"}
if args.capture_dir:
    (args.capture_dir / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
events.close()
sport.close()
for service in racing.values():
    service.close()
system.setMonitoring(False)
qInstallMessageHandler(None)
print("Settings hierarchy, notification scope, read-only Info, asynchronous Wi-Fi, persistence, cooldown and QML: PASS")
