"""Fast QML regression check for navigation and the v0.3 state contract."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Isolate the first-run and theme preferences from the real kiosk account.
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="smartpc-check-")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject, QDate, QDateTime, QTime, QTimer, QUrl, Signal  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402
import shiboken6  # noqa: E402

from app import SystemInfo  # noqa: E402
from account import AccountService  # noqa: E402
from state import DashboardState  # noqa: E402
from weather import WeatherService  # noqa: E402


class FakeKeypad(QObject):
    keyPressed = Signal(int)
    connected = True


def main() -> None:
    application = QGuiApplication([])
    application.setOrganizationName("SmartPC")
    application.setApplicationName("SmartPC check")
    engine = QQmlApplicationEngine()
    system = SystemInfo()
    weather = WeatherService(auto_refresh=False)
    account = AccountService(path=Path(os.environ["XDG_CONFIG_HOME"]) / "missing-account.json")
    keypad = FakeKeypad()
    state = DashboardState(weather, system, account, demo=True)
    engine.setInitialProperties({"keypad": keypad, "dashboardState": state})
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
    assert engine.rootObjects(), "QML failed to load"
    window = engine.rootObjects()[0]
    content = window.findChild(QObject, "contentLayer")
    assert content is not None
    screens = {
        name: window.findChild(QObject, name)
        for name in ("homeNow", "homeDay", "weatherNow", "weatherForecast", "accountPanel")
    }
    assert all(screens.values()), "a QML screen is missing"

    def visible_screen() -> str:
        visible = [name for name, screen in screens.items() if screen.property("visible")]
        assert len(visible) == 1, f"expected one visible screen, got {visible}"
        return visible[0]

    def press(position: int, transition: bool = False) -> None:
        keypad.keyPressed.emit(position)
        application.processEvents()
        if transition:
            QTimer.singleShot(240, application.quit)
            application.exec()
            assert content.property("opacity") >= 0.99, "navigation left the content invisible"
            assert abs(content.property("x")) < 0.1, "navigation did not finish"

    assert window.property("overlay") == "commands"
    assert len(window.property("families").toVariant()) == 3
    assert visible_screen() == "homeNow"
    press(7)
    assert window.property("overlay") == "" and not state.firstRun
    press(6, True)
    assert window.property("family") == 1
    assert visible_screen() == "weatherNow"
    press(8, True)
    assert window.property("viewIndex").toVariant() == [0, 1, 0]
    assert visible_screen() == "weatherForecast"
    press(4, True)
    assert window.property("family") == 0
    assert visible_screen() == "homeNow"
    press(8, True)
    assert visible_screen() == "homeDay"
    press(2, True)
    assert visible_screen() == "homeNow"
    press(6, True)
    assert window.property("viewIndex").toVariant() == [0, 1, 0]
    press(5)
    press(9)
    press(3)
    assert window.property("overlay") == "alerts"
    press(7)
    assert window.property("overlay") == "menu"
    press(7)
    assert window.property("overlay") == "detail"
    press(7)
    assert window.property("overlay") == ""
    press(1, True)
    assert window.property("family") == 0
    assert window.property("viewIndex").toVariant()[0] == 0
    assert visible_screen() == "homeNow"
    press(4, True)
    assert window.property("familyId") == "account"
    assert visible_screen() == "accountPanel"
    press(6, True)
    assert window.property("familyId") == "oggi"

    for expected in ("offline", "unavailable", "active"):
        state.cycleDemoWeather()
        assert state.weatherState["status"] == expected
    state.toggleDemoEvent()
    application.processEvents()
    assert window.property("hasEvent")
    state.cycleNightMode()
    assert DashboardState(weather, system, account, demo=True).nightMode == state.nightMode
    press(9)
    press(8)
    press(5)
    assert window.property("overlay") == "settings"
    press(5)
    assert window.property("overlay") == "system"
    quick_window = shiboken6.wrapInstance(shiboken6.getCppPointer(window)[0], QQuickWindow)

    def visual_items(parent: object):
        for child in parent.childItems():
            yield child
            yield from visual_items(child)

    system_row = next(item for item in visual_items(quick_window.contentItem()) if item.objectName() == "systemRow0")
    assert system_row.isVisible(), "system settings are missing"
    press(8)
    press(6)
    assert state.brightnessMode == "manual"
    press(8)
    press(4)
    assert state.manualBrightness == 95
    assert window.property("brightnessPercent") == 95
    for _ in range(20):
        press(4)
    assert state.manualBrightness == 20, "brightness must remain recoverable"
    press(6)
    assert state.manualBrightness == 25
    assert DashboardState(weather, system, account, demo=True).manualBrightness == 25
    state.adjustDisplaySetting(1, 1)
    assert state.brightnessMode == "auto"
    window.setProperty("now", QDateTime(QDate(2026, 9, 30), QTime(23, 0)))
    assert window.property("brightnessPercent") == 65
    window.setProperty("now", QDateTime(QDate(2026, 9, 30), QTime(12, 0)))
    assert window.property("brightnessPercent") == 100
    press(7)
    assert window.property("overlay") == "settings"
    assert not system_row.isVisible(), "system settings leaked into the menu"
    press(8)
    press(5)
    assert window.property("overlay") == "modules"
    assert state.visibleModules == ["oggi", "meteo", "account"]
    assert window.property("modulesIndex") == 1, "focus should start on the first changeable module"
    press(5)
    assert state.visibleModules == ["oggi", "account"]
    assert len(window.property("families").toVariant()) == 2
    press(5)
    assert state.visibleModules == ["oggi", "meteo", "account"]
    press(7)
    press(7)
    press(7)
    press(4, True)
    assert window.property("familyId") == "account"
    assert state.accountState["data"]["windows"]
    assert screens["accountPanel"].property("visible")
    press(9)
    press(5)
    press(8)
    press(5)
    press(8)
    press(5)
    assert state.visibleModules == ["oggi", "meteo"]
    assert window.property("familyId") == "oggi", "hiding the current module must return Home"
    assert visible_screen() == "homeNow"
    assert DashboardState(weather, system, account, demo=True).visibleModules == ["oggi", "meteo"]
    press(5)
    assert state.visibleModules == ["oggi", "meteo", "account"]
    state.toggleModuleVisibility("meteo")
    state.toggleModuleVisibility("account")
    application.processEvents()
    assert state.visibleModules == ["oggi"]
    assert len(window.property("families").toVariant()) == 1
    press(1)
    press(4)
    press(6)
    assert window.property("familyId") == "oggi"
    state.toggleModuleVisibility("meteo")
    state.toggleModuleVisibility("account")
    print("QML load, carousel, module visibility, account, settings and persistence: PASS")


if __name__ == "__main__":
    main()
