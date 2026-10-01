"""Targeted cache, worker and timing regressions; no external network."""

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="sport-optimization-")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QGuiApplication
from motorsport import MotorsportService
from motorsport_core import load_event, refresh, MotorClient, JOLPICA
from racing_details import open_results, results_fresh
from racing_timing import TimingState, deep_merge
from sport import SportService, _Worker
from sport_core import ProviderError

ROOT = Path(__file__).parent
app = QGuiApplication.instance() or QGuiApplication([])


def sample(kind):
    return json.loads(
        (ROOT / "fixtures" / ("racing-" + kind + "-normalized.json")).read_text()
    )["snapshot"]


class Checks(unittest.TestCase):
    def test_presentation_reuse_and_clock_boundaries(self):
        service = MotorsportService("f1", auto_refresh=False, initial=sample("f1"))
        now = time.time()
        with patch(
            "motorsport.present", wraps=__import__("motorsport_core").present
        ) as render:
            first = service._data_view(now)
            self.assertIs(first, service._data_view(now + 1))
            self.assertEqual(render.call_count, 1)
            service._from_cache = True
            self.assertIsNot(first, service._data_view(now + 2))
            service._snapshot = deepcopy(service._snapshot)
            service._data_view(now + 3)
            self.assertEqual(render.call_count, 3)
            service._data_view(now - 1)  # A backward clock adjustment.
            self.assertEqual(render.call_count, 4)
        # Cross a scheduled session start and the 30-minute next-session cutoff.
        session = service._snapshot["events"][0]["sessions"][0]
        start = session["start"]
        session["state"] = "scheduled"
        service._snapshot = deepcopy(service._snapshot)
        before = service._data_view(start - 0.5)
        after = service._data_view(start + 0.5)
        self.assertIsNot(before, after)
        self.assertEqual(
            after["events"][0]["sessions"][0]["statusText"], "Orario trascorso"
        )
        before = service._data_view(start + 1799.5)
        self.assertIsNot(before, service._data_view(start + 1800.5))
        # Transient envelope flags must not modify the cached presentation.
        service.moduleState
        self.assertNotIn("detailLoading", service._view)
        service.close()

    def test_timing_reuse_delta_ownership_and_freshness(self):
        original = {"a": {"b": [1, 2]}}
        update = {"a": {"b": {"1": 3}}}
        merged = deep_merge(original, update)
        self.assertEqual(original["a"]["b"], [1, 2])
        self.assertEqual(merged["a"]["b"], {"0": 1, "1": 3})
        now = time.time()
        state = TimingState()
        state.apply(
            "SessionInfo",
            {
                "Key": 1,
                "StartDate": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 600)
                ),
            },
            now,
        )
        state.apply("SessionStatus", {"Status": "Started"}, now)
        payload = {"1": {"FullName": "Driver"}}
        state.apply("DriverList", payload, now)
        payload["1"]["FullName"] = "Changed outside"
        state.apply("TimingData", {"Lines": {"1": {"Position": "1"}}}, now)
        state.connected = True
        year = time.gmtime(now).tm_year
        first = state.present(now, year, True)
        state.apply("Heartbeat", {}, now + 1)
        second = state.present(now + 1, year, True)
        self.assertIs(first["rows"], second["rows"])
        self.assertEqual(first["rows"][0]["name"], "Driver")
        self.assertFalse(state.present(now + 100, year, True)["active"])
        state.apply("WeatherData", {"AirTemp": "25"}, now + 2)
        self.assertIsNot(first["rows"], state.present(now + 2, year)["rows"])
        previous_revision = state.revision
        state.apply("SessionInfo", {"Key": 2}, now + 3)
        self.assertTrue(state.connected)
        self.assertGreater(state.revision, previous_revision)
        self.assertFalse(state.present(now + 3, year)["rows"])

    def test_result_reopen_skips_network_but_force_refreshes(self):
        data = sample("f1")
        event = next(
            e for e in data["events"] if any(s["results"] for s in e["sessions"])
        )
        target = next(s for s in event["sessions"] if s["results"])
        target["resultsAt"] = time.time()

        class Recording:
            calls = []

            def get(self, url):
                self.calls.append(url)
                raise ProviderError("offline")

        client = Recording()
        result = load_event(client, data, event["id"], target["id"])
        self.assertFalse(client.calls)
        self.assertFalse(result["detailError"])
        load_event(client, data, event["id"], target["id"], force=True)
        self.assertEqual(len(client.calls), 1)
        self.assertIn(
            {"RAC": "results", "Q": "qualifying", "SPR": "sprint"}[target["kind"]],
            client.calls[0],
        )
        now = time.time()
        self.assertFalse(results_fresh(dict(target, resultsAt=now + 1), now))
        self.assertFalse(
            results_fresh(dict(target, start=now - 3600, resultsAt=now - 601), now)
        )
        self.assertTrue(
            results_fresh(dict(target, start=now - 172800, resultsAt=now - 601), now)
        )
        moto = sample("motogp")
        event = next(
            e for e in moto["events"] if any(s["results"] for s in e["sessions"])
        )
        target = next(s for s in event["sessions"] if s["results"])
        event["programmeAt"] = event["sessionsAt"] = target["resultsAt"] = time.time()
        client.calls = []
        load_event(client, moto, event["id"], target["id"])
        self.assertFalse(client.calls)

    def test_open_results_keep_driver_extras_after_refresh(self):
        responses = json.loads(
            (ROOT / "fixtures/racing-openf1-details.json").read_text()
        )
        from motorsport_core import f1_calendar

        event = f1_calendar(
            json.loads(
                (ROOT / "fixtures/racing-f1-2025-last-calendar.json").read_text()
            ),
            2025,
        )[0]
        session = next(s for s in event["sessions"] if s["kind"] == "FP1")

        class Replay:
            def get(self, url):
                return deepcopy(responses[url])

        data = {"year": 2025, "kind": "f1"}
        open_results(Replay(), data, event, session)
        session["results"][0]["stints"] = [{"label": "Gomma", "value": "SOFT"}]
        session["results"][0]["stintsAt"] = 123
        open_results(Replay(), data, event, session, force=True)
        self.assertEqual(session["results"][0]["stints"][0]["value"], "SOFT")
        self.assertEqual(session["results"][0]["stintsAt"], 123)

    def test_full_calendar_refresh_keeps_existing_driver_details(self):
        old = sample("f1")
        event = next(e for e in old["events"] if e["round"] == "15")
        target = next(s for s in event["sessions"] if s["kind"] == "RAC")
        winner_id = target["results"][0]["id"]
        target["results"][0]["stints"] = [{"label": "Gomma", "value": "SOFT"}]
        fresh_events = deepcopy(old["events"])
        for gp in fresh_events:
            for session in gp["sessions"]:
                session["results"] = []
                session["resultsAt"] = 0
        raw_results = json.loads((ROOT / "fixtures/racing-f1-results.json").read_text())

        class Replay:
            def get(self, url):
                if "/last/results.json" in url:
                    return deepcopy(raw_results), time.time()
                if "/qualifying.json" in url or "/sprint.json" in url:
                    raise ProviderError("optional unavailable")
                return {}, time.time()

        with patch("motorsport_core.f1_calendar", return_value=fresh_events), patch(
            "motorsport_core.f1_standings",
            return_value=(deepcopy(old["standings"]), "15"),
        ):
            updated = refresh(Replay(), "f1", old["year"], old)
        event = next(e for e in updated["events"] if e["round"] == "15")
        target = next(s for s in event["sessions"] if s["kind"] == "RAC")
        winner = next(r for r in target["results"] if r["id"] == winner_id)
        self.assertEqual(winner["stints"][0]["value"], "SOFT")

    def test_manual_refresh_forces_detail_worker_with_throttle(self):
        service = MotorsportService("f1", auto_refresh=False, initial=sample("f1"))
        service._selection = (service._snapshot["events"][0]["id"], "")
        with patch.object(QThreadPool.globalInstance(), "start") as start:
            service.refreshDetails()
            self.assertTrue(service._worker.force)
            self.assertFalse(service._worker.full)
            service._worker = None
            service.refreshDetails()
            self.assertEqual(start.call_count, 1)
        service.close()

    def test_cache_io_runs_in_worker_and_disk_failure_keeps_data(self):
        data = json.loads((ROOT / "fixtures/sport-normalized-sample.json").read_text())
        main_thread = threading.get_ident()
        with tempfile.TemporaryDirectory() as directory:
            paths = (
                Path(directory) / "sport.json",
                Path(directory) / "sport-season.json",
            )
            worker = _Worker(
                None,
                None,
                "",
                True,
                False,
                data["season"],
                cache_paths=paths,
                retained_seasons=(data["season"],),
            )
            writes = []
            done = []
            worker.signals.finished.connect(
                lambda value, error: done.append((value, error))
            )

            def save(path, value):
                writes.append(threading.get_ident())

            with patch("sport.refresh_snapshot", return_value=data), patch(
                "sport.save_cache", side_effect=save
            ):
                QThreadPool.globalInstance().start(worker)
                deadline = time.monotonic() + 3
                while not done and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(0.005)
                QThreadPool.globalInstance().waitForDone(1000)
                app.processEvents()
            self.assertEqual(len(writes), 2)
            self.assertTrue(all(t != main_thread for t in writes))
            self.assertEqual(done[0], (data, None))
            worker = _Worker(
                None, None, "", True, False, data["season"], cache_paths=paths
            )
            done = []
            worker.signals.finished.connect(
                lambda value, error: done.append((value, error))
            )
            with patch("sport.refresh_snapshot", return_value=data), patch(
                "sport.save_cache", side_effect=OSError("disk full")
            ):
                worker.run()
            self.assertEqual(done[0], (data, None))
            self.assertEqual(worker.cache_error, "Cache non salvata")

    def test_closed_services_ignore_late_completion_and_manual_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            sport = SportService(
                auto_refresh=False,
                cache_path=Path(directory) / "sport.json",
                state_path=Path(directory) / "goals.json",
            )
            racing = MotorsportService(
                "f1", auto_refresh=False, cache_directory=directory
            )
            team, fantasy = sport._team, sport._fantasy
            team.provider_id = "new-team"
            team.worker = SimpleNamespace(provider_id="old-team", team_id="old")
            racing._worker = SimpleNamespace()
            fantasy.worker = SimpleNamespace()
            sport.close()
            racing.close()
            with patch.object(QThreadPool.globalInstance(), "start") as start:
                team._finished(None, ProviderError("late"))
                fantasy._finished(None, ProviderError("late"))
                racing._finished(None, ProviderError("late"))
                sport._finished(None, ProviderError("late"))
                for service in (sport, racing, team, fantasy):
                    service.refresh()
                start.assert_not_called()
            self.assertFalse(sport._timer.isActive())
            self.assertFalse(team.timer.isActive())

    def test_cooldown_does_not_consume_provider_budget(self):
        client = MotorClient()
        url = JOLPICA + "2026.json"
        client.cooldowns[url] = (time.time() + 60, 429, "blocked")
        with self.assertRaises(ProviderError):
            client.get(url)
        self.assertEqual(client._jolpica_times, [])
        self.assertEqual(client.request_count, {})


if __name__ == "__main__":
    unittest.main()
