"""Independent per-discipline workers, persistent cache and lazy GP detail."""

from copy import deepcopy
from datetime import datetime
import logging, os, time
from pathlib import Path
from PySide6.QtCore import (
    QObject,
    Property,
    QRunnable,
    QSettings,
    QStandardPaths,
    QThreadPool,
    QTimer,
    Signal,
    Slot,
)
from module_state import module_state
from sport_core import ProviderError, ROME
from motorsport_core import (
    MOTO,
    MotorClient,
    refresh,
    load_event,
    read_cache,
    save_cache,
    present,
)
from racing_timing import F1Timing, moto_timing
from racing_details import load_driver


class Signals(QObject):
    finished = Signal(object, object)


class Worker(QRunnable):
    def __init__(
        self,
        client,
        kind,
        year,
        previous,
        selection,
        full,
        offline,
        driver_id="",
        force=False,
    ):
        super().__init__()
        self.signals = Signals()
        self.client = client
        self.kind = kind
        self.year = year
        self.previous = previous
        self.cache_error = ""
        self.selection = selection
        self.driver_id = driver_id
        self.full = full
        self.offline = offline
        self.force = force

    def run(self):
        try:
            if self.offline:
                raise ProviderError("Offline di prova")
            data = (
                refresh(self.client, self.kind, self.year, self.previous)
                if self.full
                else deepcopy(self.previous)
            )
            if self.selection[0]:
                data = load_event(self.client, data, *self.selection, force=self.force)
                if self.driver_id:
                    data = load_driver(
                        self.client,
                        data,
                        *self.selection,
                        self.driver_id,
                        force=self.force
                    )
            if (
                self.kind == "motogp"
                and self.year == datetime.now(ROME).year
                and any(
                    e["start"]
                    and e["end"]
                    and e["start"] - 86400 < time.time() < e["end"] + 86400
                    for e in data["events"]
                )
            ):
                try:
                    raw, at = self.client.get(MOTO + "timing-gateway/livetiming-lite")
                    data["timingRaw"] = raw
                    data["timingAt"] = at
                except (ProviderError, ValueError):
                    pass
            try:
                save_cache(self.cache_path, data)
                for path in self.cache_path.parent.glob(
                    self.kind + "-[0-9][0-9][0-9][0-9].json"
                ):
                    if path.name not in {
                        self.kind + "-" + str(year) + ".json" for year in self.years
                    }:
                        path.unlink()
            except (OSError, ValueError):
                self.cache_error = "Cache non salvata"
            self.signals.finished.emit(data, None)
        except Exception as error:
            self.signals.finished.emit(None, error)


class MotorsportService(QObject):
    changed = Signal()
    eventsChanged = Signal(object)

    def __init__(self, kind, *, auto_refresh=True, cache_directory=None, initial=None):
        super().__init__()
        self.kind = kind
        self._auto = auto_refresh
        self._closed = False
        root = cache_directory or QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.CacheLocation
        )
        self._directory = Path(root)
        self._settings = QSettings("SmartPC", "Dashboard")
        self._years = [datetime.now(ROME).year, datetime.now(ROME).year - 1]
        try:
            saved = int(
                self._settings.value("motorsport/" + kind + "/year", self._years[0])
            )
        except (TypeError, ValueError):
            saved = self._years[0]
        self._year = saved if saved in self._years else self._years[0]
        self._snapshot = (
            deepcopy(initial)
            if initial and initial.get("year") == self._year
            else self._read_cache()
        )
        self._from_cache = bool(self._snapshot) and not initial
        self._error = ""
        self._cache_error = ""
        self._selection = ("", "")
        self._driver_id = ""
        self._client = MotorClient()
        self._worker = None
        self._last_full = 0
        self._last_manual = 0
        self._failures = 0
        self._offline = os.environ.get("SMARTPC_SPORT_OFFLINE") == "1"
        self._home = (
            str(self._settings.value("motorsport/" + kind + "/home", "false")).lower()
            == "true"
        )
        self._verified = (
            os.environ.get("SMARTPC_" + kind.upper() + "_LIVE_VERIFIED") == "1"
        )
        self._timing = F1Timing(self) if kind == "f1" else None
        if self._timing:
            self._timing.changed.connect(self.changed)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.refresh)
        self._age = QTimer(self)
        self._age.setInterval(1000 if kind == "f1" else 15000)
        self._age.timeout.connect(self._tick)
        self._age.start()
        self._last_live_signature = None
        self._view_snapshot = None
        self._view = None
        self._view_until = 0
        self._view_at = 0
        self._view_from_cache = None
        if auto_refresh:
            QTimer.singleShot(0, self.refresh)

    def _cache_path(self):
        return self._directory / (self.kind + "-" + str(self._year) + ".json")

    def _read_cache(self):
        data = read_cache(self._cache_path(), self.kind)
        return data if data and data["year"] == self._year else None

    def _data_view(self, now):
        # Source snapshots are replaced by completed workers, never edited by
        # QML. Reuse derived rows between revisions, retaining exact time
        # boundaries for sessions, GP expiry and the next-session window.
        if (
            self._view is None
            or self._snapshot is not self._view_snapshot
            or self._from_cache != self._view_from_cache
            or now >= self._view_until
            or now < self._view_at
        ):
            self._view = present(self._snapshot, now, from_cache=self._from_cache)
            self._view_snapshot = self._snapshot
            self._view_from_cache = self._from_cache
            self._view_at = now
            deadlines = [now + 60]
            for event in self._view["events"]:
                if event.get("end") and event["end"] >= now:
                    deadlines.append(event["end"] + 0.001)
                for session in event["sessions"]:
                    start = session.get("start")
                    if start:
                        if start >= now and session["state"] != "finished":
                            deadlines.append(start + 0.001)
                        if start + 1800 >= now:
                            deadlines.append(start + 1800 + 0.001)
            self._view_until = min(deadlines)
        return self._view

    def _near(self):
        now = time.time()
        return bool(
            self._year == self._years[0]
            and self._snapshot
            and any(
                e.get("end")
                and min(
                    [s["start"] for s in e["sessions"] if s["start"]]
                    or [e["start"] or float("inf")]
                )
                - 3600
                <= now
                <= e["end"] + 86400
                for e in self._snapshot["events"]
            )
        )

    def _tick(self):
        now = time.time()
        current = datetime.now(ROME).year
        if current != self._years[0] and not self._worker:
            was_current = self._year == self._years[0]
            self._years = [current, current - 1]
            if was_current or self._year not in self._years:
                self._year = current
                self._selection = ("", "")
                self._driver_id = ""
                self._snapshot = self._read_cache()
                self._from_cache = bool(self._snapshot)
                self._last_full = 0
                if self._auto:
                    self.refresh()
            self.changed.emit()
        if self._timing:
            eligible = bool(
                self._auto
                and not self._offline
                and self._year == self._years[0]
                and self._snapshot
                and any(
                    s["start"] and -45 * 60 <= now - s["start"] <= 6 * 3600
                    for e in self._snapshot["events"]
                    for s in e["sessions"]
                )
            )
            self._timing.ensure(eligible)
            live = self._timing.state.present(now, self._year, self._verified)
            signature = (
                live["active"],
                live["isLive"],
                self._timing.state.revision,
                live["status"],
                id(self._data_view(now)),
                bool(self._snapshot and now - self._snapshot["fetchedAt"] > 21600),
            )
            if signature != self._last_live_signature:
                self._last_live_signature = signature
                self.changed.emit()
        else:
            self.changed.emit()

    @Property("QVariantMap", notify=changed)
    def moduleState(self):
        now = time.time()
        data = self._data_view(now).copy()
        data.update(
            selectedEventId=self._selection[0],
            selectedSessionId=self._selection[1],
            detailLoading=bool(self._worker),
            availableYears=self._years,
            selectedYear=self._year,
            showOnHome=self._home,
            cacheError=self._cache_error,
            liveVerified=self._verified,
        )
        live = (
            self._timing.state.present(now, self._year, self._verified)
            if self._timing
            else (
                moto_timing(
                    self._snapshot.get("timingRaw", {}),
                    self._snapshot,
                    self._snapshot.get("timingAt", 0),
                    now,
                    self._verified,
                )
                if self._snapshot
                else {}
            )
        )
        if self._from_cache or self._error or self._offline:
            live.update(active=False, isLive=False)
        data["live"] = live
        at = self._snapshot.get("fetchedAt", 0) if self._snapshot else 0
        status = (
            "offline"
            if self._error and self._snapshot
            else (
                "error"
                if self._error
                else (
                    "stale"
                    if self._from_cache or at and now - at > 21600
                    else (
                        "updating"
                        if self._worker
                        else "active" if self._snapshot else "unavailable"
                    )
                )
            )
        )
        return module_state(
            status=status,
            source="Jolpica" if self.kind == "f1" else "PulseLive",
            updated_at=at,
            data=data,
            error=self._error,
        )

    @Slot()
    def refresh(self, detail_only=False, force=False):
        if self._closed or self._worker:
            return
        near = self._near()
        full = not detail_only and (
            not self._snapshot
            or time.time() - self._last_full >= (900 if near else 21600)
        )
        worker = Worker(
            self._client,
            self.kind,
            self._year,
            self._snapshot,
            self._selection,
            full or not self._snapshot,
            self._offline,
            self._driver_id,
            force,
        )
        worker.cache_path = self._cache_path()
        worker.years = self._years[:]
        worker.signals.finished.connect(self._finished)
        self._worker = worker
        QThreadPool.globalInstance().start(worker)
        self.changed.emit()

    @Slot()
    def refreshDetails(self):
        if time.monotonic() - self._last_manual < 30 or self._worker:
            return
        self._last_manual = time.monotonic()
        self.refresh(True, force=True)

    @Slot(str, str)
    def select(self, event_id, session_id=""):
        self._selection = (event_id, session_id)
        self._driver_id = ""
        self.refresh(True)
        self.changed.emit()

    @Slot(str, str, str)
    def selectDriver(self, event_id, session_id, driver_id):
        self._selection = (event_id, session_id)
        self._driver_id = driver_id
        self.refresh(True)
        self.changed.emit()

    @Slot(object, object)
    def _finished(self, data, error):
        worker = self._worker
        self._worker = None
        if self._closed or worker is None:
            return
        if data:
            self._snapshot = data
            self._error = ""
            self._failures = 0
            if worker.full:
                self._last_full = time.time()
                self._from_cache = False
            self._cache_error = worker.cache_error
        else:
            logging.getLogger(__name__).warning("%s: %s", self.kind, error)
            self._error = "Aggiornamento non riuscito. Ultimi dati conservati."
            self._failures += 1
        self.changed.emit()
        self._publish_home()
        self._tick()
        if (
            worker.selection != self._selection or worker.driver_id != self._driver_id
        ) and self._selection[0]:
            self.refresh(True)
            return
        if self._auto:
            near = self._near()
            delay = 60 if near else 21600
            if self._error:
                delay = max(
                    getattr(error, "retry_after", 0),
                    min(900, 60 * 2 ** min(self._failures, 4)),
                )
            self._timer.start(int(delay * 1000))

    def _publish_home(self):
        state = self.moduleState
        data = state["data"]
        values = []
        event = data.get("nextEvent", {})
        race = next((s for s in event.get("sessions", []) if s["kind"] == "RAC"), {})
        start = race.get("start")
        if (
            self._home
            and state["status"] in ("active", "updating")
            and start
            and 0 < start - time.time() < 7 * 86400
        ):
            values = [
                {
                    "version": 1,
                    "id": event["id"] + ":home",
                    "source": "sport_" + self.kind,
                    "sourceLabel": state["source"],
                    "category": "sport",
                    "priority": 1,
                    "type": "promemoria",
                    "title": (
                        ("F1" if self.kind == "f1" else "MotoGP")
                        + " · "
                        + event["name"]
                    )[:100],
                    "detail": "Gara · " + race.get("when", ""),
                    "issuedAt": state["updatedAt"],
                    "startsAt": start,
                    "expiresAt": start + 3 * 3600,
                    "revision": str(start),
                    "showOnHome": True,
                }
            ]
        self.eventsChanged.emit(values)

    @Slot()
    def clearSelection(self):
        self._selection = ("", "")
        self._driver_id = ""

    @Slot(int, int)
    def adjust(self, row, direction):
        if row == 0:
            if self._worker:
                return
            self._year = self._years[(self._years.index(self._year) + 1) % 2]
            self._settings.setValue("motorsport/" + self.kind + "/year", self._year)
            self._snapshot = self._read_cache()
            self._from_cache = bool(self._snapshot)
            self._selection = ("", "")
            self._driver_id = ""
            self._last_full = 0
            self._error = ""
            if self._timing:
                self._timing.close()
            self.changed.emit()
            self.eventsChanged.emit([])
            self.refresh()
        elif row == 1:
            self._home = not self._home
            self._settings.setValue("motorsport/" + self.kind + "/home", self._home)
            self.changed.emit()
            self._publish_home()
        elif row == 2 and time.monotonic() - self._last_manual >= 30:
            self._last_manual = time.monotonic()
            self._last_full = 0
            self.refresh(force=True)
        self._settings.sync()

    def close(self):
        self._closed = True
        self._auto = False
        self._selection = ("", "")
        self._driver_id = ""
        self._timer.stop()
        self._age.stop()
        if self._timing:
            self._timing.close()
