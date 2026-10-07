"""Qt Casa provider. One shared client/worker, read-only Tuya Cloud acquisition."""

from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import random
import threading
import time

from PySide6.QtCore import (
    QObject,
    Property,
    QRunnable,
    QThreadPool,
    QTimer,
    Signal,
    Slot,
)

from module_state import module_state
from tuya_core import CloudClient, TuyaError, load_config, http_get, atomic_json
from casa_core import (
    RequestBudget,
    acquire,
    load_snapshot,
    empty_snapshot,
    policy,
    display_devices,
    BASE_INTERVAL,
    FAST_INTERVAL,
)


class _Signals(QObject):
    finished = Signal(object, object)


class _Worker(QRunnable):
    def __init__(self, client, previous, stop, cache_path):
        super().__init__()
        self.client, self.previous, self.stop = client, previous, stop
        self.cache_path = cache_path
        self.signals = _Signals()

    def run(self):
        result, error = None, None
        try:
            result = acquire(self.client, self.previous, self.stop.is_set)
            if self.stop.is_set():
                raise TuyaError("cancelled", "Acquisizione Casa interrotta.")
            atomic_json(self.cache_path, result)
        except TuyaError as failure:
            result = None
            error = failure
        except OSError:
            result = None
            error = TuyaError(
                "storage", "Cache Casa non scrivibile; acquisizione non confermata."
            )
        except (ValueError, TypeError, KeyError):
            result = None
            error = TuyaError(
                "invalid", "Acquisizione Casa non valida; dati precedenti conservati."
            )
        finally:
            self.signals.finished.emit(result, error)


class CasaService(QObject):
    changed = Signal()
    refreshFinished = Signal(bool, str)

    def __init__(
        self,
        *,
        auto_refresh=True,
        config_path=None,
        state_dir=None,
        transport=http_get,
        clock=time.time,
        monotonic=time.monotonic,
        demo=False,
    ):
        super().__init__()
        self.clock, self.monotonic, self.transport = clock, monotonic, transport
        self.config_path = (
            Path(config_path)
            if config_path
            else Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
            / "smartpc/tuya-cloud.json"
        )
        self.policy_path = self.config_path.with_name("tuya-policy.json")
        self.state_dir = (
            Path(state_dir)
            if state_dir
            else Path(
                os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))
            )
            / "smartpc/casa"
        )
        self.client = self.budget = None
        self._snapshot = empty_snapshot("")
        self._busy = self._closed = self._visible = False
        self._worker = None
        self._stop = threading.Event()
        self._last_attempt = -float("inf")
        self._last_polling = False
        self._next = float("inf")
        self._errors = 0
        self._halted = False
        self._status, self._error = "unavailable", ""
        self._automatic_requested = True
        self._demo = demo
        self._timer = QTimer(self)
        self._timer.setInterval(5000)
        self._timer.timeout.connect(self._tick)
        if demo:
            self._snapshot = demo_snapshot(clock())
            self._status = "active"
        else:
            self.reloadConfig()
            if auto_refresh:
                self._timer.start()
                # One bounded initial discovery; never a recurring unknown-quota poll.
                if self.client and not self._snapshot["checkedAt"]:
                    QTimer.singleShot(0, self.refresh)
                elif self._automatic():
                    self._next = self.monotonic()

    @Slot(result=bool)
    def reloadConfig(self):
        if self._busy or self._closed or self._demo:
            return False
        try:
            config = load_config(self.config_path)
            client = CloudClient(config, clock=self.clock, monotonic=self.monotonic)
            cache = self.state_dir / (client.scope + ".json")
            budget = RequestBudget(
                self.state_dir / (client.scope + "-budget.json"),
                client.scope,
                policy(self.policy_path),
                self.clock,
            )

            def counted(url, headers, timeout):
                if self._stop.is_set():
                    raise TuyaError("cancelled", "Acquisizione Casa interrotta.")
                budget.charge()
                return self.transport(url, headers, min(timeout, 4.5))

            client.transport = counted
            self.client, self.budget, self._cache = client, budget, cache
            self._snapshot = load_snapshot(cache, client.scope)
            self._automatic_requested = self._snapshot["pollingRequested"]
            self._status = "stale" if self._snapshot["checkedAt"] else "unavailable"
            self._error, self._halted, self._errors = "", False, 0
            self._next = self.monotonic() if self._automatic() else float("inf")
        except TuyaError as error:
            self.client = self.budget = None
            self._snapshot = empty_snapshot("")
            self._status, self._error = "unavailable", str(error)
            self._next = float("inf")
        self._emit_changed()
        return self.client is not None

    def _emit_changed(self):
        self._last_polling = self._automatic()
        self.changed.emit()

    def _automatic(self):
        return bool(
            self.client
            and self.budget
            and self._automatic_requested
            and not self._halted
            and self.budget.automatic_available()
        )

    def _tick(self):
        if self._closed or self._demo or self._busy:
            return
        now = self.monotonic()
        automatic = self._automatic()
        fast = False
        pages = max(
            1, len([d for d in self._snapshot["devices"] if d["present"]]) // 50 + 1
        )
        if automatic and self._visible and not self._errors:
            fast = self.budget.can_boost(pages)
        if self._status == "active" and (
            self.clock() - self._snapshot["checkedAt"] >= 2 * BASE_INTERVAL
            or self.clock() < self._snapshot["checkedAt"] - 5
        ):
            self._status = "stale"
            self._emit_changed()
        interval = FAST_INTERVAL if fast else BASE_INTERVAL
        deadline = (
            min(self._next, self._last_attempt + FAST_INTERVAL) if fast else self._next
        )
        if automatic and now >= deadline and now - self._last_attempt >= interval:
            if fast:
                try:
                    if not self.budget.boost(FAST_INTERVAL, pages):
                        return
                except TuyaError:
                    return
            self.refresh()
        elif automatic != self._last_polling:
            self._emit_changed()

    @Slot(bool)
    def setVisible(self, visible):
        self._visible = visible
        if (
            visible
            and self._automatic()
            and self.clock() - self._snapshot["checkedAt"] >= FAST_INTERVAL
        ):
            self._next = min(self._next, self.monotonic())

    @Slot(result=bool)
    def refresh(self):
        if (
            self._demo
            or self._closed
            or not self.client
            or self._busy
            or self.monotonic() - self._last_attempt < 30
        ):
            return False
        try:
            self.budget._period(self.clock())
            if not self.budget.remaining():
                raise TuyaError(
                    "budget", "Budget Casa esaurito: aggiornamenti sospesi."
                )
        except TuyaError as error:
            self._error, self._status = str(error), "error"
            self._emit_changed()
            return False
        self._last_attempt = self.monotonic()
        self._busy = True
        self._status = "updating"
        self._error = ""
        worker = _Worker(self.client, deepcopy(self._snapshot), self._stop, self._cache)
        worker.signals.finished.connect(self._finished)
        self._worker = worker
        self._emit_changed()
        QThreadPool.globalInstance().start(worker)
        return True

    @Slot(object, object)
    def _finished(self, result, error):
        self._busy = False
        self._worker = None
        if self._closed:
            return
        ok = False
        if (
            error is None
            and isinstance(result, dict)
            and self.client
            and result.get("scope") == self.client.scope
        ):
            self._snapshot = result
            self._status, self._error, self._errors = "active", "", 0
            self._halted = False
            ok = True
        else:
            self._errors += 1
            error = (
                error
                if isinstance(error, TuyaError)
                else TuyaError("invalid", "Acquisizione Casa incompleta.")
            )
            self._status = "offline" if error.kind == "offline" else "error"
            self._error = str(error)
            # Known Tuya quota/service errors and HTTP 429 stop automatic retries.
            self._halted = error.kind in ("quota", "budget", "auth", "api", "token")
        delay = (
            BASE_INTERVAL
            if ok
            else min(3600, BASE_INTERVAL * 2 ** min(4, max(0, self._errors - 1)))
        )
        self._next = self.monotonic() + delay + (random.uniform(0, 10) if not ok else 0)
        self._emit_changed()
        self.refreshFinished.emit(ok, self._error)

    @Slot(str, result=bool)
    def toggleFavourite(self, identity):
        if (
            self._busy
            or self._closed
            or not any(d["id"] == identity for d in self._snapshot["devices"])
        ):
            return False
        result = deepcopy(self._snapshot)
        favourites = result["favourites"]
        if identity in favourites:
            favourites.remove(identity)
        elif len(favourites) < 4:
            favourites.append(identity)
        else:
            return False
        result["seeded"] = True
        return self._save_selection(result)

    @Slot(str, int, result=bool)
    def moveFavourite(self, identity, direction):
        if (
            self._busy
            or self._closed
            or direction not in (-1, 1)
            or identity not in self._snapshot["favourites"]
        ):
            return False
        result = deepcopy(self._snapshot)
        rows = result["favourites"]
        i = rows.index(identity)
        j = i + direction
        if not 0 <= j < len(rows):
            return False
        rows[i], rows[j] = rows[j], rows[i]
        return self._save_selection(result)

    def _save_selection(self, result):
        try:
            if not self._demo:
                atomic_json(self._cache, result)
        except OSError:
            self._error = "Preferiti non salvati."
            self._emit_changed()
            return False
        self._snapshot = result
        self._emit_changed()
        return True

    @Slot(result=bool)
    def togglePolling(self):
        if (
            self._closed
            or not self.budget
            or not self.budget.automatic_available()
            or self._busy
        ):
            return False
        result = deepcopy(self._snapshot)
        result["pollingRequested"] = not self._automatic_requested
        if not self._save_selection(result):
            return False
        self._automatic_requested = result["pollingRequested"]
        self._next = self.monotonic() + BASE_INTERVAL
        self._emit_changed()
        return True

    @Property("QVariantMap", notify=changed)
    def moduleState(self):
        devices = display_devices(self._snapshot, self._status)
        by_id = {d["id"]: d for d in devices}
        requested = self._snapshot["favourites"]
        automatic = self._automatic()
        data = {
            "devices": devices,
            "favourites": [by_id[i] for i in requested if i in by_id],
            "configured": self.client is not None or self._demo,
            "busy": self._busy,
            "polling": automatic,
            "quotaConfigured": bool(self.budget and self.budget.allocation),
            "requests": self.budget.data["requests"] if self.budget else 0,
            "remaining": self.budget.remaining() if self.budget else 0,
            "modeText": "Demo · dati simulati"
            if self._demo
            else "Polling attivo · 1/5 minuti entro budget"
            if automatic
            else "Aggiornamenti manuali · quota da configurare"
            if not self.budget or not self.budget.allocation
            else "Polling sospeso",
            "feedback": self._error,
            "readOnly": True,
        }
        return module_state(
            status=self._status,
            source="Tuya / Smart Life" + (" (demo)" if self._demo else ""),
            updated_at=self._snapshot["checkedAt"],
            data=data,
            error=self._error,
        )

    def close(self):
        self._closed = True
        self._timer.stop()
        self._stop.set()


def demo_snapshot(now):
    rows = []
    for identity, name, category, online, metrics in [
        (
            "demo-sensor",
            "Temperatura studio",
            "wsdcg",
            True,
            [("va_temperature", 0, "°C"), ("va_humidity", 55, "%")],
        ),
        (
            "demo-plug",
            "Presa PC",
            "cz",
            False,
            [("switch_1", True, ""), ("cur_power", 48, "W")],
        ),
        ("demo-light", "Lampada scrivania", "dj", True, [("switch_led", False, "")]),
        ("demo-motion", "Sensore movimento", "pir", False, [("pir", "pir", "")]),
    ]:
        rows.append(
            {
                "id": identity,
                "name": name,
                "category": category,
                "model": "demo",
                "productId": "demo",
                "online": online,
                "gatewayId": "",
                "subDevice": category != "dj",
                "present": True,
                "missingCount": 0,
                "states": [
                    {
                        "code": code,
                        "type": "boolean"
                        if type(value) is bool
                        else "enum"
                        if isinstance(value, str)
                        else "integer",
                        "value": value,
                        "unit": unit,
                        "quality": "reported",
                        "checkedAt": now,
                        "stale": False,
                    }
                    for code, value, unit in metrics
                ],
            }
        )
    return {
        "version": 1,
        "scope": "demo",
        "checkedAt": now,
        "devices": rows,
        "specifications": {},
        "favourites": [d["id"] for d in rows],
        "seeded": True,
    }
