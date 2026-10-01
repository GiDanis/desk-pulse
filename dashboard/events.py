"""Qt bridge for the shared event engine and its provider adapters."""

from __future__ import annotations

import math
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, QTimer, Signal, Slot

from event_core import EventEngine
from weather_alerts import BulletinProvider, BulletinSnapshot, default_bulletin_cache_path

ROME = ZoneInfo("Europe/Rome")


def default_store_path() -> Path:
    base = os.environ.get("STATE_DIRECTORY")
    if base:
        return Path(base.split(":")[0]) / "events.sqlite3"
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "smartpc-dashboard/events.sqlite3"


class _WorkerSignals(QObject):
    finished = Signal(object, object)


class _AlertWorker(QRunnable):
    def __init__(self, provider: BulletinProvider) -> None:
        super().__init__()
        self.provider = provider
        self.signals = _WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result, error = self.provider.refresh(time.time()), None
        except Exception as exc:
            result, error = None, str(exc)
        try:
            self.signals.finished.emit(result, error)
        except RuntimeError:
            pass


class EventService(QObject):
    changed = Signal()

    def __init__(self, *, path: Path | str | None = None, auto_refresh: bool = True) -> None:
        super().__init__()
        store_path = path or default_store_path()
        self._engine = EventEngine(store_path)
        cache_path = (None if str(store_path) == ":memory:" else
                      default_bulletin_cache_path() if path is None else
                      Path(store_path).parent / "dpc-bulletin.json")
        self._alert_provider = BulletinProvider(cache_path)
        self._engine.prune()
        self._last_prune = time.time()
        self._quiet_enabled = True
        self._quiet_start = 22 * 60
        self._quiet_end = 7 * 60
        self._silenced_categories: frozenset[str] = frozenset()
        self._source_status = "in attesa"
        self._source_checked_at = 0.0
        self._source_fetched_at = 0.0
        self._source_from_cache = False
        self._source_bulletin_key = ""
        self._demo_sequence = 0
        self._in_flight = False
        self._worker: _AlertWorker | None = None
        self._banner: dict[str, Any] = {}
        self._banner_until = 0.0
        self._banner_available = False
        self._snapshot: dict[str, Any] = {}

        cached = self._alert_provider.load(time.time())
        if cached is not None:
            persisted_key = self._engine.source_revision("weather-alert")
            if persisted_key > cached.key:
                # A previous cache-write failure must not resurrect an older alert.
                self._source_status = "persistente · cache precedente"
                self._source_bulletin_key = persisted_key
            else:
                self._engine.replace_source("weather-alert", cached.events, revision=cached.key)
                self._source_status = "cache · da verificare"
                self._source_checked_at = cached.checked_at
                self._source_fetched_at = cached.fetched_at
                self._source_bulletin_key = cached.key
            self._source_from_cache = True

        self._banner_timer = QTimer(self)
        self._banner_timer.setSingleShot(True)
        self._banner_timer.timeout.connect(self._finish_banner)

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(60_000)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start()

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(30 * 60_000)
        self._poll_timer.timeout.connect(self.refresh_weather_alerts)
        if auto_refresh:
            self._poll_timer.start()
            QTimer.singleShot(0, self.refresh_weather_alerts)
        self._tick()

    def set_quiet(self, enabled: bool, start: int, end: int) -> None:
        if not 0 <= start < 1440 or not 0 <= end < 1440 or start == end:
            raise ValueError("Invalid quiet hours")
        self._quiet_enabled = enabled
        self._quiet_start = start
        self._quiet_end = end
        self._tick()

    def _is_quiet(self, now: float) -> bool:
        if not self._quiet_enabled:
            return False
        local = datetime.fromtimestamp(now, ROME)
        minute = local.hour * 60 + local.minute
        if self._quiet_start < self._quiet_end:
            return self._quiet_start <= minute < self._quiet_end
        return minute >= self._quiet_start or minute < self._quiet_end

    def set_category_silenced(self, category: str, silenced: bool) -> None:
        categories = set(self._silenced_categories)
        if silenced:
            categories.add(category)
        else:
            categories.discard(category)
        self._silenced_categories = frozenset(categories)
        self._tick()

    def _finish_banner(self) -> None:
        self._banner_until = 0.0
        self._tick()

    def _tick(self) -> None:
        now = time.time()
        if now - self._last_prune >= 86400:
            self._engine.prune(now)
            self._last_prune = now
        snapshot = self._engine.snapshot(now=now, quiet=self._is_quiet(now),
                                         silenced_categories=self._silenced_categories)
        active_ids = {item["id"] for item in snapshot["inbox"]}
        if self._banner and (time.monotonic() >= self._banner_until
                             or self._banner["expiresAt"] <= now or snapshot["urgent"]
                             or self._banner["id"] not in active_ids or self._is_quiet(now)
                             or self._banner["category"] in self._silenced_categories):
            self._banner = {}
            self._banner_timer.stop()
        if not self._banner and self._banner_available and not snapshot["urgent"] and snapshot["banner"]:
            self._banner = snapshot["banner"]
            self._banner_until = time.monotonic() + 8.0
            self._banner_timer.start(8000)
            self._engine.mark_notified(self._banner["id"])
            snapshot = self._engine.snapshot(now=now, quiet=self._is_quiet(now),
                                             silenced_categories=self._silenced_categories)
        snapshot["visibleBanner"] = self._banner
        snapshot["sourceStatus"] = self._source_status
        snapshot["sourceCheckedAt"] = self._source_checked_at
        snapshot["sourceFetchedAt"] = self._source_fetched_at
        snapshot["sourceFromCache"] = self._source_from_cache
        snapshot["sourceBulletinKey"] = self._source_bulletin_key
        if snapshot != self._snapshot:
            self._snapshot = snapshot
            self.changed.emit()

    @Property("QVariantMap", notify=changed)
    def eventState(self) -> dict[str, Any]:
        return self._snapshot

    def publish_snapshot(self, source: str, values: list[dict[str, Any]]) -> bool:
        """Common entry point for any module's last valid event snapshot.

        Call on the Qt/main thread (worker results should arrive via a signal).
        An empty *valid* snapshot cancels that source's previous events. Network
        failures must preserve the last snapshot rather than publish an empty one.
        """
        if getattr(self, "_closed", False):
            return False
        changed = self._engine.replace_source(source, values)
        self._tick()
        return changed

    @Slot(bool)
    def setBannerAvailable(self, available: bool) -> None:
        self._banner_available = available
        self._tick()

    @Slot(str)
    def dismiss(self, event_id: str) -> None:
        self._engine.dismiss(event_id)
        if self._banner.get("id") == event_id:
            self._banner = {}
        self._tick()

    @Slot(str)
    def markSeen(self, event_id: str) -> None:
        self._engine.mark_seen(event_id)
        self._tick()

    def ingest_account(self, state: dict[str, Any], warning: int, critical: int) -> None:
        if state.get("status") != "active":
            return
        updated = state.get("updatedAt")
        now = time.time()
        if (type(updated) not in (int, float) or not math.isfinite(updated)
                or updated <= 0 or updated > now + 600 or now - updated > 1800):
            return
        data = state.get("data")
        if not isinstance(data, dict):
            return
        windows = data.get("windows", [])
        if not isinstance(windows, list):
            return
        events = []
        for index, window in enumerate(windows):
            if not isinstance(window, dict):
                continue
            used = window.get("usedPercent")
            if type(used) not in (int, float) or not warning <= used <= 100:
                continue
            reset = window.get("resetsAt")
            reset_at = float(reset) if type(reset) in (int, float) and math.isfinite(reset) and reset > now else 0.0
            expires = min(updated + 1800, reset_at) if reset_at else updated + 1800
            if expires <= now:
                continue
            duration = window.get("windowDurationMins")
            duration = int(duration) if type(duration) in (int, float) and math.isfinite(duration) else 0
            label = str(window.get("label") or "Codex")[:40]
            priority = 2 if used >= critical else 1
            events.append({
                "version": 1,
                "id": f"account:{index}:{duration}:{int(reset_at)}",
                "source": "account",
                "sourceLabel": "Account ChatGPT",
                "category": "account",
                "priority": priority,
                "title": f"Uso {label}: {used:.0f}%",
                "detail": f"Finestra di {duration} minuti · Account ChatGPT",
                "issuedAt": updated,
                "startsAt": min(updated, now),
                "expiresAt": expires,
                "revision": str(int(updated)),
                "sourceUrl": "",
                "showOnHome": False,
            })
        self.publish_snapshot("account", events)

    def set_demo_scenario(self, scenario: str) -> None:
        if scenario not in ("nessuno", "prossimo", "banner", "banner grande", "urgente"):
            raise ValueError("Unknown demo scenario")
        self._demo_sequence += 1
        if scenario == "nessuno":
            values = []
        else:
            now = time.time()
            priority = {"prossimo": 1, "banner": 2, "banner grande": 2, "urgente": 3}[scenario]
            values = [{
                "version": 1, "id": f"demo:{self._demo_sequence}", "source": "demo",
                "sourceLabel": "Demo",
                "category": "demo", "priority": priority,
                "bannerSize": "large" if scenario == "banner grande" else "small",
                "title": {"prossimo": "Allerta prevista", "banner": "Avviso di prova",
                          "banner grande": "Avviso grande di prova",
                          "urgente": "Allerta prioritaria di prova"}[scenario],
                "detail": ("Evento simulato · nessuna fonte esterna. Il modulo può scegliere questo formato "
                           "per dare più spazio al titolo e alla descrizione." if scenario == "banner grande"
                           else "Evento simulato · nessuna fonte esterna"),
                "issuedAt": now, "startsAt": now + 1800 if scenario == "prossimo" else now - 1,
                "expiresAt": now + 3600, "revision": str(self._demo_sequence),
                "sourceUrl": "", "showOnHome": scenario == "prossimo",
            }]
        self.publish_snapshot("demo", values)

    @Slot()
    def refresh_weather_alerts(self) -> None:
        if self._in_flight:
            return
        self._in_flight = True
        worker = _AlertWorker(self._alert_provider)
        worker.signals.finished.connect(self._on_weather_finished)
        self._worker = worker
        QThreadPool.globalInstance().start(worker)

    @Slot(object, object)
    def _on_weather_finished(self, result: object, error: object) -> None:
        self._in_flight = False
        self._worker = None
        if isinstance(result, BulletinSnapshot):
            try:
                if result.key < self._engine.source_revision("weather-alert"):
                    raise ValueError("Bollettino precedente ai dati persistenti")
                self._engine.replace_source("weather-alert", result.events, revision=result.key)
                self._source_status = "aggiornata · bollettino invariato" if result.unchanged else "aggiornata"
                if result.cache_error:
                    self._source_status += " · cache non salvata"
                self._source_checked_at = result.checked_at
                self._source_fetched_at = result.fetched_at
                self._source_from_cache = False
                self._source_bulletin_key = result.key
            except (ValueError, KeyError) as exc:
                self._source_status = f"errore: {exc}"
        else:
            prefix = "cache · " if self._source_from_cache else ""
            self._source_status = f"{prefix}non aggiornata: {str(error or 'errore')[:80]}"
        self._tick()

    def close(self) -> None:
        self._closed = True
        self._banner_timer.stop()
        self._tick_timer.stop()
        self._poll_timer.stop()
        self._engine.close()
