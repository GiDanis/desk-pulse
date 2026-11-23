"""Open-Meteo adapter for the SmartPC dashboard.

Network access and JSON parsing run in a worker thread. The QML-facing service
keeps a small on-disk cache so the last successful forecast remains available
when the device starts without an Internet connection.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
import time
from threading import Event
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from PySide6.QtCore import QObject, Property, QRunnable, QStandardPaths, QThreadPool, QTimer, Signal, Slot

from module_state import module_state


LATITUDE = 40.73815
LONGITUDE = 14.57070
TIMEZONE = "Europe/Rome"
REFRESH_INTERVAL_MS = 15 * 60 * 1000
REQUEST_TIMEOUT_SECONDS = 12
MAX_AGE_SECONDS = 30 * 60
API_URL = "https://api.open-meteo.com/v1/forecast"

WEEKDAYS_IT = (
    "LUNEDÌ", "MARTEDÌ", "MERCOLEDÌ", "GIOVEDÌ", "VENERDÌ", "SABATO", "DOMENICA"
)
WEATHER_CODES_IT = {
    0: "Sereno",
    1: "Prevalentemente sereno",
    2: "Parzialmente nuvoloso",
    3: "Coperto",
    45: "Nebbia",
    48: "Nebbia con brina",
    51: "Pioviggine leggera",
    53: "Pioviggine moderata",
    55: "Pioviggine intensa",
    56: "Pioviggine gelata leggera",
    57: "Pioviggine gelata intensa",
    61: "Pioggia debole",
    63: "Pioggia moderata",
    65: "Pioggia intensa",
    66: "Pioggia gelata debole",
    67: "Pioggia gelata intensa",
    71: "Neve debole",
    73: "Neve moderata",
    75: "Neve intensa",
    77: "Granuli di neve",
    80: "Rovesci deboli",
    81: "Rovesci moderati",
    82: "Rovesci intensi",
    85: "Rovesci di neve deboli",
    86: "Rovesci di neve intensi",
    95: "Temporale",
    96: "Temporale con grandine debole",
    99: "Temporale con grandine intensa",
}


def _number(value: Any, decimals: int = 0, suffix: str = "") -> str:
    if _finite(value) is None:
        return "—"
    return f"{value:.{decimals}f}{suffix}"


def _finite(value):
    return value if type(value) in (int,float) and math.isfinite(value) else None


def _rain_value(hourly, current_time):
    times=hourly.get("time",[]); values=hourly.get("precipitation_probability",[])
    if not isinstance(times,list) or not isinstance(values,list) or len(times)!=len(values): return None
    try:
        current=datetime.fromisoformat(current_time)
        candidates=[(abs((datetime.fromisoformat(stamp)-current).total_seconds()),value)
                    for stamp,value in zip(times,values) if isinstance(stamp,str) and _finite(value) is not None]
        return min(candidates,key=lambda item:item[0])[1] if candidates else None
    except (ValueError,TypeError): return None


def _weather_description(code: Any) -> str:
    try:
        return WEATHER_CODES_IT.get(int(code), "Condizioni variabili")
    except (TypeError, ValueError, OverflowError):
        return "Condizioni non disponibili"


def _wind_direction(degrees: Any) -> str:
    try:
        directions = ("N", "NE", "E", "SE", "S", "SO", "O", "NO")
        return directions[round(float(degrees) / 45) % 8]
    except (TypeError, ValueError, OverflowError):
        return "—"


def _nearest_precipitation_probability(hourly: dict[str, Any], current_time: str) -> str:
    times = hourly.get("time", [])
    probabilities = hourly.get("precipitation_probability", [])
    if not isinstance(times, list) or not isinstance(probabilities, list) or len(times) != len(probabilities):
        return "—"
    try:
        current = datetime.fromisoformat(current_time)
        candidates = [
            (abs((datetime.fromisoformat(stamp) - current).total_seconds()), value)
            for stamp, value in zip(times, probabilities)
            if isinstance(stamp, str) and _finite(value) is not None
        ]
        return _number(min(candidates, key=lambda item: item[0])[1], suffix="%") if candidates else "—"
    except (TypeError, ValueError):
        return "—"


def normalize_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert Open-Meteo's response into a compact, UI-stable snapshot."""
    current = payload.get("current")
    daily = payload.get("daily")
    hourly = payload.get("hourly", {})
    if not isinstance(current, dict) or not isinstance(daily, dict):
        raise ValueError("Risposta meteo incompleta")
    if not isinstance(hourly, dict) or _finite(current.get("temperature_2m")) is None or _finite(current.get("weather_code")) is None:
        raise ValueError("Condizioni meteo non valide")
    try:
        datetime.fromisoformat(current["time"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Data meteo non valida") from None

    code = current.get("weather_code")
    direction = _wind_direction(current.get("wind_direction_10m"))
    current_time = current.get("time", "")
    dates = daily.get("time", [])
    codes = daily.get("weather_code", [])
    highs = daily.get("temperature_2m_max", [])
    lows = daily.get("temperature_2m_min", [])
    rain_chances = daily.get("precipitation_probability_max", [])
    forecast = []
    if all(isinstance(values, list) for values in (dates, codes, highs, lows)):
        for index, date_text in enumerate(dates[:3]):
            try:
                day = datetime.fromisoformat(date_text).weekday()
                if any(_finite(value) is None for value in (highs[index], lows[index], codes[index])):
                    raise ValueError("Previsioni giornaliere non valide")
                forecast.append({
                    "day": "OGGI" if index == 0 else WEEKDAYS_IT[day],
                    "date": date_text,
                    "highValue": _finite(highs[index]),
                    "lowValue": _finite(lows[index]),
                    "rainProbabilityValue": _finite(rain_chances[index]) if index < len(rain_chances) else None,
                    "description": _weather_description(codes[index]),
                    "code": int(codes[index]),
                    "high": _number(highs[index], 0, "°"),
                    "low": _number(lows[index], 0, "°"),
                    "rain": _number(rain_chances[index], suffix="%") if index < len(rain_chances) else "—",
                })
            except (IndexError, TypeError, ValueError):
                continue

    if len(forecast) != 3:
        raise ValueError("Previsioni giornaliere incomplete: attesi tre giorni")

    return {
        "location": "ANGRI · SALERNO",
        "numeric": {"temperature":_finite(current.get("temperature_2m")),
                    "feelsLike":_finite(current.get("apparent_temperature")),
                    "humidity":_finite(current.get("relative_humidity_2m")),
                    "precipitation":_finite(current.get("precipitation")),
                    "rainProbability":_rain_value(hourly,current_time),
                    "windSpeed":_finite(current.get("wind_speed_10m")),
                    "windDirection":_finite(current.get("wind_direction_10m")),
                    "gusts":_finite(current.get("wind_gusts_10m"))},
        "temperature": _number(current.get("temperature_2m"), 0, "°"),
        "description": _weather_description(code),
        "code": int(code) if isinstance(code, (int, float)) else -1,
        "feels_like": _number(current.get("apparent_temperature"), 0, "°C"),
        "humidity": _number(current.get("relative_humidity_2m"), suffix="%"),
        "precipitation": _number(current.get("precipitation"), 1, " mm"),
        "rain_probability": _nearest_precipitation_probability(hourly, current_time),
        "wind": f"{_number(current.get('wind_speed_10m'), 0, ' km/h')} · {direction}",
        "gusts": _number(current.get("wind_gusts_10m"), 0, " km/h"),
        "forecast": forecast,
        "weather_time": current_time,
    }


def fetch_weather() -> dict[str, Any]:
    parameters = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": ",".join((
            "temperature_2m", "relative_humidity_2m", "apparent_temperature",
            "precipitation", "weather_code", "wind_speed_10m",
            "wind_direction_10m", "wind_gusts_10m",
        )),
        "hourly": "precipitation_probability",
        "daily": ",".join((
            "weather_code", "temperature_2m_max", "temperature_2m_min",
            "precipitation_probability_max",
        )),
        "timezone": TIMEZONE,
        "forecast_days": 3,
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }
    request = Request(
        f"{API_URL}?{urlencode(parameters)}",
        headers={"User-Agent": "SmartPC-Dashboard (Open-Meteo client)"},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(f"Open-Meteo HTTP {error.code}") from error
    except (URLError, TimeoutError, OSError) as error:
        raise RuntimeError("Open-Meteo non raggiungibile") from error
    if not isinstance(payload, dict) or payload.get("error"):
        reason = payload.get("reason", "risposta non valida") if isinstance(payload, dict) else "risposta non valida"
        raise RuntimeError(f"Open-Meteo: {reason}")
    return normalize_response(payload)


class _WorkerSignals(QObject):
    finished = Signal(object, object)


class _WeatherWorker(QRunnable):
    def __init__(self, cache_path: Path) -> None:
        super().__init__()
        self.signals = _WorkerSignals()
        self.cache_path = cache_path
        self.cancelled = Event()
        self.fetched_at = 0.0
        self.cache_error = ""

    @Slot()
    def run(self) -> None:
        try:
            snapshot, error = fetch_weather(), None
            self.fetched_at = time.time()
            if self.cancelled.is_set():
                return
            try:
                save_weather_cache(self.cache_path, snapshot, self.fetched_at)
            except (OSError, ValueError):
                self.cache_error = "Dati acquisiti · cache non salvata; ripristino offline non garantito"
        except Exception as exc:  # The worker reports errors to the UI service.
            snapshot, error = None, str(exc)
        try:
            if not self.cancelled.is_set():
                self.signals.finished.emit(snapshot, error)
        except RuntimeError:
            # The Qt receiver can disappear while a network request finishes at shutdown.
            pass


def save_weather_cache(path: Path, snapshot: dict, fetched_at: float) -> None:
    """Persist a complete snapshot atomically in the acquisition worker."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="weather-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump({"snapshot": snapshot, "fetched_at": fetched_at}, stream, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def valid_cached_snapshot(snapshot: object) -> bool:
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("temperature"), str):
        return False
    forecast = snapshot.get("forecast")
    if not isinstance(forecast, list) or len(forecast) != 3:
        return False
    try:
        datetime.fromisoformat(snapshot["weather_time"])
        for day in forecast:
            if not isinstance(day, dict) or _finite(day.get("code")) is None:
                return False
            datetime.fromisoformat(day["date"])
            if not all(isinstance(day.get(key), str) for key in ("day", "high", "low", "description")):
                return False
    except (KeyError, TypeError, ValueError):
        return False
    return True


class WeatherService(QObject):
    changed = Signal()
    refreshFinished = Signal(bool, str)

    def __init__(self, auto_refresh: bool = True) -> None:
        super().__init__()
        self._snapshot: dict[str, Any] = {}
        self._fetched_at = 0.0
        self._from_cache = False
        self._in_flight = False
        self._last_error = ""
        self._cache_error = ""
        self._closed = False
        self._worker: _WeatherWorker | None = None
        self._cache_path = self._get_cache_path()
        self._load_cache()

        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_INTERVAL_MS)
        self._timer.timeout.connect(lambda: self.refresh())
        self._age_timer = QTimer(self)
        self._age_timer.setInterval(60_000)
        self._age_timer.timeout.connect(self._age_changed)
        self._age_timer.start()
        self._published_status = self.moduleState["status"]
        if auto_refresh:
            self._timer.start()
            QTimer.singleShot(0, lambda: self.refresh())

    @staticmethod
    def _get_cache_path() -> Path:
        location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
        base = Path(location) if location else Path.home() / ".cache" / "smartpc"
        return base / "weather.json"

    def _load_cache(self) -> None:
        try:
            cached = json.loads(self._cache_path.read_text(encoding="utf-8"))
            snapshot = cached.get("snapshot")
            fetched_at = cached.get("fetched_at")
            if (valid_cached_snapshot(snapshot) and _finite(fetched_at) is not None
                    and 0 < fetched_at <= time.time() + 300):
                self._snapshot = snapshot
                self._fetched_at = fetched_at
                self._from_cache = True
        except (OSError, ValueError, AttributeError):
            pass

    def _age_changed(self) -> None:
        status = self.moduleState["status"]
        if not self._closed and status != self._published_status:
            self._published_status = status
            self.changed.emit()

    @Property("QVariantMap", notify=changed)
    def moduleState(self) -> dict[str, Any]:
        """Versioned provider state; other modules can use the same envelope."""
        if self._last_error:
            status = "offline" if self._snapshot else "error"
        elif self._in_flight:
            status = "updating"
        elif self._snapshot and (self._from_cache or time.time() - self._fetched_at > MAX_AGE_SECONDS or self._fetched_at > time.time() + 300):
            status = "stale"
        elif self._snapshot:
            status = "active"
        else:
            status = "unavailable"
        return module_state(
            status=status, source="Open-Meteo", updated_at=self._fetched_at,
            data=dict(self._snapshot, cacheError=self._cache_error) if self._snapshot else {},
            error=self._last_error or self._cache_error,
        )

    @Slot(result=bool)
    def refresh(self) -> bool:
        if self._closed or self._in_flight:
            return False
        self._in_flight = True
        self._last_error = ""
        worker = _WeatherWorker(self._cache_path)
        worker.signals.finished.connect(self._on_finished)
        self._worker = worker
        QThreadPool.globalInstance().start(worker)
        self.changed.emit()
        return True

    @Slot(object, object)
    def _on_finished(self, snapshot: object, error: object) -> None:
        if self._closed:
            return
        worker = self._worker
        self._in_flight = False
        self._worker = None
        if isinstance(snapshot, dict):
            self._snapshot = snapshot
            self._fetched_at = worker.fetched_at if worker else time.time()
            self._from_cache = False
            self._last_error = ""
            self._cache_error = worker.cache_error if worker else ""
        else:
            self._last_error = str(error or "Errore meteo")
        self.changed.emit()
        self._published_status = self.moduleState["status"]
        self.refreshFinished.emit(isinstance(snapshot, dict) and not self._cache_error,
                                  self._last_error or self._cache_error)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._timer.stop()
        self._age_timer.stop()
        if self._worker:
            self._worker.cancelled.set()
            self._worker.signals.finished.disconnect(self._on_finished)
        self._in_flight = False
