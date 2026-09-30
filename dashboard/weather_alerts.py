"""Official DPC bulletin adapter for the Angri alert zone.

The national bulletin is a daily assessment, not a real-time emergency feed.
Only explicit, known alert colours are promoted to notifications.
"""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from event_core import validate_event


BULLETIN_PAGE = "https://mappe.protezionecivile.gov.it/it/mappe-rischi/bollettino-di-criticita/"
RAW_FILES = "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/master/files/"
ROME = ZoneInfo("Europe/Rome")
COLOURS = {"GIALLA": (2, "gialla"), "ARANCIONE": (3, "arancione"), "ROSSA": (3, "rossa")}
RISKS = (("Per rischio idraulico", "rischio idraulico"),
         ("Per rischio temporali", "temporali"),
         ("Per rischio idrogeologico", "rischio idrogeologico"))


def _read(url: str, maximum: int, timeout: int = 25) -> bytes:
    request = Request(url, headers={"User-Agent": "SmartPC/0.5 (+local dashboard)"})
    with urlopen(request, timeout=timeout) as response:
        data = response.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("Bollettino troppo grande")
    return data


def _level(text: Any) -> tuple[int, str]:
    if not isinstance(text, str):
        raise ValueError("Livello allerta assente")
    match = re.search(r"ALLERTA\s+(GIALLA|ARANCIONE|ROSSA)\b", text, re.IGNORECASE)
    if match:
        return COLOURS[match.group(1).upper()]
    if "NESSUNA ALLERTA" in text.upper():
        return 0, ""
    raise ValueError(f"Livello allerta sconosciuto: {text[:80]}")


def normalize_bulletin(wrapper: dict[str, Any], maps: dict[str, dict[str, Any]],
                       bulletin_key: str, now: float) -> list[dict[str, Any]]:
    issue_day = datetime.strptime(bulletin_key[:8], "%Y%m%d").date()
    issued_at = datetime.fromisoformat(wrapper["date"].replace("Z", "+00:00")).timestamp()
    local_today = datetime.fromtimestamp(now, ROME).date()
    if issue_day < local_today - timedelta(days=1) or issue_day > local_today or issued_at > now + 600:
        raise ValueError("Bollettino non attuale")
    result: list[dict[str, Any]] = []
    for offset, day_name in ((0, "today"), (1, "tomorrow")):
        day = issue_day + timedelta(days=offset)
        starts_at = datetime.combine(day, time.min, ROME).timestamp()
        expires_at = datetime.combine(day + timedelta(days=1), time.min, ROME).timestamp()
        if expires_at <= now:
            continue
        topology = maps[day_name]
        matches = [geometry["properties"] for item in topology["objects"].values()
                   for geometry in item["geometries"]
                   if "Angri" in geometry.get("properties", {}).get("Comuni", [])]
        if len(matches) != 1:
            raise ValueError("Zona allerta di Angri non univoca")
        properties = matches[0]
        highest = _level(properties.get("Rappresentata nella mappa"))
        risks = [label for key, label in RISKS if _level(properties.get(key))[0] > 0]
        if highest[0] == 0:
            if risks:
                raise ValueError("Livelli di rischio incoerenti")
            continue
        if not risks:
            raise ValueError("Allerta senza rischio specificato")
        title = f"Allerta meteo {highest[1]}"
        result.append({
            "version": 1,
            "id": f"dpc:Angri:{day.isoformat()}",
            "source": "weather-alert",
            "sourceLabel": "Protezione Civile",
            "category": "meteo",
            "priority": highest[0],
            "notificationRank": {"gialla": 2, "arancione": 3, "rossa": 4}[highest[1]],
            "title": title,
            "detail": f"Angri · {', '.join(risks)} · {day.strftime('%d/%m')}",
            "issuedAt": issued_at,
            "startsAt": starts_at,
            "expiresAt": expires_at,
            "revision": bulletin_key,
            "sourceUrl": BULLETIN_PAGE,
            "showOnHome": True,
        })
    return result


def default_bulletin_cache_path() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        p = Path(xdg)
        return p / "dpc-bulletin.json" if p.name == "smartpc-dashboard" else p / "smartpc-dashboard/dpc-bulletin.json"
    return Path.home() / ".cache/smartpc-dashboard/dpc-bulletin.json"


@dataclass(frozen=True)
class BulletinSnapshot:
    events: list[dict[str, Any]]
    key: str
    fetched_at: float
    checked_at: float
    from_cache: bool
    unchanged: bool = False
    cache_error: str = ""


class BulletinProvider:
    """Keep the last validated Angri bulletin, separate from delivery state."""

    def __init__(self, cache_path: Path | None) -> None:
        self.cache_path = cache_path
        self._payload: dict[str, Any] | None = None

    @staticmethod
    def _snapshot(payload: dict[str, Any], now: float, *, from_cache: bool,
                  unchanged: bool = False) -> BulletinSnapshot:
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise ValueError("Cache bollettino non valida")
        key = payload["bulletinKey"]
        if not isinstance(key, str) or not re.fullmatch(r"\d{8}_\d{4}", key):
            raise ValueError("Chiave bollettino non valida")
        for field in ("fetchedAt", "checkedAt"):
            value = payload[field]
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= now + 600:
                raise ValueError("Ora cache bollettino non valida")
        events = normalize_bulletin(payload["wrapper"], payload["maps"], key, now)
        return BulletinSnapshot([validate_event(event) for event in events], key,
                                payload["fetchedAt"], payload["checkedAt"], from_cache, unchanged)

    def load(self, now: float) -> BulletinSnapshot | None:
        try:
            payload = self._payload
            if payload is None:
                if self.cache_path is None:
                    return None
                with self.cache_path.open("rb") as stream:
                    content = stream.read(100_001)
                if len(content) > 100_000:
                    raise ValueError("Cache bollettino troppo grande")
                payload = json.loads(content)
            snapshot = self._snapshot(payload, now, from_cache=True)
            self._payload = payload
            return snapshot
        except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError):
            return None

    def _save(self, payload: dict[str, Any]) -> str:
        if self.cache_path is None:
            return ""
        temporary = None
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix="dpc-", suffix=".json", dir=self.cache_path.parent)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.cache_path)
            directory = os.open(self.cache_path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            return ""
        except OSError as exc:
            return str(exc)
        finally:
            if temporary is not None:
                try:
                    Path(temporary).unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _angri_map(topology: dict[str, Any]) -> dict[str, Any]:
        matches = [geometry["properties"] for item in topology["objects"].values()
                   for geometry in item["geometries"]
                   if "Angri" in geometry.get("properties", {}).get("Comuni", [])]
        if len(matches) != 1:
            raise ValueError("Zona allerta di Angri non univoca")
        properties = matches[0]
        selected = {key: properties[key] for key in
                    ("Rappresentata nella mappa", *(key for key, _ in RISKS))}
        if isinstance(properties.get("Nome zona"), str):
            selected["Nome zona"] = properties["Nome zona"]
        selected["Comuni"] = ["Angri"]
        return {"objects": {"Angri": {"geometries": [{"properties": selected}]}}}

    def refresh(self, now: float) -> BulletinSnapshot:
        cached = self.load(now)
        page = _read(BULLETIN_PAGE, 2_000_000).decode("utf-8", errors="replace")
        keys = re.findall(r"files/xml/(\d{8}_\d{4})\.zip", page)
        if not keys:
            raise ValueError("Bollettino ufficiale non individuato")
        key = max(keys)
        if cached is not None and key < cached.key:
            raise ValueError("Bollettino precedente alla cache")
        unchanged = cached is not None and key == cached.key
        if unchanged:
            payload = dict(self._payload, checkedAt=now)
        else:
            wrapper = json.loads(_read(f"{RAW_FILES}{key}.json", 100_000))
            if not isinstance(wrapper, dict) or not isinstance(wrapper.get("date"), str):
                raise ValueError("Metadati bollettino non validi")
            maps = {}
            for day_name in ("today", "tomorrow"):
                link = wrapper.get(day_name, {}).get("topo_json")
                if not isinstance(link, str) or not link.startswith(RAW_FILES + "topojson/"):
                    raise ValueError("Mappa bollettino non valida")
                maps[day_name] = self._angri_map(json.loads(_read(link, 6_000_000)))
            payload = {"version": 1, "bulletinKey": key, "wrapper": {"date": wrapper["date"]},
                       "maps": maps, "fetchedAt": now, "checkedAt": now}
        snapshot = self._snapshot(payload, now, from_cache=False, unchanged=unchanged)
        # Only validated data may replace the previous file or in-memory snapshot.
        self._payload = payload
        cache_error = self._save(payload)
        return BulletinSnapshot(snapshot.events, snapshot.key, snapshot.fetched_at,
                                snapshot.checked_at, False, unchanged, cache_error)


def fetch_alerts(now: float) -> list[dict[str, Any]]:
    return BulletinProvider(default_bulletin_cache_path()).refresh(now).events
