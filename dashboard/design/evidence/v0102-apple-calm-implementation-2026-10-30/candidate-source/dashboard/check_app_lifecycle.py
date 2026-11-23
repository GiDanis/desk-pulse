"""Real Qt launcher cleanup on normal exit and failed QML initialization."""

import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


def child(mode):
    from theme_fixture_support import isolate_process

    private, base = isolate_process()
    try:
        from PySide6.QtCore import QTimer, QUrl
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
        from app import main
        from network import NetworkService
        from casa import CasaService
        from events import EventService
        from theme_service import ThemeService
        from weather import WeatherService, normalize_response
        from account import AccountService

        load = QQmlApplicationEngine.load
        casa_close, events_close, cancel = (
            CasaService.close,
            EventService.close,
            ThemeService.cancel,
        )
        closed = []

        def load_window(engine, url):
            if mode == "qml-failure":
                url = QUrl.fromLocalFile(str(base / "missing.qml"))
            load(engine, url)
            if mode in ("normal", "automatic"):
                QTimer.singleShot(250, QGuiApplication.instance().quit)

        network_close = NetworkService.close
        def close_network(service):
            network_close(service)
            assert service._closed and service._stop.is_set() and not service._timer.isActive()
            closed.append("network")

        def close_casa(service):
            casa_close(service)
            assert (
                service._closed
                and service._stop.is_set()
                and not service._timer.isActive()
            )
            closed.append("casa")

        def close_events(service):
            events_close(service)
            closed.append("events")

        def close_theme(service):
            cancel(service)
            closed.append("theme")

        weather_close, account_close = WeatherService.close, AccountService.close

        def close_weather(service):
            if mode == "automatic":
                assert service._snapshot and service._cache_path.exists(), "Startup timer did not finish the controlled weather acquisition"
            weather_close(service)
            assert service._closed and not service._timer.isActive() and not service._age_timer.isActive()
            closed.append("weather")

        def close_account(service):
            account_close(service)
            assert service._closed and not service._timer.isActive()
            closed.append("account")

        sys.argv = ["app.py"] if mode == "automatic" else ["app.py", "--demo"]
        raw = json.loads((Path(__file__).parent / "fixtures/theme-runtime/domains/weather-zero.json").read_text())["raw"]
        with (
            patch.object(QQmlApplicationEngine, "load", load_window),
            patch.object(CasaService, "close", close_casa),
            patch.object(NetworkService, "close", close_network),
            patch.object(EventService, "close", close_events),
            patch.object(ThemeService, "cancel", close_theme),
            patch.object(WeatherService, "close", close_weather),
            patch.object(AccountService, "close", close_account),
            patch("weather.fetch_weather", return_value=normalize_response(raw)),
            patch("weather_alerts._read", side_effect=OSError("controlled offline")),
        ):
            result = main()
        assert result == (1 if mode == "qml-failure" else 0)
        assert sorted(closed) == ["account", "casa", "events", "network", "theme", "weather"], closed
        print(json.dumps({"mode": mode, "result": result, "closed": closed}))
    finally:
        private.cleanup()


class LauncherTests(unittest.TestCase):
    def check_exit(self, mode):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), mode],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"closed":', result.stdout)

    def test_normal_exit_closes_services(self):
        self.check_exit("normal")

    def test_failed_qml_load_closes_services(self):
        self.check_exit("qml-failure")

    def test_automatic_timers_and_provider_shutdown(self):
        self.check_exit("automatic")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] in ("normal", "qml-failure", "automatic"):
        child(sys.argv[1])
    else:
        unittest.main(verbosity=2)
