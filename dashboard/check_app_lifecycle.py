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
            if mode == "normal":
                QTimer.singleShot(100, QGuiApplication.instance().quit)

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

        sys.argv = ["app.py", "--demo"]
        with (
            patch.object(QQmlApplicationEngine, "load", load_window),
            patch.object(CasaService, "close", close_casa),
            patch.object(NetworkService, "close", close_network),
            patch.object(EventService, "close", close_events),
            patch.object(ThemeService, "cancel", close_theme),
        ):
            result = main()
        assert result == (1 if mode == "qml-failure" else 0)
        assert sorted(closed) == ["casa", "events", "network", "theme"], closed
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


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] in ("normal", "qml-failure"):
        child(sys.argv[1])
    else:
        unittest.main(verbosity=2)
