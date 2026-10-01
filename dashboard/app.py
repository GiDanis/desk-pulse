"""Qt launcher and lightweight device state for the SmartPC dashboard."""

from __future__ import annotations

import signal
import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from account import AccountService
from events import EventService
from keypad import Keypad
from state import DashboardState
from sport import SportService
from motorsport import MotorsportService
from weather import WeatherService


def cpu_temperature() -> str:
    readings = []
    for zone in Path("/sys/class/thermal").glob("thermal_zone*"):
        try:
            kind = (zone / "type").read_text().strip().lower()
            if kind.startswith("cpu"):
                readings.append(int((zone / "temp").read_text()) / 1000)
        except (OSError, ValueError):
            continue
    return f"{max(readings):.0f} °C" if readings else "N/D"


def memory_usage() -> str:
    try:
        values = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            name, _, rest = line.partition(":")
            if name in ("MemTotal", "MemAvailable"):
                values[name] = int(rest.strip().split()[0])
        total = values["MemTotal"]
        available = values["MemAvailable"]
        return f"{(total - available) / total * 100:.0f}% usata"
    except (OSError, KeyError, ValueError, ZeroDivisionError):
        return "N/D"


def uptime() -> str:
    try:
        seconds = int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        return "N/D"
    days, remainder = divmod(seconds, 86400)
    hours, minutes = divmod(remainder, 3600)
    minutes //= 60
    return f"{days} g {hours} h" if days else f"{hours} h {minutes} min"


class SystemInfo(QObject):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._cpu_temperature = "N/D"
        self._memory_usage = "N/D"
        self._uptime = "N/D"
        self._last_refresh = 0.0
        self.refresh(force=True)

    def _check_refresh(self) -> None:
        if time.monotonic() - self._last_refresh > 5.0:
            self.refresh()

    @Property(str, notify=changed)
    def cpuTemperature(self) -> str:
        self._check_refresh()
        return self._cpu_temperature

    @Property(str, notify=changed)
    def memoryUsage(self) -> str:
        self._check_refresh()
        return self._memory_usage

    @Property(str, notify=changed)
    def uptimeText(self) -> str:
        self._check_refresh()
        return self._uptime

    def refresh(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last_refresh < 5.0:
            return
        self._last_refresh = now
        updated = (cpu_temperature(), memory_usage(), uptime())
        if updated != (self._cpu_temperature, self._memory_usage, self._uptime):
            self._cpu_temperature, self._memory_usage, self._uptime = updated
            self.changed.emit()


def main() -> int:
    application = QGuiApplication(sys.argv)
    application.setOrganizationName("SmartPC")
    application.setApplicationName("SmartPC")
    application.setOverrideCursor(Qt.CursorShape.BlankCursor)

    # Graceful shutdown handling for systemd and terminal signals
    signal.signal(signal.SIGTERM, lambda *_: application.quit())
    signal.signal(signal.SIGINT, lambda *_: application.quit())

    # Periodic timer to ensure the Python interpreter runs signal handlers while Qt event loop is active
    sig_timer = QTimer()
    sig_timer.setInterval(250)
    sig_timer.timeout.connect(lambda: None)
    sig_timer.start()

    engine = QQmlApplicationEngine()
    system_info = SystemInfo()
    keypad = Keypad()
    demo = "--demo" in sys.argv
    weather = WeatherService(auto_refresh=not demo)
    account = AccountService()
    events = EventService(path=":memory:" if demo else None, auto_refresh=not demo)
    sport = SportService(auto_refresh=not demo) if not demo else None
    racing = {kind: MotorsportService(kind) for kind in ('f1','motogp')} if not demo else {}
    state = DashboardState(weather, system_info, account, events, demo=demo, sport=sport, racing=racing)
    if sport: application.aboutToQuit.connect(sport.close)
    for service in racing.values(): application.aboutToQuit.connect(service.close)
    if not demo:
        def update_account_events() -> None:
            events.ingest_account(account.moduleState, state.accountWarningPercent,
                                  state.accountCriticalPercent)
        account.changed.connect(update_account_events)
        update_account_events()
    application.aboutToQuit.connect(events.close)
    engine.setInitialProperties({"keypad": keypad, "dashboardState": state})
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
    if not engine.rootObjects():
        return 1
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
