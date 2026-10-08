"""Qt Sport service: workers, adaptive polling, persistent cache and preferences."""

from __future__ import annotations
from copy import deepcopy
import os
import logging
from pathlib import Path
import random
import time

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
from sport_team import FavouriteTeamService
from fantacalcio import FantacalcioService
from sport_team_core import league_fallback
from sport_core import (
    GoalTracker,
    HTTPClient,
    ProviderError,
    home_event,
    poll_interval,
    presentation,
    read_cache,
    refresh_detail,
    refresh_snapshot,
    save_cache,
    season_for,
)


def env_flag(name):
    return os.environ.get(name, "").lower() in ("1", "true", "yes")


class _Signals(QObject):
    finished = Signal(object, object)


class _Worker(QRunnable):
    def __init__(
        self,
        client,
        previous,
        selected,
        full,
        offline,
        season,
        detail_only=False,
        cache_paths=(),
        retained_seasons=(),
    ):
        super().__init__()
        self.signals = _Signals()
        self.client, self.previous, self.selected = client, previous, selected
        self.full, self.offline, self.season = full, offline, season
        self.detail_only = detail_only
        self.cache_paths = cache_paths
        self.retained_seasons = retained_seasons
        self.cache_error = ""

    def run(self):
        try:
            if self.offline:
                raise ProviderError("Rete Sport disabilitata per verifica offline")
            value = (
                refresh_detail(self.client, self.previous, time.time(), self.selected)
                if self.detail_only
                else refresh_snapshot(
                    self.client,
                    self.previous,
                    time.time(),
                    selected_id=self.selected,
                    full=self.full,
                    requested_season=self.season,
                )
            )
            if (
                not self.previous
                or value["fetchedAt"] >= self.previous["fetchedAt"]
                or value["season"] != self.previous["season"]
            ):
                try:
                    for path in self.cache_paths:
                        save_cache(path, value)
                    if self.cache_paths:
                        retained = {
                            "sport-" + s.replace("/", "-") + ".json"
                            for s in self.retained_seasons
                        }
                        for archived in self.cache_paths[0].parent.glob(
                            "sport-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9].json"
                        ):
                            if archived.name not in retained:
                                archived.unlink()
                except (OSError, ValueError):
                    # Valid network data remains usable even on a full disk.
                    self.cache_error = "Cache non salvata"
        except Exception as error:
            value, failure = None, error
        else:
            failure = None
        try:
            self.signals.finished.emit(value, failure)
        except RuntimeError:
            pass  # Qt receivers can already be gone during application shutdown.


class SportService(QObject):
    changed = Signal()
    refreshFinished = Signal(bool, str)
    eventsChanged = Signal(object)

    def __init__(
        self,
        *,
        auto_refresh=True,
        cache_path=None,
        state_path=None,
        initial=None,
        verified=None,
    ):
        super().__init__()
        location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.CacheLocation
        )
        self._cache_path = (
            Path(cache_path)
            if cache_path
            else Path(location or Path.home() / ".cache/smartpc") / "sport.json"
        )
        state_directory = os.environ.get("STATE_DIRECTORY", "").split(":")[0]
        base = (
            Path(state_directory)
            if state_directory
            else Path(
                os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))
            )
            / "smartpc-dashboard"
        )
        self._tracker = GoalTracker(
            Path(state_path) if state_path else base / "sport-goals.json"
        )
        self._settings = QSettings("SmartPC", "Dashboard")
        current = season_for(time.time())
        year = int(current.split("/")[0])
        self._seasons = [current, f"{year-1}/{year}"]
        saved_season = str(self._settings.value("sport/season", current))
        self._season = saved_season if saved_season in self._seasons else current
        self._snapshot = deepcopy(initial) if initial else read_cache(self._cache_path)
        if self._snapshot and self._snapshot.get("season") != self._season:
            self._snapshot = read_cache(self._season_cache_path())
        self._from_cache = bool(self._snapshot) and not initial
        self._verified = (
            env_flag("SMARTPC_SPORT_LIVE_VERIFIED") if verified is None else verified
        )
        self._offline = env_flag("SMARTPC_SPORT_OFFLINE")
        self._client = HTTPClient()
        self._worker = None
        self._error = ""
        self._cache_error = ""
        self._failures = 0
        self._checked_at = 0.0
        self._last_full = 0.0
        self._last_manual = 0.0
        self._selected_id = ""
        self._favourite = str(self._settings.value("sport/favourite", ""))
        self._home_enabled = (
            str(self._settings.value("sport/showOnHome", "false")).lower() == "true"
        )
        self._goals_enabled = (
            str(self._settings.value("sport/goalsEnabled", "false")).lower() == "true"
            and self._verified
        )
        self._fantasy_requested = ""
        self._fantasy = FantacalcioService(self._cache_path.parent, auto_refresh, self)
        self._fantasy.changed.connect(self.changed)
        self._team = FavouriteTeamService(self._cache_path.parent, auto_refresh, self)
        self._team.changed.connect(self.changed)
        self._team.changed.connect(self._sync_fantasy)
        self._sync_team()
        self._auto_refresh = auto_refresh
        self._closed = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(lambda: self.refresh())
        # Reevaluate Live freshness even during a stalled worker/backoff.
        self._age_timer = QTimer(self)
        self._age_timer.setInterval(15000)
        self._age_timer.timeout.connect(self._age_changed)
        self._age_timer.start()
        if auto_refresh:
            QTimer.singleShot(0, lambda: self.refresh())

    def _age_changed(self):
        self.changed.emit()
        self._publish_events()

    def _data(self):
        data = presentation(
            self._snapshot,
            time.time(),
            from_cache=self._from_cache,
            verified=self._verified,
            favourite=self._favourite,
        )
        data.update(
            checkedAt=self._checked_at,
            cacheError=self._cache_error,
            favourite=self._favourite,
            showOnHome=self._home_enabled,
            goalsEnabled=self._goals_enabled,
            selectedSeason=self._season,
            availableSeasons=self._seasons,
            selectedMatchId=self._selected_id,
            detailLoading=bool(self._worker and self._selected_id),
            requestCount=dict(self._client.request_count),
        )
        team = self._team.moduleState
        if self._favourite and not team["data"].get("name"):
            fallback = league_fallback(data, self._favourite)
            team = dict(
                team,
                data=fallback,
                source=fallback.get("source", team["source"]),
                updatedAt=fallback.get("fetchedAt", 0),
            )
        data["favouriteTeam"] = team
        data["fantacalcio"] = self._fantasy.moduleState
        return data

    def _sync_team(self):
        dirty = False
        if self._snapshot and self._snapshot.get("provider") == "fotmob":
            for match in self._snapshot.get("fixtures", []):
                for side in ("home", "away"):
                    identity, provider_id = match.get(side + "TeamId"), match.get(
                        side + "ProviderId", ""
                    )
                    if identity and str(provider_id).isdigit():
                        key = "sport/fotmobTeamId/" + identity
                        if str(self._settings.value(key, "")) != str(provider_id):
                            self._settings.setValue(key, str(provider_id))
                            dirty = True
        if dirty:
            self._settings.sync()
        provider_id = (
            str(self._settings.value("sport/fotmobTeamId/" + self._favourite, ""))
            if self._favourite
            else ""
        )
        self._team.select_team(provider_id, self._favourite)

    @Slot(str)
    def setFavourite(self, identity):
        teams = presentation(self._snapshot, time.time()).get("teams", [])
        if identity and identity not in [t["id"] for t in teams]:
            return
        self._favourite = identity
        self._settings.setValue("sport/favourite", identity)
        self._settings.sync()
        self._sync_team()
        self.changed.emit()
        self._publish_events(force_preferences=True)

    @Slot(str)
    def selectTeamMatch(self, identity):
        if identity.startswith("team:foto:"):
            self._team.select_match(identity)
        else:
            self.selectMatch(identity)

    @Slot()
    def refreshTeam(self):
        self._team.refresh_manual()

    @Slot()
    def clearTeamSelection(self):
        self._team.clear_selection()

    def _sync_fantasy(self):
        if not self._fantasy_requested:
            return
        fixtures = (self._snapshot or {}).get("fixtures", []) + (
            self._team.snapshot or {}
        ).get("fixtures", [])
        match = next(
            (m for m in fixtures if m["canonicalMatchId"] == self._fantasy_requested),
            None,
        )
        if match:
            match = deepcopy(match)
            if not match.get("round") and match.get("providerLeagueId") == 55:
                league_match = next(
                    (
                        m
                        for m in fixtures
                        if m.get("competitionId") == "serie_a"
                        and m.get("season") == match.get("season")
                        and (m["homeTeamId"], m["awayTeamId"])
                        == (match["homeTeamId"], match["awayTeamId"])
                    ),
                    {},
                )
                match["round"] = league_match.get("round", "")
            self._fantasy.set_match(match)

    @Slot(str)
    def selectFantacalcio(self, identity):
        self._fantasy_requested = identity
        self._sync_fantasy()

    @Slot()
    def refreshFantacalcio(self):
        self._fantasy.refresh_manual()

    @Slot()
    def clearFantacalcio(self):
        self._fantasy_requested = ""
        self._fantasy.clear()

    def close(self):
        self._closed = True
        self._auto_refresh = False
        self._timer.stop()
        self._age_timer.stop()
        self._team.close()
        self._fantasy.close()

    @Property("QVariantMap", notify=changed)
    def moduleState(self):
        data = self._data()
        stale_live = any(not m.get("fresh") for m in data.get("activeMatches", []))
        fetched = self._snapshot.get("fetchedAt", 0) if self._snapshot else 0
        if self._error:
            status = "offline" if self._snapshot else "error"
        elif (
            self._from_cache
            or stale_live
            or self._snapshot
            and (
                time.time() - fetched > 21600
                or self._snapshot.get("season") != self._season
            )
        ):
            status = "stale"
        elif self._worker:
            status = "updating"
        elif self._snapshot:
            status = "active"
        else:
            status = "unavailable"
        if status in ("offline", "stale", "error"):
            for match in data.get("fixtures", []):
                match["isLive"] = False
        return module_state(
            status=status,
            source={"fotmob": "FotMob", "espn": "ESPN"}.get(
                data.get("provider"), "FotMob / ESPN"
            ),
            updated_at=fetched,
            data=data,
            error=self._error,
        )

    @Slot(result=bool)
    def refresh(self, detail_only=False):
        if self._closed or self._worker:
            return False
        now = time.time()
        current = season_for(now)
        if current != self._seasons[0]:
            previous_current = self._seasons[0]
            year = int(current.split("/")[0])
            self._seasons = [current, f"{year-1}/{year}"]
            if self._season == previous_current or self._season not in self._seasons:
                self._season = current
                self._last_full = 0
                self._settings.setValue("sport/season", current)
        self._checked_at = now
        full = (
            not self._snapshot
            or now - self._last_full >= 21600
            or self._snapshot.get("season") != self._season
        )
        detail_only = bool(
            detail_only
            and self._snapshot
            and self._snapshot.get("season") == self._season
        )
        worker = _Worker(
            self._client,
            self._snapshot,
            self._selected_id,
            full and not detail_only,
            self._offline,
            self._season,
            detail_only,
            cache_paths=(self._cache_path, self._season_cache_path()),
            retained_seasons=tuple(self._seasons),
        )
        worker.signals.finished.connect(self._finished)
        self._worker = worker
        QThreadPool.globalInstance().start(worker)
        self.changed.emit()
        return True

    @Slot(result=bool)
    def refreshManual(self):
        if self._closed or self._worker or time.monotonic() - self._last_manual < 30:
            return False
        self._last_manual = time.monotonic()
        self._last_full = 0
        return self.refresh()

    @Slot(str)
    def selectMatch(self, identity):
        self._selected_id = identity
        self.refresh(detail_only=True)
        self.changed.emit()

    @Slot(object, object)
    def _finished(self, snapshot, error):
        cache_error = self._worker.cache_error if self._worker else ""
        full = self._worker.full if self._worker else False
        detail_only = self._worker.detail_only if self._worker else False
        completed_selection = (
            self._worker.selected if self._worker else self._selected_id
        )
        self._worker = None
        if self._closed:
            return
        now = time.time()
        if snapshot:
            if (
                not self._snapshot
                or snapshot["fetchedAt"] >= self._snapshot["fetchedAt"]
                or snapshot["season"] != self._snapshot["season"]
            ):
                if (
                    self._snapshot
                    and snapshot["provider"] != self._snapshot["provider"]
                ):
                    self._tracker.disconnect()
                self._snapshot = snapshot
                if not detail_only:
                    self._from_cache = False
                self._error = ""
                self._failures = 0
                if full:
                    self._last_full = now
                self._cache_error = cache_error
            interval = poll_interval(self._snapshot, now)
        else:
            previous_error = self._error
            self._error = (
                "Aggiornamento Sport non riuscito. Dati salvati disponibili."
                if self._snapshot
                else "Dati Sport non disponibili. Riprova tra poco."
            )
            if self._error != previous_error:
                logging.getLogger(__name__).warning(
                    "Sport: %s; cache=%s", error, bool(self._snapshot)
                )
            self._failures += 1
            self._tracker.disconnect()
            interval = max(
                getattr(error, "retry_after", 0),
                min(300, 60 * 2 ** min(self._failures - 1, 3)),
            )
            interval += random.uniform(0, 5)
        self._sync_team()
        self._sync_fantasy()
        self.changed.emit()
        self._publish_events()
        self.refreshFinished.emit(bool(snapshot) and not cache_error,
                                  "Dati acquisiti · cache non salvata" if snapshot and cache_error else self._error)
        if (
            self._snapshot
            and completed_selection != self._selected_id
            and self._selected_id
        ):
            self.refresh(detail_only=True)
        elif self._auto_refresh:
            self._timer.start(int(min(interval, 86400) * 1000))

    def _publish_events(self, force_preferences=False):
        state = self.moduleState
        data = state["data"]
        if state["status"] not in ("active", "updating") or not self._snapshot:
            self._tracker.disconnect()
            if force_preferences:
                self.eventsChanged.emit([])
            return  # Error preserves the event source; existing expiry still applies.
        now = time.time()
        notices = self._tracker.update(
            data, now, self._goals_enabled and self._verified
        )
        self.eventsChanged.emit(
            home_event(data, self._favourite, self._home_enabled, now) + notices
        )

    @Slot(int)
    def cycleFavourite(self, direction):
        teams = [""] + [t["id"] for t in self._data().get("teams", [])]
        index = teams.index(self._favourite) if self._favourite in teams else 0
        self.setFavourite(teams[(index + (1 if direction >= 0 else -1)) % len(teams)])

    @Slot()
    def toggleHome(self):
        self._home_enabled = not self._home_enabled
        self._settings.setValue("sport/showOnHome", self._home_enabled)
        self._settings.sync()
        self.changed.emit()
        self._publish_events(force_preferences=True)

    @Slot()
    def toggleGoals(self):
        if not self._verified:
            return
        self._goals_enabled = not self._goals_enabled
        self._settings.setValue("sport/goalsEnabled", self._goals_enabled)
        self._settings.sync()
        self._tracker.disconnect()
        self.changed.emit()
        self._publish_events()

    def _season_cache_path(self):
        return self._cache_path.with_name(
            "sport-" + self._season.replace("/", "-") + ".json"
        )

    @Slot(int)
    def cycleSeason(self, direction):
        if self._worker:
            return
        index = self._seasons.index(self._season)
        self._season = self._seasons[
            (index + (1 if direction >= 0 else -1)) % len(self._seasons)
        ]
        self._settings.setValue("sport/season", self._season)
        self._settings.sync()
        self._snapshot = read_cache(self._season_cache_path())
        self._from_cache = bool(self._snapshot)
        self._error = ""
        self._selected_id = ""
        self._last_full = 0
        self._tracker.disconnect()
        self.eventsChanged.emit([])
        self.changed.emit()
        self.refresh()
