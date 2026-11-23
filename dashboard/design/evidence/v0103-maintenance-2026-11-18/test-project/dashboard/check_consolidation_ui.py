"""0.8.2 persistence/lifecycle/manual refresh/input regressions; no network."""
from copy import deepcopy
import argparse
import json
import threading
import time
from unittest.mock import patch

from theme_fixture_support import CORPUS, LegacyHarness, isolate_process


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="base:day:off")
    args = parser.parse_args()
    theme, variant, motion = args.profile.split(":")
    private, base = isolate_process()
    harness = None
    services, gates, results = [], [], []
    try:
        from PySide6.QtCore import QObject, QThreadPool
        from account import AccountService, MAX_AGE_SECONDS as ACCOUNT_AGE
        from state import DashboardState
        from weather import WeatherService, normalize_response, save_weather_cache
        harness = LegacyHarness(base, {"theme": theme, "variant": variant, "motion": motion})
        raw = json.loads((CORPUS / "domains/weather-zero.json").read_text())["raw"]
        complete = normalize_response(raw)

        def wait_for(condition):
            deadline = time.monotonic() + 5
            while not condition() and time.monotonic() < deadline:
                harness.pump(5)
            assert condition(), "Controlled worker timeout"

        weather = WeatherService(auto_refresh=False)
        services.append(weather)
        weather._cache_path = base / "cache" / "maintenance-weather.json"
        completions, writer_threads = [], []
        weather.refreshFinished.connect(lambda ok, message: completions.append((ok, message)))
        entered, release = threading.Event(), threading.Event()
        gates.append(release)

        def delayed_write(path, snapshot, stamp):
            writer_threads.append(threading.get_ident())
            entered.set()
            assert release.wait(4)
            save_weather_cache(path, snapshot, stamp)

        with patch("weather.fetch_weather", return_value=complete), patch("weather.save_weather_cache", side_effect=delayed_write):
            assert weather.refresh()
            wait_for(entered.is_set)
            assert weather._in_flight and not completions and not weather._snapshot
            assert not weather.refresh()
            harness.expression('activateKey(9)')
            harness.pump(30)
            assert harness.value("overlay") == "menu"
            assert len(writer_threads) == 1 and writer_threads[0] != threading.get_ident()
            release.set()
            wait_for(lambda: not weather._in_flight)
        assert completions == [(True, "")]
        persisted, stamp = weather._cache_path.read_bytes(), weather._fetched_at
        assert json.loads(persisted)["snapshot"] == complete
        results.append("worker-persistence-before-completion-and-responsive-ui")
        with patch("weather.fetch_weather", side_effect=RuntimeError("offline")):
            assert weather.refresh()
            wait_for(lambda: not weather._in_flight)
        assert weather._snapshot == complete and weather._fetched_at == stamp
        assert weather._cache_path.read_bytes() == persisted
        assert weather.moduleState["status"] == "offline" and not completions[-1][0]
        results.append("offline-retains-complete-snapshot-and-original-time")
        newer = deepcopy(complete)
        newer["temperature"] = "12°"
        with patch("weather.fetch_weather", return_value=newer), patch("weather.os.replace", side_effect=OSError("disk full")):
            assert weather.refresh()
            wait_for(lambda: not weather._in_flight)
        assert weather._snapshot == newer and weather.moduleState["status"] == "active"
        assert weather.moduleState["data"]["cacheError"] and not completions[-1][0]
        assert weather._cache_path.read_bytes() == persisted
        assert not list(weather._cache_path.parent.glob("weather-*.json"))
        results.append("write-failure-visible-live-data-usable-old-cache-atomic")
        with patch("weather.WeatherService._get_cache_path", return_value=weather._cache_path):
            rebooted = WeatherService(auto_refresh=False)
        services.append(rebooted)
        assert rebooted._snapshot == complete and rebooted.moduleState["status"] == "stale"
        corrupt = json.loads(persisted)
        corrupt["snapshot"]["forecast"][0] = {"code": 0}
        weather._cache_path.write_text(json.dumps(corrupt))
        with patch("weather.WeatherService._get_cache_path", return_value=weather._cache_path):
            invalid = WeatherService(auto_refresh=False)
        services.append(invalid)
        assert not invalid._snapshot and invalid.moduleState["status"] == "unavailable"
        results.append("restart-previous-cache-and-nested-corruption")
        for change in (lambda value: value["current"].update(temperature_2m=float("nan")),
                       lambda value: value["daily"]["temperature_2m_max"].__setitem__(0, None)):
            value = deepcopy(raw)
            change(value)
            try:
                normalize_response(value)
            except ValueError:
                pass
            else:
                raise AssertionError("Incomplete/non-finite weather accepted")
        results.append("nonfinite-and-incomplete-response-rejected")
        closing = WeatherService(auto_refresh=False)
        services.append(closing)
        closing._cache_path = base / "cache" / "closed-weather.json"
        gate, returned = threading.Event(), threading.Event()
        gates.append(returned)

        def late_fetch():
            gate.set()
            assert returned.wait(4)
            return complete

        with patch("weather.fetch_weather", side_effect=late_fetch):
            assert closing.refresh()
            wait_for(gate.is_set)
            closing.close()
            assert not closing.refresh()
            returned.set()
            assert QThreadPool.globalInstance().waitForDone(4000)
            harness.pump(20)
        assert not closing._snapshot and not closing._cache_path.exists()
        results.append("close-cancels-late-publication-and-persistence")
        account_path = base / "cache" / "maintenance-account.json"
        now = time.time()
        account_payload = {"version": 1, "status": "active", "updatedAt": now,
                           "data": {"plan": "Fixture", "windows": [{"label": "Codex", "usedPercent": 0}]}}
        account_path.write_text(json.dumps(account_payload))
        account = AccountService(account_path)
        services.append(account)
        with patch("account.read_account_state", wraps=__import__("account").read_account_state) as read:
            for _ in range(100):
                account.refresh(force=False)
            assert read.call_count == 0
            with patch("account.time.time", return_value=now + ACCOUNT_AGE + 1):
                account.refresh(force=False)
            assert account.moduleState["status"] == "stale" and read.call_count == 0
            account.refresh()
            assert read.call_count == 1
        results.append("unchanged-account-zero-rereads-age-still-transitions")
        with patch("account.time.time", return_value=now - 301):
            account.refresh(force=False)
        assert account.moduleState["status"] == "error" and account.moduleState["data"]
        account.refresh(force=False)
        assert account.moduleState["status"] == "active"
        results.append("clock-backward-future-account-not-current")
        replacement = account_path.with_suffix(".new")
        account_payload["data"]["windows"][0]["usedPercent"] = 25
        replacement.write_text(json.dumps(account_payload))
        replacement.replace(account_path)
        account.refresh(force=False)
        assert account.moduleState["data"]["windows"][0]["usedPercent"] == 25
        account_path.write_text('{"version":1,"status":"active","updatedAt":NaN,"data":{"windows":[]}}')
        account.refresh()
        assert account.moduleState["status"] == "error" and account.moduleState["updatedAt"] == now
        assert account.moduleState["data"]["windows"][0]["usedPercent"] == 25
        account_path.unlink()
        account.refresh()
        assert account.moduleState["status"] == "unavailable" and account.moduleState["data"]
        results.append("account-atomic-replace-invalid-missing-retain-last-complete")
        state = DashboardState(weather, harness.system, account, harness.events,
                               sport=harness.sport, racing=harness.racing, casa=harness.casa, network=harness.network)
        with patch("weather.fetch_weather", return_value=complete):
            assert state.refreshSource("meteo")
            assert state.sourceRefreshStates["meteo"]["status"] == "running"
            assert not state.refreshSource("meteo")
            wait_for(lambda: not weather._in_flight)
        assert state.sourceRefreshStates["meteo"]["status"] == "succeeded"
        assert not state.refreshSource("meteo")
        assert state.sourceRefreshStates["meteo"]["status"] == "cooldown"
        assert state.refreshSource("account")
        assert state.sourceRefreshStates["account"]["status"] == "failed"
        assert "PC" in state.sourceRefreshStates["account"]["message"]
        assert not state.refreshSource("unknown")
        results.append("manual-running-completion-cooldown-local-account-failure")
        factory = harness.service.apiFactory
        harness.root.setProperty("overlay", "sources")
        harness.pump(30)
        context = factory.create("settings.sources")
        payload = harness.expression('publicSurfacePayload("settings.sources")')
        payload.update(active=True, interactive=True, viewportWidth=960, viewportHeight=640)
        assert factory.updateLegacy(context, payload)
        with patch.object(harness.state, "refreshSource", return_value=True):
            result = context.requestAction("sources.refresh", "weather", {})
            assert result.status == "pending"
            harness.state.sourceRefreshFinished.emit("meteo", False, "Cache non salvata")
            assert result.status == "failed"

        def synchronous(source):
            harness.state.sourceRefreshFinished.emit(source, True, "Cache riletta dal PC")
            return True

        with patch.object(harness.state, "refreshSource", side_effect=synchronous):
            result = context.requestAction("sources.refresh", "account", {})
            assert result.status == "completed"
        assert not harness.value("pendingPublicActions")
        results.append("public-pending-failure-and-synchronous-completion-not-lost")
        harness.root.setProperty("overlay", "")
        harness.root.setProperty("familyId", "sport")
        harness.root.setProperty("sportView", "PROSSIME")
        harness.root.setProperty("sportOverviewPage", 0)
        harness.pump(30)
        assert harness.value("sportOverviewPages") > 1
        timer = harness.root.findChild(QObject, "sportOverviewTimer")
        timer.setProperty("interval", 40)
        wait_for(lambda: harness.value("sportOverviewPage") != 0)
        harness.expression('activateKey(9)')
        harness.expression('activateKey(7)')
        page = harness.value("sportOverviewPage")
        harness.pump(170)
        assert harness.value("sportOverviewPage") == page and not timer.property("running")
        harness.expression('activateKey(1)')
        harness.root.setProperty("familyId", "sport")
        harness.pump(20)
        assert timer.property("running")
        results.append("sport-pauses-on-input-keeps-page-resumes-on-reentry")
        assert not harness.transport and not harness.messages, (harness.transport, harness.messages)
        print(json.dumps({"status": "passed", "profile": args.profile, "checks": results, "count": len(results),
                          "scope": "Qt/Main, isolated files, controlled workers, denied external network"}))
    finally:
        for gate in gates:
            gate.set()
        for service in services:
            service.close()
        if harness:
            harness.close()
        private.cleanup()


if __name__ == "__main__":
    main()
