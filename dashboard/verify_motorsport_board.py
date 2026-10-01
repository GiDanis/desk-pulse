"""Bounded board evidence: real REST, Qt SignalR, cold offline cache and EGLFS.

Capture mode replays only responses downloaded by fetch mode, using isolated
preferences. Stop the kiosk before capturing with EGLFS.
"""

import argparse
import json
import os
from pathlib import Path
import statistics
import tempfile
import time

parser = argparse.ArgumentParser()
parser.add_argument(
    "--mode", choices=("fetch", "timing", "offline", "capture"), required=True
)
parser.add_argument("--directory", required=True)
parser.add_argument("--duration", type=int, default=12)
args = parser.parse_args()
root = Path(args.directory)
root.mkdir(parents=True, exist_ok=True)
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="smartpc-motor-verify-")
from motorsport_core import (
    MotorClient,
    refresh,
    load_event,
    save_cache,
    read_cache,
    present,
)
from sport_core import ROME
from datetime import datetime

if args.mode == "fetch":
    result = {}

    class RecordingClient(MotorClient):
        def __init__(self):
            super().__init__()
            self.responses = {}

        def get(self, url):
            raw, at = super().get(url)
            self.responses[url] = [raw, at]
            return raw, at

    client = RecordingClient()
    for kind in ("f1", "motogp"):
        result[kind] = {}
        for year in (datetime.now(ROME).year, datetime.now(ROME).year - 1):
            data = refresh(client, kind, year)
            assert not data.get("partialError"), data.get("partialError")
            assert not data.get("detailError"), data.get("detailError")
            # A distinct earlier GP proves lazy history retrieval.
            past = present(data, time.time())["past"]
            # Record exact current-GP routes as well as the /last/ endpoints.
            data = load_event(client, data, past[0]["id"])
            assert not data.get("detailError"), data.get("detailError")
            if kind == "motogp":
                fp = next((s for s in past[0]["sessions"] if s["kind"] == "FP1"), None)
                if fp:
                    data = load_event(client, data, past[0]["id"], fp["id"])
                assert not data.get("detailError"), data.get("detailError")
            selected = past[1] if len(past) > 1 else past[0]
            data = load_event(client, data, selected["id"])
            assert not data.get("detailError"), data.get("detailError")
            detail = next(e for e in data["events"] if e["id"] == selected["id"])
            counts = {s["kind"]: len(s["results"]) for s in detail["sessions"]}
            assert counts.get("RAC", 0) > 15 and any(
                counts.get(k, 0) >= 10 for k in ("Q", "Q2")
            )
            save_cache(root / (kind + "-" + str(year) + ".json"), data)
            result[kind][str(year)] = {
                "events": len(data["events"]),
                "pilots": len(data["standings"]),
                "constructors": len(data["constructors"]),
                "next_gp": present(data, time.time())["nextEvent"].get("name"),
                "historical_gp": detail["name"],
                "session_rows": counts,
                "fetchedAt": data["fetchedAt"],
            }
    (root / "responses.json").write_text(
        json.dumps(client.responses, separators=(",", ":"))
    )
    result["requests"] = client.request_count
    (root / "online.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0)

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6
from motorsport import MotorsportService
from racing_timing import F1Timing

app = QGuiApplication([])
app.setOrganizationName("SmartPC")
app.setApplicationName("Motorsport board verification")
year = datetime.now(ROME).year

if args.mode == "timing":
    timing = F1Timing()
    timing.ensure(True)

    def finish():
        info = timing.state.present(time.time(), year)
        result = {
            "connected": timing.state.connected,
            "topics": list(timing.state.topics),
            "session": info["name"],
            "meeting": info["meeting"],
            "status": info["status"],
            "active": info["active"],
            "isLive": info["isLive"],
            "rows": len(info["rows"]),
            "scope": "real unauthenticated Qt SignalR Core subscription; no active-session latency proof",
        }
        (root / "signalr.json").write_text(json.dumps(result, indent=2) + "\n")
        (root / "signalr-topics.json").write_text(
            json.dumps(timing.state.topics, separators=(",", ":"))
        )
        print(json.dumps(result))
        timing.close()
        app.exit(0 if result["connected"] and result["topics"] else 2)

    QTimer.singleShot(14000, finish)
    raise SystemExit(app.exec())

services = {
    kind: MotorsportService(kind, auto_refresh=False, cache_directory=root)
    for kind in ("f1", "motogp")
}
if args.mode == "offline":
    result = {}
    for kind, service in services.items():
        assert service.moduleState["data"]["fromCache"]
        service._offline = True
        service.refresh()

    def finish():
        if any(s._worker for s in services.values()):
            return
        for kind, service in services.items():
            state = service.moduleState
            assert state["status"] == "offline" and not state["data"]["live"].get(
                "isLive"
            )
            result[kind] = {
                "status": state["status"],
                "fromCache": state["data"]["fromCache"],
                "events": len(state["data"]["events"]),
                "pilots": len(state["data"]["standings"]),
                "result_rows": sum(
                    len(s["results"])
                    for e in state["data"]["events"]
                    for s in e["sessions"]
                ),
            }
            service.close()
        (root / "offline.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        app.quit()

    for service in services.values():
        service.changed.connect(finish)
    QTimer.singleShot(5000, lambda: app.exit(2))
    raise SystemExit(app.exec())

from account import AccountService
from app import SystemInfo
from events import EventService
from sport import SportService
from state import DashboardState
from weather import WeatherService

responses = json.loads((root / "responses.json").read_text())


class ReplayClient:
    def get(self, url):
        from sport_core import ProviderError

        if url not in responses:
            raise ProviderError("Risposta non raccolta nella prova REST")
        return responses[url]


for kind, service in services.items():
    # All captured dates and scores came from fetch mode; suppress further HTTP.
    service._client = ReplayClient()
    service._from_cache = False


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
engine.warnings.connect(lambda rows: errors.extend(str(row) for row in rows))
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
    item = window.property(key)
    return item.toVariant() if hasattr(item, "toVariant") else item


def press(key):
    keypad.keyPressed.emit(key)


def capture(name):
    image = window.grabWindow()
    assert not image.isNull() and image.width() == 960 and image.height() == 640
    assert image.save(str(root / (name + ".png")))


# Declarative path: physical captures after each actual navigation action.
steps = []
for kind in ("f1", "motogp"):
    steps.extend(
        [
            (lambda k=kind: window.setProperty("familyId", k), kind + "-programme"),
            (lambda: press(5), kind + "-calendar"),
            (lambda: press(5), kind + "-weekend"),
            (lambda: press(5), kind + "-future-session"),
            (lambda: press(6), kind + "-session-info"),
            (lambda: (press(7), press(7), press(7), press(8)), kind + "-results"),
            (lambda: (press(5), press(5)), kind + "-result-weekend"),
            (
                lambda: (
                    window.setProperty(
                        "racingIndex",
                        next(
                            i
                            for i, s in enumerate(value("racingRows"))
                            if s["kind"] == "RAC"
                        ),
                    ),
                    press(5),
                ),
                kind + "-race-result",
            ),
            (lambda: (press(7), press(7), press(7), press(8)), kind + "-standings"),
            (lambda: press(5), kind + "-full-standings"),
        ]
    )
    if kind == "f1":
        steps.append((lambda: press(6), "f1-constructors"))
    steps.append((lambda: press(7), None))
steps.extend(
    [
        (
            lambda: (
                press(9),
                press(8),
                press(5),
                window.setProperty("settingsIndex", 5),
                press(5),
            ),
            "motogp-settings",
        ),
        (lambda: press(1), None),
    ]
)
step_index = 0
last_frame = 0
last_action = 0
intervals = []
first_frames = []
action_count = 0


def frame():
    global last_frame
    now = time.perf_counter()
    if last_action and last_frame < last_action <= now:
        first_frames.append((now - last_action) * 1000)
    if (
        now - last_action < 0.25
        and last_frame >= last_action
        and 0 < now - last_frame < 0.1
    ):
        intervals.append((now - last_frame) * 1000)
    last_frame = now


window.frameSwapped.connect(frame)


def step():
    global step_index
    if step_index >= len(steps):
        nav.start()
        QTimer.singleShot(args.duration * 1000, finish)
        return
    action, name = steps[step_index]
    step_index += 1
    action()
    QTimer.singleShot(450, lambda: (capture(name) if name else None, step()))


nav = QTimer()
nav.setInterval(450)
actions = (6, 8, 5, 8, 7, 2, 6, 8, 5, 8, 7, 1, 4)


def action():
    global action_count, last_action
    last_action = time.perf_counter()
    press(actions[action_count % len(actions)])
    action_count += 1


nav.timeout.connect(action)


def finish():
    nav.stop()
    ordered = sorted(intervals)
    result = {
        "renderer": str(window.rendererInterface().graphicsApi()),
        "actions": action_count,
        "frames": len(intervals),
        "duration_s": args.duration,
        "median_ms": round(statistics.median(intervals), 2) if intervals else None,
        "p95_ms": (
            round(ordered[int((len(ordered) - 1) * 0.95)], 2) if ordered else None
        ),
        "max_ms": round(max(intervals), 2) if intervals else None,
        "first_frame_max_ms": round(max(first_frames), 2) if first_frames else None,
        "qml_errors": errors,
        "scope": "bounded real REST data EGLFS navigation; not endurance, active-session latency or fixed-60fps guarantee",
    }
    (root / "render.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    for service in services.values():
        service.close()
    events.close()
    app.exit(2 if errors else 0)


QTimer.singleShot(500, step)
QTimer.singleShot((args.duration + 35) * 1000, lambda: app.exit(2))
raise SystemExit(app.exec())
