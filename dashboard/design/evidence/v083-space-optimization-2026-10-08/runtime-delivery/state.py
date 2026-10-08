"""QML-facing module state and persistent display preferences."""

from __future__ import annotations

from datetime import datetime, timedelta
import os
import time
from typing import Any

from theme_service import ThemeService
from theme_core import ThemeError

from PySide6.QtCore import QObject, Property, QSettings, Signal, Slot

from module_state import module_state
from events import EventService


DEMO_WEATHER = {
    "location": "ANGRI · SALERNO",
    "temperature": "18°",
    "description": "Sereno",
    "code": 0,
    "feels_like": "17°C",
    "humidity": "64%",
    "rain_probability": "10%",
    "wind": "8 km/h · N",
    "gusts": "14 km/h",
    "precipitation": "0.0 mm",
    "forecast": [
        {"code":0,"day": "OGGI", "description": "Sereno", "high": "21°", "low": "14°", "rain": "10%"},
        {"code":3,"day": "DOMANI", "description": "Nuvoloso", "high": "20°", "low": "13°", "rain": "30%"},
        {"code":61,"day": "DOPODOMANI", "description": "Pioggia", "high": "18°", "low": "12°", "rain": "75%"},
    ],
}

MIN_BRIGHTNESS = 20
MAX_BRIGHTNESS = 100
BRIGHTNESS_STEP = 5
TOGGLEABLE_MODULES = ("meteo", "account", "sport", "f1", "motogp", "casa", "network")


def _account_threshold(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, default))
    except ValueError:
        return default
    return value if 1 <= value <= 100 else default


def _saved_int(settings: QSettings, key: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(settings.value(key, default))
    except (TypeError, ValueError):
        return default
    return value if minimum <= value <= maximum else default


def _saved_bool(settings: QSettings, key: str, default: bool = True) -> bool:
    value = settings.value(key, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in ("false", "0", "no")


class DashboardState(QObject):
    weatherChanged = Signal()
    accountChanged = Signal()
    sportChanged = Signal()
    racingChanged = Signal()
    networkChanged = Signal()
    networkMetricsChanged = Signal()
    networkMetricsRefreshFinished = Signal(bool,str)
    networkRefreshFinished = Signal(bool, str)
    casaChanged = Signal()
    casaRefreshFinished = Signal(bool, str)
    systemChanged = Signal()
    settingsChanged = Signal()
    sourceRefreshFinished = Signal(str, bool, str)
    modulesChanged = Signal()
    accountThresholdsChanged = Signal()
    eventChanged = Signal()

    def __init__(self, weather: QObject, system: QObject, account: QObject,
                 events: EventService | None = None, demo: bool = False, sport: QObject | None = None, racing=None, trace=None, casa=None, network=None) -> None:
        super().__init__()
        self.settingsChanged.connect(self.modulesChanged)
        self._weather = weather
        self._system = system
        self._account = account
        self._events = events
        self._sport = sport
        self._racing = racing or {}
        self._source_refresh_states: dict[str, dict] = {}
        self._network = network
        if network is not None:
            network.changed.connect(self.networkChanged)
            network.changed.connect(self.modulesChanged)
            network.refreshFinished.connect(self.networkRefreshFinished)
            network.metricsChanged.connect(self.networkMetricsChanged)
            network.metricsRefreshFinished.connect(self.networkMetricsRefreshFinished)
        self._casa = casa
        if casa is not None:
            casa.changed.connect(self.casaChanged)
            casa.changed.connect(self.settingsChanged)
            casa.refreshFinished.connect(self.casaRefreshFinished)
        self._account_warning_percent = _account_threshold("SMARTPC_ACCOUNT_WARNING_PERCENT", 80)
        self._account_critical_percent = max(
            self._account_warning_percent,
            _account_threshold("SMARTPC_ACCOUNT_CRITICAL_PERCENT", 95),
        )
        self._demo = demo
        self._scenario = "online"
        self._demo_event = False
        self._demo_alert_scenario = "nessuno"
        self._settings = QSettings("SmartPC", "Dashboard")
        self._account_warning_percent = _saved_int(self._settings, "account/warningPercent", min(99, self._account_warning_percent), 1, 99)
        self._account_critical_percent = max(self._account_warning_percent + 1,
            _saved_int(self._settings, "account/criticalPercent", self._account_critical_percent, 2, 100))
        self._theme_recovery_error = ""
        try:
            self._appearance = ThemeService(self, trace=trace)
            self._appearance.changed.connect(self.settingsChanged)
        except (ThemeError, OSError) as error:
            self._appearance = None
            self._theme_recovery_error = str(error)
        self._last_source_refresh: dict[str, float] = {}
        providers = {"meteo": weather, "account": account, "alerts": events,
                     "sport": sport, "casa": casa, "network": network, **self._racing}
        for source, provider in providers.items():
            if provider is not None and hasattr(provider, "refreshFinished"):
                provider.refreshFinished.connect(
                    lambda ok, message, name=source: self._finish_source_refresh(name, ok, message))
        self._module_visible = {
            module_id: _saved_bool(self._settings, f"moduleVisible/{module_id}")
            for module_id in TOGGLEABLE_MODULES
        }
        # Keep provider keys for rollback; the macroarea has an independent gate.
        self._sport_group_visible = _saved_bool(self._settings, "navigation/sportVisible",
                                              any(self._module_visible[k] for k in ("sport", "f1", "motogp")))
        if not self._settings.contains("navigation/schemaVersion"):
            self._settings.setValue("navigation/sportVisible", self._sport_group_visible)
            self._settings.setValue("navigation/schemaVersion", 1)
            self._settings.sync()
        saved = self._settings.value("nightMode", "auto")
        self._night_mode = saved if saved in ("auto", "day", "night") else "auto"
        brightness_mode = self._settings.value("brightnessMode", "auto")
        self._brightness_mode = brightness_mode if brightness_mode in ("auto", "manual") else "auto"
        self._manual_brightness = _saved_int(self._settings, "manualBrightness", 100, MIN_BRIGHTNESS, MAX_BRIGHTNESS)
        self._day_brightness = _saved_int(self._settings, "dayBrightness", 100, MIN_BRIGHTNESS, MAX_BRIGHTNESS)
        self._night_brightness = _saved_int(self._settings, "nightBrightness", 65, MIN_BRIGHTNESS, MAX_BRIGHTNESS)
        self._day_start_hour = _saved_int(self._settings, "dayStartHour", 7, 0, 23)
        self._night_start_hour = _saved_int(self._settings, "nightStartHour", 21, 0, 23)
        if self._day_start_hour == self._night_start_hour:
            self._day_start_hour, self._night_start_hour = 7, 21
        self._first_run = str(self._settings.value("seenCommands", "false")).lower() != "true"
        self._quiet_enabled = _saved_bool(self._settings, "notifications/quietEnabled", True)
        self._quiet_start = _saved_int(self._settings, "notifications/quietStart", 22 * 60, 0, 1439)
        self._quiet_end = _saved_int(self._settings, "notifications/quietEnd", 7 * 60, 0, 1439)
        self._weather_interruptions = _saved_bool(self._settings, "notifications/meteoInterruptions", True)
        self._account_interruptions = _saved_bool(self._settings, "notifications/accountInterruptions", True)
        if self._quiet_start == self._quiet_end:
            self._quiet_start, self._quiet_end = 22 * 60, 7 * 60
        if events is not None:
            events.set_quiet(self._quiet_enabled, self._quiet_start, self._quiet_end)
            events.set_category_silenced("meteo", not self._weather_interruptions)
            events.set_category_silenced("account", not self._account_interruptions)
            events.changed.connect(self.eventChanged)
        if sport is not None:
            sport.changed.connect(self.sportChanged)
            if events is not None:
                sport.eventsChanged.connect(lambda values: events.publish_snapshot("sport", values))
        for kind, service in self._racing.items():
            service.changed.connect(self.racingChanged)
            if events is not None:
                service.eventsChanged.connect(lambda values, k=kind: events.publish_snapshot("sport_"+k, values))
        weather.changed.connect(self.weatherChanged)
        account.changed.connect(self.accountChanged)
        system.changed.connect(self.systemChanged)

    @Property("QVariantMap", notify=weatherChanged)
    def weatherState(self) -> dict[str, Any]:
        if not self._demo:
            return self._weather.moduleState
        data = {} if self._scenario == "empty" else DEMO_WEATHER.copy()
        return module_state(
            status={"online": "active", "offline": "offline", "empty": "unavailable"}[self._scenario],
            source="Open-Meteo (demo)",
            updated_at=(datetime.now() - timedelta(hours=2 if self._scenario == "offline" else 0)).timestamp() if data else 0,
            data=data,
            error="Rete non disponibile" if self._scenario == "offline" else "",
        )

    @Property("QVariantMap", notify=systemChanged)
    def systemState(self) -> dict[str, Any]:
        return module_state(
            status="active", source="Linux", updated_at=self._system.updatedAt,
            data=self._system.data,
        )

    @Slot(bool)
    def setSystemInfoVisible(self, visible: bool) -> None:
        self._system.setMonitoring(visible)

    @Slot()
    def refreshSystemInfo(self) -> None:
        self._system.refresh()

    @Slot(str, result=bool)
    def refreshSource(self, source: str) -> bool:
        """Acceptance and completion are distinct; keep each provider's guards."""
        now = time.monotonic()
        if self._demo:
            self._set_source_refresh(source, "refused", "Demo · nessuna richiesta esterna")
            return False
        current = self._source_refresh_states.get(source, {})
        if current.get("status") in ("running", "queued"):
            self._set_source_refresh(source, current["status"], "Aggiornamento già in corso")
            return False
        if source not in ("casa", "network") and now - self._last_source_refresh.get(source, -60) < 30:
            self._set_source_refresh(source, "cooldown", "Attendi 30 secondi prima di riprovare")
            return False
        providers = {"meteo": self._weather, "account": self._account, "alerts": self._events,
                     "sport": self._sport, "casa": self._casa, "network": self._network, **self._racing}
        provider = providers.get(source)
        if provider is None:
            self._set_source_refresh(source, "unavailable", "Fonte non disponibile")
            return False
        action = (provider.refresh_weather_alerts if source == "alerts" else
                  provider.refreshManual if source == "sport" or source in self._racing else provider.refresh)
        self._set_source_refresh(source, "running", "Rilettura dal PC…" if source == "account" else "Aggiornamento in corso…")
        try:
            accepted = bool(action())
        except (OSError, RuntimeError):
            accepted = False
        if accepted:
            self._last_source_refresh[source] = now
            if source == "network" and getattr(provider, "_pending_refresh", False):
                self._set_source_refresh(source, "queued", "Aggiornamento accodato allo storico in corso")
            return True
        busy = bool(getattr(provider, "_worker", None) or getattr(provider, "_in_flight", False))
        message = "Aggiornamento già in corso" if busy else "Richiesta non accettata · verifica stato e attesa della fonte"
        self._set_source_refresh(source, "refused", message)
        return False

    @Property("QVariantMap", notify=settingsChanged)
    def sourceRefreshStates(self):
        return {name: value.copy() for name, value in self._source_refresh_states.items()}

    def _set_source_refresh(self, source, status, message):
        self._source_refresh_states[source] = {"status": status, "message": message,
                                               "updatedAt": time.time()}
        self.settingsChanged.emit()

    def _finish_source_refresh(self, source, ok, message):
        if self._source_refresh_states.get(source, {}).get("status") not in ("running", "queued"):
            return  # Scheduled acquisitions do not claim completion of a manual operation.
        self._set_source_refresh(source, "succeeded" if ok else "failed",
                                 message or ("Dati acquisiti e salvati" if ok else "Aggiornamento non riuscito · ultimi dati conservati"))
        self.sourceRefreshFinished.emit(source, ok, message)

    @Property('QVariantMap', notify=casaChanged)
    def casaState(self):
        return self._casa.moduleState if self._casa else module_state(status='unavailable',source='Tuya / Smart Life')

    @Property(bool, notify=casaChanged)
    def casaAvailable(self):
        data=self.casaState['data']
        return bool(data.get('configured') and data.get('favourites'))

    @Slot(bool)
    def setCasaVisible(self,visible):
        if self._casa: self._casa.setVisible(visible)

    @Slot(str,result=bool)
    def toggleCasaFavourite(self,identity):
        return bool(self._casa and self._casa.toggleFavourite(identity))

    @Slot(str,int,result=bool)
    def moveCasaFavourite(self,identity,direction):
        return bool(self._casa and self._casa.moveFavourite(identity,direction))

    @Slot(result=bool)
    def reloadCasaConfig(self):
        return bool(self._casa and self._casa.reloadConfig())

    @Slot(result=bool)
    def toggleCasaPolling(self):
        return bool(self._casa and self._casa.togglePolling())

    @Property('QVariantMap', notify=networkChanged)
    def networkState(self):
        return self._network.moduleState if self._network else module_state(status='unavailable',source='iliadbox')

    @Property(bool, notify=networkChanged)
    def networkAvailable(self):
        data=self.networkState['data']
        return bool(data.get('hasInventory'))

    @Slot(bool)
    def setNetworkVisible(self,visible):
        if self._network: self._network.setVisible(visible)

    @Slot(str,str,str,int,int,str)
    def setNetworkMetricsInterest(self,route,entity,section,hours,metric,station):
        if self._network:self._network.setMetricsInterest(route,entity,section,hours,metric,station)

    @Slot(str,str,str,int,int,str,result='QVariantMap')
    def networkMetricsView(self,route,entity,section,hours,metric,station):
        return self._network.metricsView(route,entity,section,hours,metric,station) if self._network else {}

    @Slot(result=bool)
    def refreshNetworkMetrics(self):
        return bool(self._network and self._network.refreshMetrics())

    @Slot(str,result=bool)
    def toggleNetworkFavourite(self,identity):
        return bool(self._network and self._network.toggleFavourite(identity))

    @Slot(str,int,result=bool)
    def moveNetworkFavourite(self,identity,direction):
        return bool(self._network and self._network.moveFavourite(identity,direction))

    @Slot(result=bool)
    def reloadNetworkConfig(self):
        return bool(self._network and self._network.reloadConfig())

    @Slot(result=bool)
    def toggleNetworkPolling(self):
        return bool(self._network and self._network.togglePolling())

    @Slot(str,str,result=bool)
    def setNetworkAlias(self,identity,alias):
        return bool(self._network and self._network.setAlias(identity,alias))

    @Property("QVariantMap", notify=accountChanged)
    def accountState(self) -> dict[str, Any]:
        if not self._demo:
            return self._account.moduleState
        return module_state(
            status="active", source="Codex App Server (demo)", updated_at=datetime.now().timestamp(),
            data={"plan": "Plus", "windows": [
                {"label": "Codex", "usedPercent": 34, "windowDurationMins": 300,
                 "resetsAt": (datetime.now() + timedelta(hours=3)).timestamp()},
                {"label": "Codex", "usedPercent": 37, "windowDurationMins": 10080,
                 "resetsAt": (datetime.now() + timedelta(days=4)).timestamp()},
            ], "credits": {"balance": "0", "unlimited": False}, "resetCredits": 3},
        )

    @Property(bool, constant=True)
    def sportAvailable(self) -> bool:
        return self._sport is not None

    @Property("QVariantMap", notify=sportChanged)
    def sportState(self) -> dict[str, Any]:
        return self._sport.moduleState if self._sport is not None else module_state(status="unavailable", source="FotMob / ESPN")

    @Property('QVariantList', constant=True)
    def racingAvailable(self):
        return list(self._racing)

    @Property('QVariantMap', notify=racingChanged)
    def racingStates(self):
        return {kind:service.moduleState for kind,service in self._racing.items()}

    @Slot(str,str,str)
    def selectRacing(self,kind,event_id,session_id):
        if kind in self._racing:self._racing[kind].select(event_id,session_id)

    @Slot(str,str,str,str)
    def selectRacingDriver(self,kind,event_id,session_id,driver_id):
        if kind in self._racing:self._racing[kind].selectDriver(event_id,session_id,driver_id)

    @Slot(str)
    def refreshRacingDetails(self,kind):
        if kind in self._racing:self._racing[kind].refreshDetails()

    @Slot(str)
    def clearRacingSelection(self,kind):
        if kind in self._racing:self._racing[kind].clearSelection()

    @Slot(str,int,int)
    def adjustRacingSetting(self,kind,row,direction):
        if kind in self._racing:self._racing[kind].adjust(row,direction)

    @Slot(str)
    def selectSportMatch(self, identity: str) -> None:
        if self._sport:
            self._sport.selectMatch(identity)

    @Slot(str)
    def setSportFavourite(self, identity):
        if self._sport: self._sport.setFavourite(identity)

    @Slot(str)
    def selectTeamMatch(self, identity):
        if self._sport: self._sport.selectTeamMatch(identity)

    @Slot()
    def refreshSportTeam(self):
        if self._sport: self._sport.refreshTeam()

    @Slot()
    def clearSportTeamSelection(self):
        if self._sport: self._sport.clearTeamSelection()

    @Slot(str)
    def selectFantacalcio(self, identity):
        if self._sport: self._sport.selectFantacalcio(identity)

    @Slot()
    def refreshFantacalcio(self):
        if self._sport: self._sport.refreshFantacalcio()

    @Slot()
    def clearFantacalcio(self):
        if self._sport: self._sport.clearFantacalcio()

    @Slot(int, int)
    def adjustSportSetting(self, row: int, direction: int) -> None:
        if not self._sport:
            return
        if row == 0:
            self._sport.cycleFavourite(direction)
        elif row == 1:
            self._sport.toggleHome()
        elif row == 2:
            self._sport.toggleGoals()
        elif row == 3:
            self._sport.cycleSeason(direction)
        elif row == 4:
            self._sport.refreshManual()

    @Property(int, notify=settingsChanged)
    def accountWarningPercent(self) -> int:
        return self._account_warning_percent

    @Property(int, notify=settingsChanged)
    def accountCriticalPercent(self) -> int:
        return self._account_critical_percent

    @Slot(int, int)
    def adjustAccountSetting(self, row: int, direction: int) -> None:
        if row not in (0, 1) or not direction:
            return
        step = 5 if direction > 0 else -5
        if row == 0:
            self._account_warning_percent = max(1, min(self._account_critical_percent - 1, self._account_warning_percent + step))
        else:
            self._account_critical_percent = max(self._account_warning_percent + 1, min(100, self._account_critical_percent + step))
        self._settings.setValue("account/warningPercent", self._account_warning_percent)
        self._settings.setValue("account/criticalPercent", self._account_critical_percent)
        self._settings.sync()
        self.settingsChanged.emit()
        self.accountThresholdsChanged.emit()

    @Property(bool, notify=settingsChanged)
    def animationsEnabled(self) -> bool:
        return self._appearance is not None and self._appearance.resolvedAppearance["motionMode"] != "off"

    @Slot()
    def toggleAnimations(self) -> None:
        if self._appearance is None: return
        self._appearance.beginEdit()
        self._appearance.setSection("motionMode", "off" if self.animationsEnabled else "normal")
        self._appearance.apply()

    @Property(str, constant=True)
    def themeRecoveryError(self):
        return self._theme_recovery_error

    @Property(QObject, constant=True)
    def appearance(self):
        return self._appearance

    @Property("QVariantList", notify=modulesChanged)
    def visibleModules(self) -> list[str]:
        return ["oggi"] + [module_id for module_id in TOGGLEABLE_MODULES
                           if self._module_visible[module_id] and (module_id != "sport" or self._sport is not None) and (module_id not in ("f1","motogp") or module_id in self._racing) and (module_id != "casa" or self.casaAvailable) and (module_id != "network" or self.networkAvailable)]

    @Property(bool, notify=modulesChanged)
    def sportGroupVisible(self):
        return self._sport_group_visible

    @Property("QVariantMap", notify=modulesChanged)
    def moduleVisibility(self):
        return {**self._module_visible, "sports": self._sport_group_visible}

    @Slot(str)
    def toggleModuleVisibility(self, module_id: str) -> None:
        if module_id == "sports":
            self._sport_group_visible = not self._sport_group_visible
            self._settings.setValue("navigation/sportVisible", self._sport_group_visible)
            self._settings.sync()
            self.settingsChanged.emit()
            return
        if module_id not in TOGGLEABLE_MODULES:
            return
        self._module_visible[module_id] = not self._module_visible[module_id]
        self._settings.setValue(f"moduleVisible/{module_id}", self._module_visible[module_id])
        self._settings.sync()
        self.settingsChanged.emit()

    @Property("QVariantMap", notify=eventChanged)
    def nextRelevantEvent(self) -> dict[str, Any]:
        if self._demo and self._demo_event:
            return {"type": "promemoria", "title": "Evento di prova", "when": "Tra 30 min"}
        return self._events.eventState.get("nextRelevantEvent", {}) if self._events else {}

    @Property("QVariantMap", notify=eventChanged)
    def eventsState(self) -> dict[str, Any]:
        return self._events.eventState if self._events else {
            "inbox": [], "urgent": {}, "visibleBanner": {}, "sourceStatus": "in attesa"}

    @Slot(str)
    def dismissEvent(self, event_id: str) -> None:
        if self._events:
            self._events.dismiss(event_id)

    @Slot(str)
    def markEventSeen(self, event_id: str) -> None:
        if self._events:
            self._events.markSeen(event_id)

    @Slot(bool)
    def setBannerAvailable(self, available: bool) -> None:
        if self._events:
            self._events.setBannerAvailable(available)

    @Slot(bool)
    def setBannerPresentationAcknowledgement(self, required: bool) -> None:
        if self._events: self._events.setPresentationAcknowledgement(required)

    @Slot(str, result=bool)
    @Slot(str, str, int, result=bool)
    def markBannerPresented(self, event_id: str, revision: str | None = None, rank: int = -1) -> bool:
        return bool(self._events and self._events.markBannerPresented(event_id, revision, rank))

    @Property(bool, notify=settingsChanged)
    def quietHoursEnabled(self) -> bool:
        return self._quiet_enabled

    @Property(int, notify=settingsChanged)
    def quietStartMinute(self) -> int:
        return self._quiet_start

    @Property(int, notify=settingsChanged)
    def quietEndMinute(self) -> int:
        return self._quiet_end

    @Property(bool, notify=settingsChanged)
    def weatherInterruptions(self) -> bool:
        return self._weather_interruptions

    @Property(bool, notify=settingsChanged)
    def accountInterruptions(self) -> bool:
        return self._account_interruptions

    @Slot(int, int)
    def adjustNotificationSetting(self, row: int, direction: int) -> None:
        step = 1 if direction > 0 else -1 if direction < 0 else 0
        if not step:
            return
        if row == 0:
            self._quiet_enabled = not self._quiet_enabled
            key, value = "notifications/quietEnabled", self._quiet_enabled
        elif row in (1, 2):
            attribute = "_quiet_start" if row == 1 else "_quiet_end"
            other = self._quiet_end if row == 1 else self._quiet_start
            value = (getattr(self, attribute) + step * 15) % 1440
            if value == other:
                value = (value + step * 15) % 1440
            setattr(self, attribute, value)
            key = "notifications/quietStart" if row == 1 else "notifications/quietEnd"
        elif row in (3, 4):
            attribute = "_weather_interruptions" if row == 3 else "_account_interruptions"
            value = not getattr(self, attribute)
            setattr(self, attribute, value)
            key = "notifications/meteoInterruptions" if row == 3 else "notifications/accountInterruptions"
        else:
            return
        self._settings.setValue(key, value)
        self._settings.sync()
        if self._events:
            self._events.set_quiet(self._quiet_enabled, self._quiet_start, self._quiet_end)
            self._events.set_category_silenced("meteo", not self._weather_interruptions)
            self._events.set_category_silenced("account", not self._account_interruptions)
        self.settingsChanged.emit()

    @Property(str, notify=settingsChanged)
    def nightMode(self) -> str:
        return self._appearance.resolvedAppearance.get("paletteMode", self._night_mode) if self._appearance else self._night_mode

    @Property(str, notify=settingsChanged)
    def brightnessMode(self) -> str:
        return self._brightness_mode

    @Property(int, notify=settingsChanged)
    def manualBrightness(self) -> int:
        return self._manual_brightness

    @Property(int, notify=settingsChanged)
    def dayBrightness(self) -> int:
        return self._day_brightness

    @Property(int, notify=settingsChanged)
    def nightBrightness(self) -> int:
        return self._night_brightness

    @Property(int, notify=settingsChanged)
    def dayStartHour(self) -> int:
        return self._day_start_hour

    @Property(int, notify=settingsChanged)
    def nightStartHour(self) -> int:
        return self._night_start_hour

    @Property(bool, notify=settingsChanged)
    def firstRun(self) -> bool:
        return self._first_run

    @Slot()
    def markCommandsSeen(self) -> None:
        if self._first_run:
            self._first_run = False
            self._settings.setValue("seenCommands", "true")
            self.settingsChanged.emit()

    @Slot()
    def cycleNightMode(self) -> None:
        self.adjustDisplaySetting(0, 1)

    @Slot(int, int)
    def adjustDisplaySetting(self, row: int, direction: int) -> None:
        """Adjust one System row with the keypad; values never hide the UI."""
        step = 1 if direction > 0 else -1 if direction < 0 else 0
        if not step:
            return
        if row == 0:
            if self._appearance is None: return
            modes = ("auto", "day", "night")
            self._appearance.beginEdit()
            self._appearance.setSection("paletteMode", modes[(modes.index(self.nightMode) + step) % len(modes)])
            self._appearance.apply()
            return
        elif row == 1:
            self._brightness_mode = "manual" if self._brightness_mode == "auto" else "auto"
            key, value = "brightnessMode", self._brightness_mode
        elif row in (2, 3, 4):
            attribute, key = {
                2: ("_manual_brightness", "manualBrightness"),
                3: ("_day_brightness", "dayBrightness"),
                4: ("_night_brightness", "nightBrightness"),
            }[row]
            current = getattr(self, attribute)
            value = max(MIN_BRIGHTNESS, min(MAX_BRIGHTNESS, current + step * BRIGHTNESS_STEP))
            if value == current:
                return
            setattr(self, attribute, value)
        elif row in (5, 6):
            attribute, other, key = (
                ("_day_start_hour", self._night_start_hour, "dayStartHour") if row == 5
                else ("_night_start_hour", self._day_start_hour, "nightStartHour")
            )
            value = (getattr(self, attribute) + step) % 24
            if value == other:
                value = (value + step) % 24
            setattr(self, attribute, value)
        else:
            return
        self._settings.setValue(key, value)
        self._settings.sync()
        self.settingsChanged.emit()

    @Property(bool, constant=True)
    def demo(self) -> bool:
        return self._demo

    @Property(str, notify=weatherChanged)
    def demoScenario(self) -> str:
        return self._scenario

    @Slot()
    def cycleDemoWeather(self) -> None:
        if self._demo:
            scenarios = ("online", "offline", "empty")
            self._scenario = scenarios[(scenarios.index(self._scenario) + 1) % len(scenarios)]
            self.weatherChanged.emit()

    @Slot()
    def toggleDemoEvent(self) -> None:
        if self._demo:
            self._demo_event = not self._demo_event
            self.eventChanged.emit()

    @Property(str, notify=eventChanged)
    def demoAlertScenario(self) -> str:
        return self._demo_alert_scenario

    @Slot()
    def cycleDemoAlert(self) -> None:
        if self._demo and self._events:
            scenarios = ("nessuno", "prossimo", "banner", "banner grande", "urgente")
            self._demo_alert_scenario = scenarios[(scenarios.index(self._demo_alert_scenario) + 1) % len(scenarios)]
            self._events.set_demo_scenario(self._demo_alert_scenario)
            self.eventChanged.emit()
