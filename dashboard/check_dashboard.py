"""Fast QML regression check for navigation and the v0.3 state contract."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

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
from events import EventService  # noqa: E402
from state import DashboardState  # noqa: E402
from weather import WeatherService  # noqa: E402
from weather_alerts import BulletinProvider  # noqa: E402
from check_weather_alerts import bulletin_fixture  # noqa: E402


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
    events = EventService(path=Path(os.environ["XDG_CONFIG_HOME"]) / "events.sqlite3", auto_refresh=False)
    keypad = FakeKeypad()
    state = DashboardState(weather, system, account, events, demo=True)
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

    def as_value(value: object):
        return value.toVariant() if hasattr(value, "toVariant") else value

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
    assert window.property("viewIndex").toVariant() == [0, 1, 0, 0, 0, 0]
    assert visible_screen() == "weatherForecast"
    press(4, True)
    assert window.property("family") == 0
    assert visible_screen() == "homeNow"
    press(8, True)
    assert visible_screen() == "homeDay"
    press(2, True)
    assert visible_screen() == "homeNow"
    press(6, True)
    assert window.property("viewIndex").toVariant() == [0, 1, 0, 0, 0, 0]
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
    assert window.property("overlay") == "appearance"
    press(7)
    press(8)
    press(5)
    assert window.property("overlay") == "system"
    quick_window = shiboken6.wrapInstance(shiboken6.getCppPointer(window)[0], QQuickWindow)

    def visual_items(parent: object):
        for child in parent.childItems():
            yield child
            yield from visual_items(child)

    system_row = next(item for item in visual_items(quick_window.contentItem()) if item.objectName() == "systemRow0")
    assert system_row.isVisible(), "system settings are missing"
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
    press(1)
    events.set_quiet(False, 22 * 60, 7 * 60)
    events.set_demo_scenario("banner")
    application.processEvents()
    assert as_value(window.property("bannerEvent"))["title"] == "Avviso di prova"
    small_banner = next(item for item in visual_items(quick_window.contentItem()) if item.objectName() == "eventBanner")
    large_banner = next(item for item in visual_items(quick_window.contentItem()) if item.objectName() == "eventLargeBanner")
    unread_badge = next(item for item in visual_items(quick_window.contentItem()) if item.objectName() == "unreadAlertsBadge")
    assert small_banner.isVisible() and not large_banner.isVisible()
    assert not unread_badge.isVisible(), "unread badge duplicated a visible banner"
    family_before = window.property("familyId")
    views_before = as_value(window.property("viewIndex"))
    events.set_demo_scenario("banner grande")
    application.processEvents()
    assert as_value(window.property("bannerEvent"))["bannerSize"] == "large"
    assert large_banner.isVisible() and not small_banner.isVisible()
    assert large_banner.height() > small_banner.height()
    assert window.property("familyId") == family_before
    assert as_value(window.property("viewIndex")) == views_before
    press(3)
    assert window.property("overlay") == "alerts"
    assert not large_banner.isVisible(), "large banner covered the inbox"
    assert len(as_value(window.property("alertItems"))) == 1
    press(5)
    assert window.property("overlay") == "alertDetail"
    assert window.property("unreadAlertCount") == 0
    press(7)
    assert window.property("overlay") == "alerts"
    press(7)
    press(6)
    assert window.property("familyId") == "meteo"
    events.set_demo_scenario("urgente")
    application.processEvents()
    assert as_value(window.property("urgentEvent"))["title"] == "Allerta prioritaria di prova"
    press(7)
    assert window.property("familyId") == "meteo" and window.property("overlay") == ""
    events.set_demo_scenario("nessuno")

    press(9)
    window.setProperty("menuIndex", 1)
    press(5)
    window.setProperty("settingsIndex", 3)
    press(5)
    assert window.property("overlay") == "notifications"
    press(5)
    assert window.property("overlay") == "notificationQuiet"
    was_enabled = state.quietHoursEnabled
    press(5)
    assert state.quietHoursEnabled != was_enabled
    press(5)  # Enable the time range before adjusting it.
    press(8)
    old_start = state.quietStartMinute
    press(6)
    assert state.quietStartMinute == (old_start + 15) % 1440
    persisted = DashboardState(weather, system, account, demo=True)
    assert persisted.quietHoursEnabled == state.quietHoursEnabled
    assert persisted.quietStartMinute == state.quietStartMinute
    press(7)
    press(8)
    press(5)
    assert window.property("overlay") == "notificationCategories"
    assert window.property("categoryIndex") == 0
    old_weather_interruptions = state.weatherInterruptions
    press(5)
    assert state.weatherInterruptions != old_weather_interruptions
    assert DashboardState(weather, system, account, demo=True).weatherInterruptions == state.weatherInterruptions
    events.set_demo_scenario("urgente")
    application.processEvents()
    press(7)
    assert window.property("overlay") == "notificationCategories"
    assert window.property("categoryIndex") == 0, "urgent notice lost settings focus"
    events.set_demo_scenario("nessuno")
    press(1)
    events.set_quiet(False, 22 * 60, 7 * 60)
    stamp = time.time()
    account_snapshot = {"status": "active", "updatedAt": stamp, "data": {"windows": [
        {"label": "Codex", "usedPercent": 84, "windowDurationMins": 300, "resetsAt": stamp + 3600}]}}
    events.ingest_account(account_snapshot, 80, 95)
    assert events.eventState["inbox"][0]["priority"] == 1
    assert window.property("unreadAlertCount") == 1 and unread_badge.isVisible()
    press(8)
    assert visible_screen() == "homeDay" and unread_badge.isVisible()
    press(2)
    account_snapshot["data"]["windows"][0]["usedPercent"] = 96
    events.ingest_account(account_snapshot, 80, 95)
    assert events.eventState["visibleBanner"]["title"] == "Uso Codex: 96%"
    assert not unread_badge.isVisible()
    QTimer.singleShot(8500, application.quit)
    application.exec()
    assert not events.eventState["visibleBanner"], "banner did not finish after eight seconds"
    assert unread_badge.isVisible(), "unread notice disappeared with its banner"
    press(3)
    assert window.property("unreadAlertCount") == 1, "opening the inbox marked notices as read"
    assert not unread_badge.isVisible()
    press(5)
    assert window.property("unreadAlertCount") == 0
    press(7)
    press(7)
    assert not unread_badge.isVisible()
    events.ingest_account(account_snapshot, 80, 95)
    assert not events.eventState["visibleBanner"], "unchanged account snapshot repeated the banner"
    account_snapshot["data"]["windows"][0]["usedPercent"] = 20
    events.ingest_account(account_snapshot, 80, 95)
    assert not events.eventState["inbox"]

    with tempfile.TemporaryDirectory() as directory:
        cache_path = Path(directory) / "dpc-bulletin.json"
        stamp = time.time()
        responses = bulletin_fixture(stamp)
        with patch("weather_alerts._read", side_effect=lambda url, _: responses[url]):
            snapshot = BulletinProvider(cache_path).refresh(stamp)
        cached_service = EventService(path=Path(directory) / "events.sqlite3", auto_refresh=False)
        assert cached_service.eventState["sourceFromCache"]
        assert cached_service.eventState["sourceCheckedAt"] == stamp
        assert len(cached_service.eventState["inbox"]) == 2, "cache failed to recover alerts without an existing database"
        current_id = next(event["id"] for event in cached_service.eventState["inbox"] if not event["upcoming"])
        cached_service._engine.mark_notified(current_id)
        cached_service.markSeen(current_id)
        with patch("weather_alerts._read", side_effect=OSError("offline")) as read:
            restarted = EventService(path=Path(directory) / "events.sqlite3", auto_refresh=False)
            read.assert_not_called()
        restarted._on_weather_finished(None, "offline simulato")
        assert "cache" in restarted.eventState["sourceStatus"]
        assert next(event["seen"] for event in restarted.eventState["inbox"] if event["id"] == current_id)
        assert not restarted.eventState["banner"], "offline restart repeated an already delivered banner"
        assert len(restarted.eventState["inbox"]) == 2
        # A newer all-clear applied to SQLite must survive a failed cache write.
        responses = bulletin_fixture(stamp + 60, colour="NESSUNA ALLERTA")
        with patch("weather_alerts._read", side_effect=lambda url, _: responses[url]), \
                patch("weather_alerts.os.replace", side_effect=OSError("non scrivibile")):
            empty = BulletinProvider(cache_path).refresh(stamp + 60)
        assert empty.cache_error
        restarted._on_weather_finished(empty, None)
        assert not restarted.eventState["inbox"]
        restarted_again = EventService(path=Path(directory) / "events.sqlite3", auto_refresh=False)
        assert not restarted_again.eventState["inbox"], "older cache resurrected a cancelled alert"
        for service in (cached_service, restarted, restarted_again):
            service._tick_timer.stop()
            service._poll_timer.stop()
            service._banner_timer.stop()
            service._engine.close()
    print("QML, both banners, unread Home badge, cached offline restart and notification settings: PASS")


if __name__ == "__main__":
    main()
