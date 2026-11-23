"""Real public data, isolated preferences, cold cache and 960x640 captures."""

import argparse
import json
import os
from pathlib import Path
import tempfile
import time

parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=("fetch", "capture", "offline"), required=True)
parser.add_argument("--directory", required=True)
args = parser.parse_args()
root = Path(args.directory)
root.mkdir(parents=True, exist_ok=True)
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="smartpc-racing-details-")

from motorsport_core import MotorClient, refresh, load_event, present, save_cache
from racing_details import load_driver

if args.mode == "fetch":

    class Recording(MotorClient):
        def __init__(self):
            super().__init__()
            self.responses = {}

        def get(self, url):
            response = super().get(url)
            self.responses[url] = response
            return response

    client = Recording()
    f1 = refresh(client, "f1", 2025)
    event = present(f1, time.time())["lastEvent"]
    fp = next(s for s in event["sessions"] if s["kind"] == "FP1")
    f1 = load_event(client, f1, event["id"], fp["id"])
    event = next(e for e in f1["events"] if e["id"] == event["id"])
    practice = next(s for s in event["sessions"] if s["kind"] == "FP1")
    assert len(practice["results"]) >= 20, practice.get("extraError")
    load_driver(client, f1, event["id"], practice["id"], practice["results"][0]["id"])
    race = next(s for s in event["sessions"] if s["kind"] == "RAC")
    f1 = load_driver(client, f1, event["id"], race["id"], race["results"][0]["id"])
    winner = race["results"][0]
    assert (
        winner["pitStops"]
        and len(winner["lapTimes"]) == winner["laps"]
        and winner["stints"]
    ), winner.get("extraError")
    # Sprint qualifying has multiple durations, independent of race results.
    sprint_event = next(
        e for e in f1["events"] if any(s["kind"] == "SQ" for s in e["sessions"])
    )
    sq = next(s for s in sprint_event["sessions"] if s["kind"] == "SQ")
    f1 = load_event(client, f1, sprint_event["id"], sq["id"])
    sprint_event = next(e for e in f1["events"] if e["id"] == sprint_event["id"])
    sq = next(s for s in sprint_event["sessions"] if s["kind"] == "SQ")
    assert sq["results"], sq.get("extraError")
    moto = refresh(client, "motogp", 2026)
    last = present(moto, time.time())["lastEvent"]
    assert last["infoRows"] and any(s.get("conditions") for s in last["sessions"])
    race_m = next(s for s in last["sessions"] if s["kind"] == "RAC")
    assert race_m["results"][0]["bike"] and race_m.get("records")
    for kind, data in (("f1", f1), ("motogp", moto)):
        save_cache(root / (kind + "-" + str(data["year"]) + ".json"), data)
    (root / "responses.json").write_text(
        json.dumps(client.responses, ensure_ascii=False)
    )
    report = {
        "f1_gp": event["name"],
        "f1_practice_rows": len(practice["results"]),
        "f1_sprint_qualifying_rows": len(sq["results"]),
        "f1_driver": winner["name"],
        "pit_stops": len(winner["pitStops"]),
        "lap_times": len(winner["lapTimes"]),
        "stints": len(winner["stints"]),
        "moto_gp": last["name"],
        "moto_circuit_fields": len(last["infoRows"]),
        "moto_records": len(race_m["records"]),
        "moto_conditions": race_m.get("conditions"),
        "requests": sum(client.request_count.values()),
        "accounts": "none",
    }
    (root / "online.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0)

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, QThreadPool, QSettings
from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6
from motorsport import MotorsportService

app = QGuiApplication([])
app.setOrganizationName("SmartPC")
app.setApplicationName("Racing details check")
sources = {
    k: json.loads((root / (k + "-" + str(y) + ".json")).read_text())["snapshot"]
    for k, y in (("f1", 2025), ("motogp", 2026))
}
for k, d in sources.items():
    QSettings("SmartPC", "Dashboard").setValue("motorsport/" + k + "/year", d["year"])
services = {
    k: MotorsportService(k, auto_refresh=False, cache_directory=root, initial=d)
    for k, d in sources.items()
}

if args.mode == "offline":
    from motorsport_core import read_cache

    report = {}
    for k, y in (("f1", 2025), ("motogp", 2026)):
        data = read_cache(root / f"{k}-{y}.json", k)
        view = present(data, time.time(), from_cache=True)
        event = view["lastEvent"]
        race = next(s for s in event["sessions"] if s["kind"] == "RAC")
        assert race["results"][0]["detailRows"]
        if k == "f1":
            assert race["results"][0]["stints"] and race["results"][0]["lapTimes"]
        else:
            assert race["conditions"] and event["circuitData"]
        report[k] = {
            "circuit_rows": len(event["infoRows"]),
            "driver_rows": len(race["results"][0]["detailRows"]),
            "from_cache": view["fromCache"],
        }
    (root / "offline.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    for s in services.values():
        s.close()
    raise SystemExit(0)

responses = json.loads((root / "responses.json").read_text())


class Replay:
    def get(self, url):
        from sport_core import ProviderError

        if url not in responses:
            raise ProviderError("Risposta non raccolta")
        return responses[url]


for s in services.values():
    s._client = Replay()

from app import SystemInfo
from account import AccountService
from events import EventService
from weather import WeatherService
from sport import SportService
from state import DashboardState


class Keypad(QObject):
    keyPressed = Signal(int)
    connected = False


keypad = Keypad()
sport = SportService(auto_refresh=False)
events = EventService(path=":memory:", auto_refresh=False)
state = DashboardState(
    WeatherService(auto_refresh=False),
    SystemInfo(),
    AccountService(),
    events,
    sport=sport,
    racing=services,
)
state.markCommandsSeen()
engine = QQmlApplicationEngine()
errors = []
engine.warnings.connect(lambda ws: errors.extend(str(w) for w in ws))
engine.setInitialProperties({"keypad": keypad, "dashboardState": state})
engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
assert engine.rootObjects()
window = shiboken6.wrapInstance(
    shiboken6.getCppPointer(engine.rootObjects()[0])[0], QQuickWindow
)
if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    window.setVisibility(QWindow.Visibility.Windowed)
    window.resize(960, 640)


def value(key):
    v = window.property(key)
    return v.toVariant() if hasattr(v, "toVariant") else v


def press(key):
    keypad.keyPressed.emit(key)


def open_event(kind, finished=True):
    window.setProperty("overlay", "")
    window.setProperty("overlayStack", [])
    window.setProperty("familyId", kind)
    event = present(sources[kind], time.time())[
        "lastEvent" if finished else "nextEvent"
    ]
    window.setProperty("racingEventId", event["id"])
    window.setProperty("racingEventPage", 0)
    window.setProperty("racingIndex", 0)
    window.setProperty("overlay", "racingEvent")


def open_session(kind, session_kind):
    sessions = value("racingEvent")["sessions"]
    window.setProperty(
        "racingIndex",
        next(i for i, s in enumerate(sessions) if s["kind"] == session_kind),
    )
    press(5)


steps = [
    (lambda: open_event("f1"), "f1-weekend"),
    (lambda: press(6), "f1-circuit"),
    (lambda: press(6), "f1-summary"),
    (lambda: (press(6), open_session("f1", "RAC")), "f1-race"),
    (lambda: press(5), "f1-driver"),
    (lambda: press(6), "f1-pits"),
    (lambda: press(6), "f1-laps"),
    (lambda: press(6), "f1-stints"),
    (lambda: (press(7), press(7), open_session("f1", "FP1")), "f1-practice"),
    (lambda: press(5), "f1-practice-driver"),
    (lambda: press(6), "f1-practice-stints"),
    (lambda: open_event("motogp", False), "moto-weekend"),
    (lambda: press(6), "moto-circuit"),
    (lambda: (open_event("motogp"), press(6), press(6)), "moto-summary"),
    (lambda: (press(6), open_session("motogp", "RAC"), press(6)), "moto-conditions"),
    (lambda: (press(4), press(5)), "moto-driver"),
]
index = 0


def step():
    global index
    if index == len(steps):
        assert not errors, errors
        report = {
            "screens": index,
            "size": "960x640",
            "renderer": str(window.rendererInterface().graphicsApi()),
            "qml_errors": errors,
        }
        (root / "render.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))
        for s in services.values():
            s.close()
        sport._fantasy.clear()
        events.close()
        QThreadPool.globalInstance().waitForDone(3000)
        app.quit()
        return
    action, name = steps[index]
    index += 1
    action()

    def capture():
        if any(s._worker for s in services.values()):
            QTimer.singleShot(100, capture)
            return
        img = window.grabWindow()
        assert not img.isNull() and img.width() == 960 and img.height() == 640
        assert img.save(str(root / (name + ".png")))
        step()

    QTimer.singleShot(450, capture)


QTimer.singleShot(500, step)
QTimer.singleShot(30000, lambda: app.exit(2))
raise SystemExit(app.exec())
