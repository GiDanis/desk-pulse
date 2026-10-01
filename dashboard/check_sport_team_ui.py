"""Real HID routing for favourite hub, plus isolated board captures/offline restart."""

import argparse
import json
import os
from pathlib import Path
import tempfile
import time
from copy import deepcopy

parser = argparse.ArgumentParser()
parser.add_argument("--directory")
parser.add_argument("--capture", action="store_true")
parser.add_argument("--offline-only", action="store_true")
args = parser.parse_args()
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="smartpc-team-check-")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.environ["QT_QPA_PLATFORM"] == "offscreen":
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
from PySide6.QtCore import QObject, QSettings, QThreadPool, QUrl, Signal
from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6
from sport_core import (
    read_cache as read_league,
    save_cache as save_league,
    ProviderError,
)
from sport_team_core import parse_team, save_cache, read_cache
from sport import SportService
from app import SystemInfo
from weather import WeatherService
from account import AccountService
from events import EventService
from state import DashboardState
from keypad import KeyDecoder, KEY_POSITIONS

app = QGuiApplication([])
app.setOrganizationName("SmartPC")
app.setApplicationName("Team check")
fixtures = Path(__file__).with_name("fixtures")
root = (
    Path(args.directory)
    if args.directory
    else Path(tempfile.mkdtemp(prefix="smartpc-team-data-"))
)
if not args.directory:
    league = json.loads((fixtures / "sport-normalized-sample.json").read_text())
    league["fetchedAt"] = league["standingsFetchedAt"] = time.time()
    save_league(root / "sport.json", league)
    profile = parse_team(
        json.loads((fixtures / "sport-team-inter.json").read_text()),
        "8636",
        "inter",
        time.time(),
    )
    save_cache(root / "sport-team-8636.json", profile)
else:
    league = read_league(root / "sport.json")
    profile = read_cache(root / "sport-team-8636.json", "8636", "inter")
assert profile and league
# Production auto-refresh must schedule another check after a successful worker.
from types import SimpleNamespace
from sport_team import FavouriteTeamService

poll = FavouriteTeamService(root, auto_refresh=False)
poll.select_team("8636", "inter")
poll.auto = True
poll.worker = SimpleNamespace(
    provider_id="8636", team_id="inter", detail_only=False, match_id="", cache_error=""
)
poll._finished(deepcopy(profile), None)
assert poll.timer.isActive() and 60000 <= poll.timer.interval() <= 21600000
poll.close()

settings = QSettings("SmartPC", "Dashboard")
settings.setValue("sport/season", league["season"])
if args.offline_only:
    settings.setValue("sport/favourite", "inter")
    settings.setValue("sport/fotmobTeamId/inter", "8636")
    os.environ["SMARTPC_SPORT_OFFLINE"] = "1"
sport = SportService(
    auto_refresh=False,
    cache_path=root / "sport.json",
    state_path=root / "check-goals.json",
    initial=None if args.offline_only else league,
)


def wait_workers():
    deadline = time.monotonic() + 8
    while (sport._worker or sport._team.worker) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert not sport._worker and not sport._team.worker
    app.processEvents()


if args.offline_only:
    assert sport.moduleState["data"]["favourite"] == "inter"
    assert sport._team.from_cache
    sport._team.refresh()
    wait_workers()
    team = sport.moduleState["data"]["favouriteTeam"]
    assert team["status"] == "offline" and len(team["data"]["fixtures"]) == len(
        profile["fixtures"]
    )
    assert len(team["data"]["squad"]) == len(profile["squad"])
    assert not any(m["isLive"] for m in team["data"]["fixtures"])
    report = {
        "status": team["status"],
        "fromCache": team["data"]["fromCache"],
        "fixtures": len(team["data"]["fixtures"]),
        "squad": len(team["data"]["squad"]),
        "favourite": "inter",
        "scope": "new process with network disabled; no OS reboot",
    }
    (root / "team-offline.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    sport.close()
    raise SystemExit(0)


class Client:
    def get(self, url):
        mid = url.split("matchId=")[-1]
        time.sleep(0.02)
        if args.directory:
            response = json.loads((root / "team-responses.json").read_text()).get(url)
            if response:
                return response[0], response[1]
        path = fixtures / ("sport-team-detail-" + mid + ".json")
        if path.exists():
            return json.loads(path.read_text()), time.time()
        raise ProviderError("Detail unavailable in recorded responses")


sport._team.client = Client()


class Keypad(QObject):
    keyPressed = Signal(int)
    connected = False


keypad = Keypad()
events = EventService(path=":memory:", auto_refresh=False)
weather = WeatherService(auto_refresh=False)
account = AccountService(path=root / "missing-account.json")
state = DashboardState(weather, SystemInfo(), account, events, sport=sport)
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
    result = window.property(name)
    return result.toVariant() if hasattr(result, "toVariant") else result


def settle():
    deadline = time.monotonic() + 0.12
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)


def capture(name):
    if not args.capture:
        return
    settle()
    img = window.grabWindow()
    assert not img.isNull() and img.width() == 960 and img.height() == 640
    assert img.save(str(root / (name + ".png")))


decoder = KeyDecoder()
codes = {v: k for k, v in KEY_POSITIONS.items()}


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


window.setProperty("familyId", "sport")
window.setProperty("sportView", "CLASSIFICA")
press(8)
assert value("sportView") == "LA MIA SQUADRA"
capture("team-empty")
press(5)
assert value("overlay") == "sportTeamPicker"
inter = next(i for i, t in enumerate(value("teamPickerRows")) if t["id"] == "inter")
for _ in range(inter):
    press(8)
capture("team-picker")
press(5)
assert (
    value("overlay") == "sportTeam"
    and sport.moduleState["data"]["favourite"] == "inter"
)
assert value("teamData")["calendarScope"] == "team"
count = len(value("teamRows"))
assert count > 3
capture("team-calendar")
press(7)
capture("team-summary")
press(5)
assert value("overlay") == "sportTeam"
# Open next friendly, navigate detail and preserve selected row on return.
selected = value("teamRows")[0]["canonicalMatchId"]
press(5)
wait_workers()
assert (
    value("overlay") == "sportDetail"
    and value("sportMatch")["canonicalMatchId"] == selected
)
assert value("sportMatch")["homeScore"] is None and value("sportMatch")["venue"]
capture("team-future-detail")
press(6)
capture("team-future-stats")
press(7)
assert value("overlay") == "sportTeam" and value("teamIndex") == 0
# Open a Champions League match with its distinct parent league identifier.
cl = next(i for i, m in enumerate(value("teamRows")) if m["providerLeagueId"] == 42)
for _ in range(cl):
    press(8)
selected = value("teamRows")[cl]["canonicalMatchId"]
press(5)
wait_workers()
assert (
    value("sportMatch")["canonicalMatchId"] == selected
    and not value("teamData")["detailError"]
)
capture("team-champions-detail")
press(7)
assert value("teamIndex") == cl
# Latest requested match is fetched after the worker already running.
sport._team.select_match("team:foto:6367342")
sport._team.select_match("team:foto:6106251")
wait_workers()
assert sport._team.selection == "team:foto:6106251"
assert sport._team.snapshot["detailErrorMatchId"] == "team:foto:6106251"
assert not sport._team.snapshot["detailError"]
sport._team.clear_selection()
# Every future is reachable, including dates still to be confirmed.
for _ in range(count):
    press(8)
assert value("teamIndex") == count - 1
capture("team-calendar-last")
for _ in range(count):
    press(2)
assert value("teamIndex") == -1
press(6)
assert value("teamSerieAOnly")
assert all(m["providerLeagueId"] == 55 for m in value("teamRows"))
capture("team-filter-serie-a")
press(4)
press(8)
press(6)
assert value("teamTab") == 1 and value("teamRows")
capture("team-results")
press(6)
assert value("teamTab") == 2
assert any(r["value"] == "Cristian Chivu" for r in value("teamRows"))
capture("team-info")
press(8)
press(8)
press(8)
capture("team-info-stadium")
press(6)
assert value("teamTab") == 3 and len(value("teamRows")) == 25
capture("team-squad")
for _ in range(25):
    press(8)
assert value("teamIndex") == 24
capture("team-squad-last")
# Preferences and cache survive a new service without touching production settings.
again = SportService(
    auto_refresh=False,
    cache_path=root / "sport.json",
    state_path=root / "other-goals.json",
)
assert again.moduleState["data"]["favourite"] == "inter" and again._team.from_cache
again.close()
# Removing the favourite is reachable through INFO.
press(4)
assert value("teamTab") == 2
press(5)
assert value("overlay") == "sportTeamPicker"
for _ in range(21):
    press(2)
press(5)
assert sport.moduleState["data"]["favourite"] == ""
assert value("overlay") == "sportTeam"
press(5)
assert value("overlay") == "sportTeamPicker"
press(7)
press(7)
assert value("overlay") == ""
# Home and existing Serie A routes still work.
press(1)
assert value("familyId") == "oggi" and not value("sportTeamDetail")
window.setProperty("familyId", "sport")
window.setProperty("sportView", "CLASSIFICA")
press(5)
assert value("overlay") == "sportTable"
assert not warnings, warnings
report = {
    "status": "PASS",
    "futureFixtures": count,
    "allFixtures": len(profile["fixtures"]),
    "competitions": sorted({m["competitionName"] for m in profile["fixtures"]}),
    "squad": len(profile["squad"]),
    "qmlWarnings": warnings,
    "checks": [
        "HID picker/save/remove",
        "all futures and TBD",
        "multi-competition details",
        "filter",
        "tab navigation and full squad",
        "back preserves focus",
        "preferences and cache restart",
        "Serie A table and Home regression",
    ],
}
(root / "team-ui.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report))
sport.close()
events.close()
QThreadPool.globalInstance().waitForDone(3000)
app.processEvents()
