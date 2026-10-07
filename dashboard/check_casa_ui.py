"""Casa Qt worker, persistence, scheduler and real Main navigation; synthetic I/O."""

from copy import deepcopy
import argparse
import json
from pathlib import Path
import time
import threading
from unittest.mock import patch

from theme_fixture_support import isolate_process, LegacyHarness


def verify(profile, capture=None):
    private, base = isolate_process()
    harness = None
    services = []
    checks = []
    try:
        from PySide6.QtCore import qVersion
        from casa import CasaService
        from check_casa import FakeCloud, CONFIG
        from tuya_core import atomic_json, TuyaError

        harness = LegacyHarness(base, profile)
        config = base / "config/tuya-cloud.json"
        atomic_json(
            config,
            {
                key: getattr(CONFIG, key)
                for key in ("endpoint", "access_id", "access_secret", "uid")
            },
        )
        fake = FakeCloud()
        wall = [fake.now]
        mono = [1000.0]
        failure = [False]

        def transport(url, headers, timeout):
            assert timeout <= 4.5
            if failure[0]:
                raise TuyaError("offline", "Cloud di prova non raggiungibile.")
            return fake(url, headers, timeout)

        def make(directory):
            service = CasaService(
                auto_refresh=False,
                config_path=config,
                state_dir=directory,
                transport=transport,
                clock=lambda: wall[0],
                monotonic=lambda: mono[0],
            )
            services.append(service)
            return service

        service = make(base / "provider")

        def settle(value):
            deadline = time.monotonic() + 5
            while value._busy and time.monotonic() < deadline:
                harness.pump(5)
            assert not value._busy, "worker timeout"

        assert service.refresh() and not service.refresh()
        settle(service)
        assert (
            service.moduleState["status"] == "active"
            and service.budget.data["requests"] == 3
        )
        assert service.moduleState["data"]["favourites"][0]["primaryText"] == "Spento"
        checks.append("singleFlightAndPreSendAccounting")
        mono[0] += 60
        wall[0] += 60
        before = service.budget.data["requests"]
        assert service.refresh()
        assert service.moduleState["data"]["devices"][0]["previous"]
        settle(service)
        assert service.budget.data["requests"] == before + 1
        checks.append("BatchRefreshOneCallAndUpdatingPrevious")
        snapshot = deepcopy(service._snapshot)
        failure[0] = True
        mono[0] += 60
        wall[0] += 60
        assert service.refresh()
        settle(service)
        assert (
            service._snapshot == snapshot and service.moduleState["status"] == "offline"
        )
        restarted = make(base / "provider")
        assert (
            restarted.moduleState["status"] == "stale"
            and restarted.moduleState["data"]["devices"][0]["previous"]
        )
        assert restarted.budget.data["requests"] == service.budget.data["requests"]
        checks.append("OfflineCacheAndCounterSurviveNewProvider")
        failure[0] = False
        mono[0] += 60
        wall[0] += 60
        assert restarted.refresh()
        settle(restarted)
        assert restarted.moduleState["status"] == "active"
        before = deepcopy(restarted._snapshot)
        mono[0] += 60
        wall[0] += 60
        with patch("casa.atomic_json", side_effect=OSError("synthetic disk failure")):
            assert restarted.refresh()
            settle(restarted)
        assert (
            restarted._snapshot == before and restarted.moduleState["status"] == "error"
        )
        checks.append("UnwritableCacheNeverConfirmsAcquisition")
        # Slow durable writes must not block Qt or complete an action early.
        entered = threading.Event()
        release = threading.Event()
        writer_threads = []
        completions = []
        restarted.refreshFinished.connect(lambda ok, error: completions.append(ok))

        def slow_save(path, snapshot):
            writer_threads.append(threading.get_ident())
            entered.set()
            if not release.wait(5):
                raise OSError("test save timeout")
            atomic_json(path, snapshot)

        mono[0] += 60
        wall[0] += 60
        with patch("casa.atomic_json", side_effect=slow_save):
            try:
                assert restarted.refresh()
                deadline = time.monotonic() + 3
                while not entered.is_set() and time.monotonic() < deadline:
                    harness.pump(5)
                assert entered.is_set()
                assert (
                    len(writer_threads) == 1
                    and writer_threads[0] != threading.get_ident()
                )
                harness.pump(30)
                assert restarted._busy and not completions
                assert restarted._snapshot == before
            finally:
                release.set()
            settle(restarted)
        assert completions == [True]
        checks.append("DurableSaveOffGuiThreadAndCompletionAfterPersistence")
        # Allocated scheduler is deliberately synthetic; no Tuya quota is assumed.
        allocation = {
            "periodStart": wall[0] - 100,
            "periodEnd": wall[0] + 86400,
            "serviceExpiresAt": wall[0] + 86400,
            "apiAllowance": 26000,
            "consumedBeforeStart": 0,
        }
        atomic_json(config.with_name("tuya-policy.json"), allocation)
        scheduled = make(base / "scheduled")
        scheduled.setVisible(False)
        scheduled._tick()
        settle(scheduled)
        before = scheduled.budget.data["requests"]
        mono[0] += 299
        wall[0] += 299
        scheduled._tick()
        assert scheduled.budget.data["requests"] == before
        mono[0] += 1
        wall[0] += 1
        scheduled._tick()
        settle(scheduled)
        assert scheduled.budget.data["requests"] == before + 1
        scheduled.setVisible(True)
        mono[0] += 60
        wall[0] += 60
        before = scheduled.budget.data["requests"]
        scheduled._tick()
        settle(scheduled)
        assert (
            scheduled.budget.data["requests"] == before + 1
            and scheduled.budget.data["boostSeconds"] == 60
        )
        before = scheduled.budget.data["requests"]
        mono[0] += 60
        wall[0] += 60
        with patch.object(scheduled.budget, "boost", return_value=False):
            scheduled._tick()
        assert not scheduled._busy and scheduled.budget.data["requests"] == before
        checks.append("DeniedBoostNeverStartsFastAcquisition")
        scheduled.budget.data["boostSeconds"] = 7200
        before = scheduled.budget.data["requests"]
        mono[0] += 60
        wall[0] += 60
        scheduled._tick()
        assert scheduled.budget.data["requests"] == before
        checks.append("FiveMinuteBackgroundOneMinuteVisibleAndTwoHourCap")
        assert scheduled.togglePolling()
        restored = make(base / "scheduled")
        assert not restored.moduleState["data"]["polling"]
        assert restored.togglePolling()
        failure[0] = True
        mono[0] += 300
        wall[0] += 300
        restored._tick()
        settle(restored)
        assert restored.moduleState["status"] == "offline"
        due = restored._next
        mono[0] = due
        wall[0] += 301
        failure[0] = False
        restored._tick()
        settle(restored)
        assert restored.moduleState["status"] == "active"
        mono[0] += 60
        wall[0] += 60
        with patch.object(
            restored.client,
            "transport",
            side_effect=TuyaError("auth", "Synthetic auth failure"),
        ):
            assert restored.refresh()
            settle(restored)
        assert restored._halted and not restored.moduleState["data"]["polling"]
        mono[0] += 60
        wall[0] += 60
        assert restored.refresh()
        settle(restored)
        assert not restored._halted and restored.moduleState["data"]["polling"]
        checks.append("SuccessfulManualRecoveryRestoresConfiguredPolling")
        wall[0] = allocation["periodEnd"]
        before = restored.budget.data["requests"]
        mono[0] += 400
        restored._tick()
        assert restored.budget.data["requests"] == before
        changes = []
        restored.changed.connect(lambda: changes.append(True))
        for _ in range(3):
            mono[0] += 5
            restored._tick()
        assert changes == [], "unchanged expired policy repeatedly invalidated the UI"
        checks.append("PollingPreferenceReconnectAndExpiredServiceStop")
        restored.close()
        assert not restored.togglePolling()
        # Real demo UI: literal false and zero, dominant offline, identity selection.
        harness.root.setProperty("familyId", "casa")
        harness.root.setProperty("viewIndex", [0] * 7)
        harness.wait_ready()
        harness.pump(100)
        assert harness.expression(
            'activeContentId === "casa.overview" && casaRows.length === 4'
        )
        assert harness.value("casaRows")[0]["primaryText"] == "0 °C"
        assert harness.value("casaRows")[1]["availability"] == "Offline"
        if capture:
            capture.mkdir(parents=True, exist_ok=True)
            assert harness.window.grabWindow().save(str(capture / "casa-overview.png"))
        assert harness.expression("activateKey(2); casaTabsSelected")
        harness.expression("activateKey(6)")
        harness.wait_ready()
        assert harness.expression('activeContentId === "casa.devices"')
        harness.expression("activateKey(8); activateKey(5)")
        harness.wait_ready()
        assert harness.value("overlay") == "casaDetail"
        assert harness.value("casaSelectedId") == "demo-sensor"
        if capture:
            assert harness.window.grabWindow().save(str(capture / "casa-detail.png"))
        harness.expression("activateKey(7)")
        harness.root.setProperty("overlay", "casaSettings")
        harness.wait_ready()
        if capture:
            assert harness.window.grabWindow().save(str(capture / "casa-settings.png"))
        assert harness.expression(
            'casaSettingsAction("casa.favourite.move","demo-sensor",1)'
        )
        assert harness.casa._snapshot["favourites"][1] == "demo-sensor"
        assert harness.expression(
            'casaSettingsAction("casa.favourite.toggle","demo-light",1)'
        )
        assert "demo-light" not in harness.casa._snapshot["favourites"]
        harness.casa._snapshot["devices"][0]["name"] = "Nome modificato"
        harness.casa.changed.emit()
        harness.pump(40)
        assert harness.value("casaSelectedId") == "demo-sensor"
        checks.append("RealMainKeyNavigationDetailsFavouritesAndIdentityRetention")
        # Completion goes through the real public action broker, after the worker.
        harness.state._casa = restarted
        restarted.changed.connect(harness.state.casaChanged)
        restarted.changed.connect(harness.state.settingsChanged)
        restarted.refreshFinished.connect(harness.state.casaRefreshFinished)
        harness.state.casaChanged.emit()
        harness.state.settingsChanged.emit()
        harness.root.setProperty("overlay", "sources")
        harness.pump(40)
        context = harness.service.apiFactory.create("settings.sources")
        payload = harness.expression('publicSurfacePayload("settings.sources")')
        payload.update(
            active=True, interactive=True, viewportWidth=960, viewportHeight=640
        )
        assert harness.service.apiFactory.updateLegacy(context, payload)
        failure[0] = True
        mono[0] += 60
        wall[0] += 60
        result = context.requestAction("sources.refresh", "casa", {})
        assert result.status == "pending", result.status
        settle(restarted)
        harness.pump(30)
        assert (
            result.status == "failed" and restarted.moduleState["status"] == "offline"
        )
        harness.service.apiFactory.release(context)
        checks.append("PublicRefreshPendingThenFailedNoFalseConfirmation")
        assert not harness.messages, harness.messages
        assert not harness.transport, "unexpected external network"
        return {
            "status": "passed",
            "checks": checks,
            "count": len(checks),
            "qt": qVersion(),
            "profile": profile,
            "qmlWarnings": harness.messages,
            "scope": "Synthetic responses, real Qt worker and Main; no physical device or keypad changes.",
        }
    finally:
        for service in services:
            service.close()
        if harness:
            harness.close()
        private.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="base:day:off")
    parser.add_argument("--capture-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(
        dict(zip(("theme", "variant", "motion"), args.profile.split(":"))),
        args.capture_dir,
    )
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
