"""QML-facing module state and persistent display preferences."""

from __future__ import annotations

from datetime import datetime, timedelta
import os
from typing import Any

from PySide6.QtCore import QObject, Property, QSettings, Signal, Slot

from module_state import module_state


DEMO_WEATHER = {
    "location": "ANGRI · SALERNO",
    "temperature": "18°",
    "description": "Sereno",
    "feels_like": "17°C",
    "humidity": "64%",
    "rain_probability": "10%",
    "wind": "8 km/h · N",
    "gusts": "14 km/h",
    "precipitation": "0.0 mm",
    "forecast": [
        {"day": "OGGI", "description": "Sereno", "high": "21°", "low": "14°", "rain": "10%"},
        {"day": "DOMANI", "description": "Nuvoloso", "high": "20°", "low": "13°", "rain": "30%"},
        {"day": "DOPODOMANI", "description": "Pioggia", "high": "18°", "low": "12°", "rain": "75%"},
    ],
}

MIN_BRIGHTNESS = 20
MAX_BRIGHTNESS = 100
BRIGHTNESS_STEP = 5
TOGGLEABLE_MODULES = ("meteo", "account")


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
    systemChanged = Signal()
    settingsChanged = Signal()
    eventChanged = Signal()

    def __init__(self, weather: QObject, system: QObject, account: QObject, demo: bool = False) -> None:
        super().__init__()
        self._weather = weather
        self._system = system
        self._account = account
        self._account_warning_percent = _account_threshold("SMARTPC_ACCOUNT_WARNING_PERCENT", 80)
        self._account_critical_percent = max(
            self._account_warning_percent,
            _account_threshold("SMARTPC_ACCOUNT_CRITICAL_PERCENT", 95),
        )
        self._demo = demo
        self._scenario = "online"
        self._demo_event = False
        self._settings = QSettings("SmartPC", "Dashboard")
        self._module_visible = {
            module_id: _saved_bool(self._settings, f"moduleVisible/{module_id}")
            for module_id in TOGGLEABLE_MODULES
        }
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
            status="active", source="Orange Pi", updated_at=datetime.now().timestamp(),
            data={"cpuTemperature": self._system.cpuTemperature,
                  "memoryUsage": self._system.memoryUsage,
                  "uptime": self._system.uptimeText},
        )

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

    @Property(int, constant=True)
    def accountWarningPercent(self) -> int:
        return self._account_warning_percent

    @Property(int, constant=True)
    def accountCriticalPercent(self) -> int:
        return self._account_critical_percent

    @Property("QVariantList", notify=settingsChanged)
    def visibleModules(self) -> list[str]:
        return ["oggi"] + [module_id for module_id in TOGGLEABLE_MODULES if self._module_visible[module_id]]

    @Slot(str)
    def toggleModuleVisibility(self, module_id: str) -> None:
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
        return {}

    @Property(str, notify=settingsChanged)
    def nightMode(self) -> str:
        return self._night_mode

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
            modes = ("auto", "day", "night")
            self._night_mode = modes[(modes.index(self._night_mode) + step) % len(modes)]
            key, value = "nightMode", self._night_mode
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
