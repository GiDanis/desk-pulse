"""One club worker at a time, durable profile cache and latest-selection wins."""

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
from sport_core import HTTPClient, ProviderError
from sport_team_core import refresh, save_cache, read_cache, present, profile_interval


class Signals(QObject):
    finished = Signal(object, object)


class Worker(QRunnable):
    def __init__(
        self,
        client,
        provider_id,
        team_id,
        previous,
        match_id,
        path,
        offline,
        detail_only,
    ):
        super().__init__()
        self.signals = Signals()
        self.client = client
        self.provider_id = provider_id
        self.team_id = team_id
        self.previous = previous
        self.match_id = match_id
        self.path = path
        self.offline = offline
        self.detail_only = detail_only
        self.cache_error = ""

    def run(self):
        try:
            if self.offline:
                raise ProviderError("Squadra: rete disabilitata per prova offline")
            data = refresh(
                self.client,
                self.provider_id,
                self.team_id,
                self.previous,
                self.match_id,
                self.detail_only,
            )
            try:
                save_cache(self.path, data)
            except (OSError, ValueError):
                self.cache_error = "Cache squadra non salvata"
            self.signals.finished.emit(data, None)
        except Exception as error:
            self.signals.finished.emit(None, error)


class FavouriteTeamService(QObject):
    changed = Signal()

    def __init__(self, directory, auto_refresh=True, parent=None):
        super().__init__(parent)
        self.directory = Path(directory)
        self.auto = auto_refresh
        self.closed = False
        self.provider_id = ""
        self.team_id = ""
        self.selection = ""
        self.snapshot = None
        self.from_cache = False
        self.error = ""
        self.cache_error = ""
        self.worker = None
        self.client = HTTPClient()
        self.failures = 0
        self.offline = os.environ.get("SMARTPC_SPORT_OFFLINE") == "1"
        self.last_manual = 0
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.refresh)

    def path(self):
        return self.directory / ("sport-team-" + self.provider_id + ".json")

    def select_team(self, provider_id, team_id):
        if (provider_id, team_id) == (self.provider_id, self.team_id):
            return
        self.timer.stop()
        self.provider_id = provider_id
        self.team_id = team_id
        self.selection = ""
        self.error = ""
        self.cache_error = ""
        self.failures = 0
        self.snapshot = (
            read_cache(self.path(), provider_id, team_id) if provider_id else None
        )
        self.from_cache = bool(self.snapshot)
        self.changed.emit()
        if self.auto and provider_id:
            self.refresh()

    @Property("QVariantMap", notify=changed)
    def moduleState(self):
        data = present(self.snapshot, time.time(), self.team_id, self.from_cache)
        data.update(
            detailLoading=bool(self.worker and self.selection),
            selectedMatchId=self.selection,
            cacheError=self.cache_error,
            detailError=self.snapshot.get("detailError", "") if self.snapshot else "",
            detailErrorMatchId=(
                self.snapshot.get("detailErrorMatchId", "") if self.snapshot else ""
            ),
        )
        at = self.snapshot.get("fetchedAt", 0) if self.snapshot else 0
        status = (
            "offline"
            if self.error and self.snapshot
            else (
                "error"
                if self.error
                else (
                    "stale"
                    if self.from_cache or at and time.time() - at > 21600
                    else (
                        "updating"
                        if self.worker
                        else "active" if self.snapshot else "unavailable"
                    )
                )
            )
        )
        return module_state(
            status=status, source="FotMob", updated_at=at, data=data, error=self.error
        )

    @Slot()
    def refresh(self, detail_only=False):
        if self.closed or self.worker or not self.provider_id:
            return
        w = Worker(
            self.client,
            self.provider_id,
            self.team_id,
            self.snapshot,
            self.selection,
            self.path(),
            self.offline,
            detail_only and bool(self.snapshot),
        )
        w.signals.finished.connect(self._finished)
        self.worker = w
        QThreadPool.globalInstance().start(w)
        self.changed.emit()

    def select_match(self, identity):
        self.selection = identity
        self.refresh(True)
        self.changed.emit()

    @Slot(object, object)
    def _finished(self, data, error):
        w = self.worker
        self.worker = None
        if self.closed or w is None:
            return
        if (w.provider_id, w.team_id) != (self.provider_id, self.team_id):
            if self.provider_id:
                self.refresh()
            return
        if data:
            self.snapshot = data
            self.error = ""
            self.cache_error = w.cache_error
            self.failures = 0
            if not w.detail_only:
                self.from_cache = False
        else:
            self.error = (
                "Aggiornamento squadra non riuscito. Dati precedenti disponibili."
            )
            self.failures += 1
        self.changed.emit()
        if w.match_id != self.selection and self.selection:
            self.refresh(True)
        elif self.auto:
            matches = self.snapshot.get("fixtures", []) if self.snapshot else []
            interval = profile_interval(matches, time.time())
            self.timer.start(
                int(
                    max(
                        getattr(error, "retry_after", 0),
                        min(900, 60 * 2 ** min(self.failures, 4)),
                    )
                    if error
                    else interval
                )
                * 1000
            )

    def refresh_manual(self):
        if time.monotonic() - self.last_manual < 30:
            return
        self.last_manual = time.monotonic()
        self.refresh()

    def clear_selection(self):
        self.selection = ""

    def close(self):
        self.closed = True
        self.auto = False
        self.selection = ""
        self.timer.stop()
