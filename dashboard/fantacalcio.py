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
    Client,
    SOURCE,
    page_key,
    eligible,
    presentation,
    read_cache,
    save_cache,
)
from sport_core import ProviderError


class Signals(QObject):
    finished = Signal(object, object)


class Worker(QRunnable):
    def __init__(self, client, key, path, offline, ttl):
        super().__init__()
        self.signals = Signals()
        self.client = client
        self.key = key
        self.path = path
        self.offline = offline
        self.ttl = ttl
        self.cache_error = ""

    def run(self):
        try:
            if self.offline:
                raise ProviderError("Rete Fantacalcio disabilitata")
            page = self.client.get(self.key, self.ttl)
            try:
                save_cache(self.path, page)
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
        self.client = Client()
        self.match = {}
        self.key = ""
        self.page = None
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
        if self.match.get("status") in ("live", "half_time"):
            return 90
        kickoff = self.match.get("kickoffUtc") or 0
        return 300 if kickoff and time.time() - kickoff < 86400 else 21600

    def set_match(self, match):
        self.match = deepcopy(match or {})
        key = page_key(self.match)
        if key != self.key:
            self.timer.stop()
            self.key = key
            self.page = read_cache(self.path(key), key) if key else None
            self.from_cache = bool(self.page)
            self.error = ""
            self.cache_error = ""
            self.failures = 0
        self.changed.emit()
        if (
            self.auto
            and key
            and self.match.get("status") in ("live", "half_time", "finished")
            and (
                not self.page
                or self.from_cache
                or time.time() - self.page["fetchedAt"] >= self.interval()
            )
        ):
            self.refresh()

    @Property("QVariantMap", notify=changed)
    def moduleState(self):
        data = presentation(self.page, self.match)
        at = self.page.get("fetchedAt", 0) if self.page else 0
        data.update(
            selectedMatchId=self.match.get("canonicalMatchId", ""),
            loading=bool(self.worker),
            fromCache=self.from_cache,
            cacheError=self.cache_error,
        )
        data["message"] = (
            "Voti disponibili solo per le partite di Serie A."
            if not eligible(self.match)
            else (
                "Formazioni e voti saranno disponibili dopo la pubblicazione."
                if self.match.get("status") == "scheduled"
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
            if self.error and self.page
            else (
                "error"
                if self.error
                else (
                    "updating"
                    if self.worker
                    else (
                        "stale"
                        if self.page
                        and (self.from_cache or time.time() - at > self.interval())
                        else "active" if self.page else "unavailable"
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
            or self.match.get("status") not in ("live", "half_time", "finished")
        ):
            return
        w = Worker(
            self.client, self.key, self.path(self.key), self.offline, self.interval()
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
            self.page = page
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
        self.timer.stop()
        self.match = {}
        self.key = ""
        self.page = None
        self.from_cache = False
        self.error = ""
        self.cache_error = ""
        self.changed.emit()

    def close(self):
        self.closed = True
        self.auto = False
        self.timer.stop()
        self.key = ""
