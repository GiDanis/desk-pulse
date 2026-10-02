"""Actual QML + physical HID decoder routing; isolated provider snapshots."""

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="smartpc-racing-ui-")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
from PySide6.QtCore import QObject, QUrl, Signal, QThreadPool, QDateTime
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from app import SystemInfo
from account import AccountService
from events import EventService
from weather import WeatherService
from sport import SportService
from theme_test_support import configure_appearance, assert_theme_keeps_selection
from state import DashboardState
from motorsport import MotorsportService
from motorsport_core import save_cache
from keypad import KeyDecoder, KEY_POSITIONS


class Keypad(QObject):
    keyPressed = Signal(int)
    connected = False


def main():
    app = QGuiApplication([])
    app.setOrganizationName("SmartPC")
    app.setApplicationName("Motorsport check")
    directory = Path(os.environ["XDG_CONFIG_HOME"])
    fixtures = Path(__file__).with_name("fixtures")
    sources = {
        kind: json.loads(
            (fixtures / ("racing-" + kind + "-normalized.json")).read_text()
        )["snapshot"]
        for kind in ("f1", "motogp")
    }
    # Fixture sessions must stay in their acquisition-time context. Otherwise
    # a session passes while the test ages, changing the expected empty state.
    fixture_clock = patch('time.time', return_value=min(data['fetchedAt'] for data in sources.values()))
    fixture_clock.start()
    services = {
        kind: MotorsportService(
            kind, auto_refresh=False, cache_directory=directory, initial=data
        )
        for kind, data in sources.items()
    }
    # Network failures are intentionally exercised by real workers, rather than
    # silently supplying responses in the production services.
    for service in services.values():
        service._offline = True
    sport = SportService(
        auto_refresh=False,
        cache_path=directory / "sport.json",
        state_path=directory / "goals.json",
    )
    events = EventService(path=directory / "events.sqlite3", auto_refresh=False)
    state = DashboardState(
        WeatherService(auto_refresh=False),
        SystemInfo(),
        AccountService(path=directory / "missing.json"),
        events,
        sport=sport,
        racing=services,
    )
    state.markCommandsSeen()
    configure_appearance(state)
    keypad = Keypad()
    engine = QQmlApplicationEngine()
    errors = []
    engine.warnings.connect(lambda warnings: errors.extend(str(w) for w in warnings))
    engine.setInitialProperties({"keypad": keypad, "dashboardState": state})
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
    assert engine.rootObjects()
    window = engine.rootObjects()[0]
    window.findChild(QObject, 'clockTimer').setProperty('running', False)
    window.setProperty('now', QDateTime.fromSecsSinceEpoch(int(min(data['fetchedAt'] for data in sources.values()))))

    def value(key):
        item = window.property(key)
        return item.toVariant() if hasattr(item, "toVariant") else item

    decoder = KeyDecoder()
    codes = {position: code for code, position in KEY_POSITIONS.items()}

    def press(key):
        decoder.feed(1, 29, 1)
        if key == 1:
            decoder.feed(1, 42, 1)
        decoded = decoder.feed(1, codes[key], 1)
        assert decoded == key
        decoder.feed(1, codes[key], 0)
        decoder.feed(1, 42, 0)
        decoder.feed(1, 29, 0)
        keypad.keyPressed.emit(decoded)
        app.processEvents()

    def settle():
        deadline = time.monotonic() + 3
        while any(s._worker for s in services.values()) and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.005)
        assert not any(s._worker for s in services.values())
        app.processEvents()

    press(4)
    assert value("familyId") == "motogp"
    press(4)
    assert value("familyId") == "f1"
    for kind in ("f1", "motogp"):
        assert value("familyId") == kind and value("racingView") == "PROGRAMMA"
        press(5)
        assert value("overlay") == "racingList"
        selected_gp = value("racingRows")[value("racingIndex")]["id"]
        press(5)
        settle()
        assert (
            value("overlay") == "racingEvent" and value("racingEventId") == selected_gp
        )
        assert len(value("racingRows")) >= 5
        press(6)
        assert value("racingEventPage") == 1 and value("overlay") == "racingEvent"
        press(6)
        assert value("racingEventPage") == 2
        press(6)
        assert value("racingEventPage") == 0
        press(5)
        settle()
        assert value("overlay") == "racingSession"
        selected_session = value("racingSessionId")
        assert_theme_keeps_selection(app,window,state,("overlay","racingEventId","racingSessionId","racingIndex","racingFocusedId","racingDetailPage"))
        assert "ancora iniziare" in window.findChild(
            QObject, "racingEmptyResult"
        ).property("text"), (kind, value('racingSession'), window.findChild(QObject, 'racingEmptyResult').property('text'))
        press(6)
        assert value("racingDetailPage") == 1
        press(3)
        press(7)
        assert value("racingDetailPage") == 1
        press(7)
        assert value("overlay") == "racingEvent"
        assert value("racingRows")[value("racingIndex")]["id"] == selected_session
        press(7)
        assert value("overlay") == "racingList"
        assert value("racingRows")[value("racingIndex")]["id"] == selected_gp
        press(7)
        press(8)
        assert value("racingView") == "RISULTATI"
        press(5)
        press(5)
        settle()
        assert value("overlay") == "racingEvent"
        rows = value("racingRows")
        race_index = next(i for i, s in enumerate(rows) if s["kind"] == "RAC")
        window.setProperty("racingIndex", race_index)
        press(5)
        settle()
        count = len(value("racingSession")["results"])
        assert count > 20
        for _ in range(count + 1):
            press(8)
        assert value("racingResultIndex") == count - 1
        selected_driver = value("racingSession")["results"][count - 1]["id"]
        press(5)
        settle()
        assert (
            value("overlay") == "racingDriver"
            and value("racingDriverId") == selected_driver
        )
        for _ in range(len(value("racingDriverTabs"))):
            press(6)
        assert value("racingDriverPage") == 0
        press(7)
        settle()
        assert (
            value("overlay") == "racingSession"
            and value("racingResultIndex") == count - 1
        )
        press(9)
        press(7)
        assert value("racingResultIndex") == count - 1
        press(7)
        press(7)
        press(7)
        press(8)
        assert value("racingView") == "CLASSIFICA"
        press(5)
        assert value("overlay") == "racingTable"
        assert "Classifica" in window.findChild(QObject, "racingFooter").property(
            "text"
        )
        count = len(value("racingRows"))
        for _ in range(count + 1):
            press(8)
        assert value("racingIndex") == count - 1
        press(3)
        press(7)
        assert value("racingIndex") == count - 1
        if kind == "f1":
            press(6)
            assert value("racingStandingTab") == 1
            assert len(value("racingRows")) == len(sources[kind]["constructors"])
            for _ in range(12):
                press(8)
            press(4)
            assert value("racingStandingTab") == 0 and value("racingIndex") == 0
        press(7)
        if kind == "f1":
            press(6)
    # Each discipline remembers its view when changing family.
    press(4)
    assert value("racingView") == "CLASSIFICA"
    press(6)
    assert value("racingView") == "CLASSIFICA"
    # A current active stream adds a timing view; disconnect keeps the viewed
    # rows available without a Live badge or an unsolicited page jump.
    press(4)
    f1 = services["f1"]
    # This phase injects a connected stream into a service with auto-refresh
    # disabled. Its normal age tick correctly calls ensure(False), which would
    # disconnect that synthetic stream at an arbitrary point between keypresses.
    f1._age.stop()
    f1._offline = False
    f1._error = ""
    now = time.time()
    timing = f1._timing.state
    timing.apply(
        "SessionInfo",
        {
            "Key": 900,
            "Name": "Race",
            "StartDate": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 300)),
        },
        now,
    )
    timing.apply("SessionStatus", {"Status": "Started"}, now)
    timing.apply(
        "DriverList", {"1": {"FullName": "Test driver", "TeamName": "Test team"}}, now
    )
    timing.apply(
        "TimingData",
        {"Lines": {"1": {"Position": "1", "BestLapTime": {"Value": "1:20.000"}}}},
        now,
    )
    timing.connected = True
    f1.changed.emit()
    app.processEvents()
    press(2)
    press(2)
    assert value("racingView") == "IN CORSO"
    assert not value("racingData")["live"]["isLive"]
    press(5)
    assert value("overlay") == "racingTiming" and len(value("racingRows")) == 1
    press(6)
    assert value("racingTimingPage") == 1
    press(6)
    assert value("racingTimingPage") == 2
    press(6)
    press(5)
    assert value("overlay") == "racingDriver" and value("racingDriverLive")
    press(7)
    assert value("overlay") == "racingTiming"
    press(7)
    timing.connected = False
    f1.changed.emit()
    app.processEvents()
    assert (
        value("racingView") == "IN CORSO" and not value("racingData")["live"]["active"]
    )
    f1._age.start()
    press(6)
    press(9)
    press(8)
    press(5)
    assert value("overlay") == "settings"
    for _ in range(5):
        press(8)
    assert value("settingsIndex") == 5
    press(5)
    assert value("overlay") == "integrations"
    press(8)
    press(8)
    press(5)
    assert (
        value("overlay") == "racingSettings" and value("racingSettingsKind") == "motogp"
    )
    press(8)
    press(5)
    assert services["motogp"].moduleState["data"]["showOnHome"]
    press(1)
    press(4)
    assert value("familyId") == "motogp"
    state.toggleModuleVisibility("motogp")
    app.processEvents()
    assert value("familyId") != "motogp"
    state.toggleModuleVisibility("motogp")
    app.processEvents()
    # Cold cache, true worker failure, year selection and year mismatch rejection.
    for kind, service in services.items():
        save_cache(directory / (kind + "-2026.json"), sources[kind])
        restarted = MotorsportService(
            kind, auto_refresh=False, cache_directory=directory
        )
        assert restarted.moduleState["data"]["fromCache"] and not restarted.moduleState[
            "data"
        ]["live"].get("isLive")
        restarted._offline = True
        restarted.refresh()
        services["test"] = restarted
        settle()
        assert (
            restarted.moduleState["status"] == "offline"
            and restarted.moduleState["data"]["standings"]
        )
        previous = deepcopy(sources[kind])
        previous["year"] = 2025
        save_cache(directory / (kind + "-2025.json"), previous)
        restarted.adjust(0, 1)
        settle()
        assert restarted.moduleState["data"]["selectedYear"] == 2025
        assert restarted.moduleState["data"]["fromCache"]
        restarted.close()
        del services["test"]
        service.close()
    events.close()
    QThreadPool.globalInstance().waitForDone(3000)
    assert not errors, errors
    fixture_clock.stop()
    print(
        "Motorsport QML: HID routing, F1/MotoGP, GP/session focus, future empty states, full results/standings, constructors, bookmarks, settings pages, hidden modules, offline/current and previous year PASS"
    )


if __name__ == "__main__":
    main()
