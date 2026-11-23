"""Measure frame intervals while navigating real QML views on the board.

Run only after stopping the kiosk service; EGLFS owns the display exclusively.
The script does not use the network or alter the USB keypad configuration.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from account import AccountService
from app import SystemInfo
from state import DashboardState
from weather import WeatherService


class SimulatedKeypad(QObject):
    keyPressed = Signal(int)
    connected = False


def percentile(values: list[float], proportion: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * proportion))]


def main() -> int:
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    application = QGuiApplication(sys.argv[:1])
    application.setOrganizationName("SmartPC")
    application.setApplicationName("SmartPC benchmark")
    engine = QQmlApplicationEngine()
    system = SystemInfo()
    weather = WeatherService(auto_refresh=False)
    account = AccountService(path=Path(__file__).parent / "missing-account.json")
    keypad = SimulatedKeypad()
    state = DashboardState(weather, system, account, demo=True)
    state.markCommandsSeen()
    engine.setInitialProperties({"keypad": keypad, "dashboardState": state})
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]
    intervals: list[float] = []
    last_frame = 0.0
    last_action = 0.0
    actions = (6, 8, 4, 2)
    action_index = 0

    def frame() -> None:
        nonlocal last_frame
        stamp = time.perf_counter()
        if stamp - last_action < 0.25 and last_frame:
            interval = (stamp - last_frame) * 1000
            if interval < 100:  # Exclude the idle gap before each transition.
                intervals.append(interval)
        last_frame = stamp

    def navigate() -> None:
        nonlocal action_index, last_action
        last_action = time.perf_counter()
        keypad.keyPressed.emit(actions[action_index % len(actions)])
        action_index += 1

    window.frameSwapped.connect(frame)
    timer = QTimer()
    timer.setInterval(450)
    timer.timeout.connect(navigate)
    timer.start()
    QTimer.singleShot(duration * 1000, application.quit)
    application.exec()
    if not intervals:
        print(json.dumps({"error": "No transition frames captured"}))
        return 1
    print(json.dumps({
        "duration_s": duration, "transitions": action_index, "frames": len(intervals),
        "median_ms": round(statistics.median(intervals), 2),
        "p95_ms": round(percentile(intervals, 0.95), 2),
        "over_16_67_percent": round(sum(i > 16.67 for i in intervals) / len(intervals) * 100, 1),
        "max_ms": round(max(intervals), 2),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
