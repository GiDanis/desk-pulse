"""HID navigation, team/future/cup detail, workers and offline editorial cache."""

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument("--directory")
parser.add_argument("--capture", action="store_true")
parser.add_argument("--offline-only", action="store_true")
args = parser.parse_args()
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="smartpc-fanta-config-")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.environ["QT_QPA_PLATFORM"] == "offscreen":
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
from PySide6.QtCore import QObject, QSettings, QThreadPool, QUrl, Signal
from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6
from fantacalcio_core import (
    parse_page,
    save_cache,
    presentation as fantasy_data,
    read_cache,
)
from sport_core import (
    fotmob_detail,
    read_cache as read_league,
    save_cache as save_league,
    ProviderError,
)
from sport_team_core import parse_team, save_cache as save_team
from sport import SportService
from app import SystemInfo
from weather import WeatherService
from account import AccountService
from events import EventService
from state import DashboardState
from keypad import KeyDecoder, KEY_POSITIONS

app = QGuiApplication([])
app.setOrganizationName("SmartPC")
app.setApplicationName("Fantacalcio check")
fixtures = Path(__file__).with_name("fixtures")
root = (
    Path(args.directory)
    if args.directory
    else Path(tempfile.mkdtemp(prefix="smartpc-fanta-data-"))
)
root.mkdir(parents=True, exist_ok=True)
if args.directory:
    league = read_league(root / "sport.json")
    page = read_cache(root / "fantacalcio-2026-27-5.json", "2026-27/5")
    assert league and page
else:
    league = json.loads((fixtures / "sport-normalized-sample.json").read_text())
    league["fetchedAt"] = league["standingsFetchedAt"] = time.time()
    index = next(
        i for i, m in enumerate(league["fixtures"]) if m["providerMatchId"] == "5749681"
    )
    league["fixtures"][index] = fotmob_detail(
        json.loads((fixtures / "fantacalcio-fotmob-roma-inter.json").read_text()),
        league["fixtures"][index],
    )
    page = parse_page(
        (fixtures / "fantacalcio-2026-27-5-roma-inter.html").read_text(),
        "2026-27/5",
        time.time(),
    )
    save_cache(root / "fantacalcio-2026-27-5.json", page)
    save_league(root / "sport.json", league)
    team = parse_team(
        json.loads((fixtures / "sport-team-inter.json").read_text()),
        "8636",
        "inter",
        time.time(),
    )
    save_team(root / "sport-team-8636.json", team)
settings = QSettings("SmartPC", "Dashboard")
settings.setValue("sport/season", league["season"])
sport = SportService(
    auto_refresh=False,
    cache_path=root / "sport.json",
    state_path=root / "check-goals.json",
    initial=league,
)
match = next(m for m in league["fixtures"] if m["providerMatchId"] == "5749681")


class Client:
    def __init__(self):
        self.calls = []
        self.pages = {}

    def get(self, key, ttl=300):
        self.calls.append(key)
        time.sleep(0.025)
        if key != "2026-27/5":
            raise ProviderError("Unrecorded matchweek")
        return deepcopy(page)


sport._fantasy.client = Client()


def wait_workers():
    deadline = time.monotonic() + 5
    while (
        sport._fantasy.worker or sport._worker or sport._team.worker
    ) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert not sport._fantasy.worker and not sport._worker and not sport._team.worker
    app.processEvents()


if args.offline_only:
    sport._fantasy.offline = True
    sport.selectFantacalcio(match["canonicalMatchId"])
    assert sport._fantasy.from_cache
    sport._fantasy.refresh()
    wait_workers()
    state = sport._fantasy.moduleState
    assert state["status"] == "offline" and state["data"]["published"]
    counts = [len(t["players"]) for t in state["data"]["teams"]]
    assert counts == [23, 23]
    assert state["data"]["teams"][1]["players"][0]["vote"] == 6.5
    report = {
        "status": "offline",
        "fromCache": state["data"]["fromCache"],
        "players": counts,
        "source": state["source"],
        "scope": "new process, no network, no OS reboot",
    }
    (root / "fantacalcio-offline.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    sport.close()
    raise SystemExit(0)


class Keypad(QObject):
    keyPressed = Signal(int)
    connected = False


keypad = Keypad()
events = EventService(path=":memory:", auto_refresh=False)
state = DashboardState(
    WeatherService(auto_refresh=False),
    SystemInfo(),
    AccountService(path=root / "missing-account.json"),
    events,
    sport=sport,
)
state.markCommandsSeen()
engine = QQmlApplicationEngine()
warnings = []
engine.warnings.connect(lambda values: warnings.extend(str(v) for v in values))
engine.setInitialProperties({"keypad": keypad, "dashboardState": state})
engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
assert engine.rootObjects()
window = shiboken6.wrapInstance(
    shiboken6.getCppPointer(engine.rootObjects()[0])[0], QQuickWindow
)
if os.environ["QT_QPA_PLATFORM"] == "offscreen":
    window.setVisibility(QWindow.Visibility.Windowed)
    window.resize(960, 640)


def value(name):
    v = window.property(name)
    return v.toVariant() if hasattr(v, "toVariant") else v


def capture(name):
    if not args.capture:
        return
    deadline = time.monotonic() + 0.16
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    img = window.grabWindow()
    assert not img.isNull() and img.width() == 960 and img.height() == 640
    assert img.save(str(root / (name + ".png")))


codes = {v: k for k, v in KEY_POSITIONS.items()}
decoder = KeyDecoder()


def press(key):
    decoder.feed(1, 29, 1)
    if key == 1:
        decoder.feed(1, 42, 1)
    pos = decoder.feed(1, codes[key], 1)
    assert pos == key
    decoder.feed(1, codes[key], 0)
    decoder.feed(1, 42, 0)
    decoder.feed(1, 29, 0)
    keypad.keyPressed.emit(pos)
    app.processEvents()


window.setProperty("familyId", "sport")
window.setProperty("sportView", "RISULTATI")
window.setProperty("sportMatchId", match["canonicalMatchId"])
window.setProperty("overlay", "sportDetail")
assert len(value("sportDetailTabs")) == 4
press(6)
press(6)
press(6)
assert value("sportDetailPage") == 3 and value("fantasyData")["published"]
assert value("fantasyState")["source"] == "Redazione Fantacalcio"
assert len(value("fantasyRows")) == 23
capture("fantacalcio-home-starters")
for _ in range(23):
    press(8)
assert value("fantasyPlayerIndex") == 22
capture("fantacalcio-home-bench")
press(5)
assert value("fantasyTeamIndex") == 1 and value("fantasyPlayerIndex") == 0
rows = value("fantasyRows")
assert rows[0]["vote"] == 6.5 and rows[0]["fantavote"] == 4.5
capture("fantacalcio-away-starters")
for _ in range(11):
    press(8)
assert value("fantasyRows")[value("fantasyPlayerIndex")]["group"] == "Subentrati"
capture("fantacalcio-away-substitutes")
for _ in range(12):
    press(8)
capture("fantacalcio-away-bench")
for _ in range(24):
    press(2)
assert value("fantasyPlayerIndex") == -1
press(5)
wait_workers()
assert sport._fantasy.client.calls == ["2026-27/5"]
assert not sport._fantasy.from_cache
press(6)
assert value("sportDetailPage") == 0 and not sport._fantasy.key
press(4)
assert value("sportDetailPage") == 3
# A failed refresh keeps the valid editorial votes.
sport._fantasy.offline = True
sport._fantasy.refresh()
wait_workers()
assert (
    value("fantasyState")["status"] == "offline" and value("fantasyData")["published"]
)
capture("fantacalcio-offline")
press(7)
assert not sport._fantasy.key
# Future Serie A: same tab, no request and no invented scores/grades.
future = next(m for m in league["fixtures"] if m["status"] == "scheduled")
window.setProperty("sportMatchId", future["canonicalMatchId"])
window.setProperty("sportDetailPage", 0)
window.setProperty("overlay", "sportDetail")
press(4)
assert value("sportDetailPage") == 3 and not value("fantasyData")["published"]
assert not value("fantasyRows")
capture("fantacalcio-future")
assert sport._fantasy.client.calls == ["2026-27/5"]
# Favourite detail route uses the same editorial data and tab.
press(7)
sport.setFavourite("inter")
favourite = dict(
    match,
    canonicalMatchId="team:foto:5749681",
    competitionId="football:55",
    providerLeagueId=55,
    competitionName="Serie A",
)
team_rows = sport._team.snapshot["fixtures"]
team_index = next(
    i for i, m in enumerate(team_rows) if m["providerMatchId"] == "5749681"
)
team_rows[team_index] = favourite
sport._team.changed.emit()
window.setProperty("sportTeamDetail", True)
window.setProperty("sportMatchId", "team:foto:5749681")
window.setProperty("sportDetailPage", 0)
window.setProperty("overlay", "sportDetail")
press(4)
assert value("sportDetailPage") == 3 and value("fantasyData")["published"]
assert len(value("fantasyRows")) == 23
capture("fantacalcio-favourite-route")
# Cups/amichevoli never have the fantasy tab or make vote requests.
press(7)
cup = next(m for m in sport._team.snapshot["fixtures"] if m["providerLeagueId"] == 42)
window.setProperty("sportTeamDetail", True)
window.setProperty("sportMatchId", cup["canonicalMatchId"])
window.setProperty("overlay", "sportDetail")
window.setProperty("sportDetailPage", 0)
assert len(value("sportDetailTabs")) == 3
press(4)
assert value("sportDetailPage") == 2 and not sport._fantasy.key
assert sport._fantasy.client.calls == ["2026-27/5"]
press(1)
assert value("familyId") == "oggi" and not sport._fantasy.key
# A response of the previous matchweek cannot replace the current selection.
sport._fantasy.offline = False
sport._fantasy.auto = True
sport.selectFantacalcio(match["canonicalMatchId"])
sport._fantasy.refresh()
new_match = dict(match, canonicalMatchId="test-next-matchweek", round="4")
sport._fantasy.set_match(new_match)
wait_workers()
assert (
    sport._fantasy.key == "2026-27/4"
    and sport._fantasy.match["canonicalMatchId"] == "test-next-matchweek"
)
assert sport._fantasy.error and not sport._fantasy.moduleState["data"]["published"]
sport._fantasy.clear()
sport._fantasy.auto = False
assert not warnings, warnings
report = {
    "status": "PASS",
    "source": value("fantasyState")["source"],
    "playersPerTeam": 23,
    "qmlWarnings": warnings,
    "checks": [
        "HID four tabs",
        "both teams/all starters/subs/bench",
        "base and fantavote editorial source",
        "worker/manual refresh",
        "failed refresh preserves votes",
        "future without vote requests",
        "favourite route",
        "cup excluded",
        "Home/back regression",
    ],
}
(root / "fantacalcio-ui.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report))
sport.close()
events.close()
QThreadPool.globalInstance().waitForDone(3000)
app.processEvents()
