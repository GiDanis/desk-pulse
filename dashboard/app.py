"""Qt launcher and lightweight device state for the SmartPC dashboard."""

from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from account import AccountService
from events import EventService
from keypad import Keypad
from state import DashboardState
from sport import SportService
from motorsport import MotorsportService
from system_info import SystemInfo
from weather import WeatherService
from casa import CasaService


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--theme-trace-output", type=Path)
    options, _ = parser.parse_known_args()
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
    from theme_api import bootstrap_theme_api
    bootstrap_theme_api(engine)
    system_info = SystemInfo()
    keypad = Keypad()
    demo = "--demo" in sys.argv
    weather = WeatherService(auto_refresh=not demo)
    account = AccountService()
    casa = CasaService(auto_refresh=not demo, demo=demo)
    events = EventService(path=":memory:" if demo else None, auto_refresh=not demo)
    sport = SportService(auto_refresh=not demo) if not demo else None
    racing = {kind: MotorsportService(kind) for kind in ('f1','motogp')} if not demo else {}
    trace = None
    if options.theme_trace_output:
        from theme_trace_bridge import ThemeTraceBridge
        trace = ThemeTraceBridge()
    state = DashboardState(weather, system_info, account, events, demo=demo, sport=sport, racing=racing, trace=trace, casa=casa)
    if not demo:
        def update_account_events() -> None:
            events.ingest_account(account.moduleState, state.accountWarningPercent,
                                  state.accountCriticalPercent)
        account.changed.connect(update_account_events)
        state.accountThresholdsChanged.connect(update_account_events)
        update_account_events()
    engine.setInitialProperties({"keypad": keypad, "dashboardState": state, "traceRecorder": trace})
    # Close Python services after the event loop returns. On Qt 6.8, invoking
    # these callbacks from aboutToQuit can re-enter QML during Qt teardown.
    try:
        engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
        if not engine.rootObjects():
            return 1
        if trace:
            trace.attach(engine.rootObjects()[0])
        result = application.exec()
    finally:
        casa.close()
        if state.appearance:
            state.appearance.cancel()
        if sport:
            sport.close()
        for service in racing.values():
            service.close()
        events.close()
    if trace:
        trace.write_report(options.theme_trace_output)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
