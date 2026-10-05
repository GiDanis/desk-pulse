"""Demand-driven editorial grades worker; one shared cache per matchweek."""

from copy import deepcopy
import os
from pathlib import Path
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
from fantacalcio_core import (
    SOURCE,
    page_key,
    eligible,
    presentation,
    selected_teams,
    read_cache,
    save_cache,
)
from sport_core import ProviderError
from fantacalcio_live import FantasyClient, live_window


class Signals(QObject):
    finished = Signal(object, object)


class Worker(QRunnable):
    def __init__(self, client, key, path, offline, ttl, match=None):
        super().__init__()
        self.signals = Signals()
        self.client = client
        self.key = key
        self.path = path
        self.offline = offline
        self.ttl = ttl
        self.match = deepcopy(match or {})
        self.cache_error = ""

    def run(self):
        try:
            if self.offline:
                raise ProviderError("Rete Fantacalcio disabilitata")
            page = (
                self.client.get_for_match(self.key, self.ttl, self.match)
                if hasattr(self.client, "get_for_match")
                else self.client.get(self.key, self.ttl)
            )
            if not page.get("provisional"):
                try:
                    historical = deepcopy(page)
                    historical.pop("liveNotice", None)
                    save_cache(self.path, historical)
                except (OSError, ValueError):
                    self.cache_error = "Cache voti non salvata"
            self.signals.finished.emit(page, None)
        except Exception as error:
            self.signals.finished.emit(None, error)


class FantacalcioService(QObject):
    changed = Signal()

    def __init__(self, directory, auto_refresh=True, parent=None):
        super().__init__(parent)
        self.directory = Path(directory)
        self.auto = auto_refresh
        self.closed = False
        self.client = FantasyClient(self.directory)
        self.match = {}
        self.key = ""
        self.page = None
        self.live_page = None
        self.from_cache = False
        self.error = ""
        self.cache_error = ""
        self.worker = None
        self.failures = 0
        self.last_manual = 0
        self.offline = os.environ.get("SMARTPC_SPORT_OFFLINE", "").lower() in (
            "1",
            "true",
            "yes",
        )
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.refresh)

    def path(self, key):
        return self.directory / ("fantacalcio-" + key.replace("/", "-") + ".json")

    def interval(self):
        if live_window(self.match):
            return 30
        kickoff = self.match.get("kickoffUtc") or 0
        return 300 if kickoff and time.time() - kickoff < 86400 else 21600

    def set_match(self, match):
        self.match = deepcopy(match or {})
        key = page_key(self.match)
        if key != self.key:
            self.timer.stop()
            self.key = key
            self.page = read_cache(self.path(key), key) if key else None
            self.live_page = None
            self.from_cache = bool(self.page)
            self.error = ""
            self.cache_error = ""
            self.failures = 0
        self.changed.emit()
        current_page = self.display_page()
        if (
            self.auto
            and key
            and (
                live_window(self.match)
                or self.match.get("status") in ("live", "half_time", "finished")
            )
            and (
                not current_page
                or self.from_cache
                and not current_page.get("provisional")
                or time.time() - current_page["fetchedAt"] >= self.interval()
            )
        ):
            self.refresh()

    def display_page(self):
        if (
            self.live_page
            and live_window(self.match)
            and time.time() - self.live_page["fetchedAt"] <= 120
            and len(selected_teams(self.live_page, self.match)) == 2
        ):
            return self.live_page
        return self.page

    @Property("QVariantMap", notify=changed)
    def moduleState(self):
        page = self.display_page()
        data = presentation(page, self.match)
        at = page.get("fetchedAt", 0) if page else 0
        data.update(
            selectedMatchId=self.match.get("canonicalMatchId", ""),
            loading=bool(self.worker),
            fromCache=self.from_cache and not data.get("provisional"),
            cacheError=self.cache_error,
        )
        data["message"] = (
            "Voti disponibili solo per le partite di Serie A."
            if not eligible(self.match)
            else (
                "Formazioni disponibili vicino al calcio d’inizio; voti durante la partita."
                if self.match.get("status") == "scheduled"
                and not live_window(self.match)
                else (
                    "Attendo la giornata dal dettaglio della partita."
                    if not self.key
                    else (
                        "Voti non ancora pubblicati per questo incontro."
                        if not data.get("published")
                        else ""
                    )
                )
            )
        )
        status = (
            "offline"
            if self.error and page
            else (
                "error"
                if self.error
                else (
                    "updating"
                    if self.worker
                    else (
                        "stale"
                        if page
                        and (data["fromCache"] or time.time() - at > self.interval())
                        else "active" if page else "unavailable"
                    )
                )
            )
        )
        return module_state(
            status=status, source=SOURCE, updated_at=at, data=data, error=self.error
        )

    @Slot()
    def refresh(self):
        if self.closed:
            return
        if (
            self.worker
            or not self.key
            or not (
                live_window(self.match)
                or self.match.get("status") in ("live", "half_time", "finished")
            )
        ):
            return
        w = Worker(
            self.client,
            self.key,
            self.path(self.key),
            self.offline,
            self.interval(),
            self.match,
        )
        w.signals.finished.connect(self._finished)
        self.worker = w
        QThreadPool.globalInstance().start(w)
        self.changed.emit()

    def refresh_manual(self):
        if time.monotonic() - self.last_manual < 30:
            return
        self.last_manual = time.monotonic()
        # Bypass the short memory TTL, retaining valid disk data on failure.
        if hasattr(self.client, "pages"):
            self.client.pages.pop(self.key, None)
        if hasattr(self.client, "live"):
            self.client.live.pages.pop(self.key, None)
        self.refresh()

    @Slot(object, object)
    def _finished(self, page, error):
        w = self.worker
        self.worker = None
        if self.closed or w is None:
            return
        if w.key != self.key:
            if self.auto:
                self.refresh()
            return
        if page:
            if page.get("provisional"):
                self.live_page = page
            else:
                self.page = page
                if self.match.get("status") == "finished" and presentation(
                    page, self.match
                ).get("published"):
                    self.live_page = None
            self.from_cache = False
            self.error = ""
            self.cache_error = w.cache_error
            self.failures = 0
        else:
            self.error = "Aggiornamento voti non riuscito."
            self.failures += 1
        self.changed.emit()
        if self.auto and self.key:
            retry = (
                max(
                    getattr(error, "retry_after", 0),
                    min(900, 60 * 2 ** min(self.failures, 4)),
                )
                if error
                else self.interval()
            )
            self.timer.start(int(min(retry, 86400) * 1000))

    def clear(self):
        changed = bool(self.match or self.key or self.page is not None or
                       self.live_page is not None or self.from_cache or
                       self.error or self.cache_error)
        self.timer.stop()
        self.match = {}
        self.key = ""
        self.page = None
        self.live_page = None
        self.from_cache = False
        self.error = ""
        self.cache_error = ""
        if changed:
            self.changed.emit()

    def close(self):
        self.closed = True
        self.auto = False
        self.timer.stop()
        self.key = ""
