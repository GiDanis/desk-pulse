"""Casa persistence, budget and batch normalization. No Qt and no controls."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import fcntl
import os
from functools import wraps
import math
from pathlib import Path
import time

from tuya_core import (
    CloudClient,
    TuyaError,
    ID,
    CODE,
    MAX_DEVICES,
    MAX_RESPONSE,
    atomic_json,
    normalize_device,
    normalize_status,
    _finite,
    _text,
)

BASE_INTERVAL = 300
FAST_INTERVAL = 60
MANUAL_LIMIT = 100  # Lifetime cap until an effective console allocation is supplied.
METRIC_LABELS = {
    "va_temperature": "Temperatura",
    "temp_current": "Temperatura",
    "va_humidity": "Umidità",
    "humidity_value": "Umidità",
    "battery_percentage": "Batteria",
    "switch_1": "Interruttore",
    "switch_led": "Luce",
    "switch": "Interruttore",
    "pir": "Movimento riportato",
    "cur_power": "Potenza",
    "cur_current": "Corrente",
    "cur_voltage": "Tensione",
    "add_ele": "Energia riportata",
    "work_mode": "Modalità",
}


def read_json(path):
    if path.stat().st_size > MAX_RESPONSE:
        raise ValueError("size")
    return json.loads(
        path.read_text(),
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("number")),
    )


def policy(path: Path) -> dict:
    """No nominal free allowance is assumed. Policy contains no secrets."""
    try:
        raw = read_json(path)
        keys = (
            "periodStart",
            "periodEnd",
            "apiAllowance",
            "consumedBeforeStart",
            "serviceExpiresAt",
        )
        if not isinstance(raw, dict) or any(not _finite(raw.get(k)) for k in keys):
            return {}
        start, end = raw["periodStart"], raw["periodEnd"]
        if (
            not 0 < start < end
            or end - start > 40 * 86400
            or type(raw["apiAllowance"]) is not int
            or not 1 <= raw["apiAllowance"] <= 10**8
            or type(raw["consumedBeforeStart"]) is not int
            or not 0 <= raw["consumedBeforeStart"] <= raw["apiAllowance"]
            or raw["serviceExpiresAt"] <= start
        ):
            return {}
        return {k: raw[k] for k in keys}
    except (OSError, ValueError, TypeError):
        return {}


def serialized_budget(operation):
    """Serialize ledger writers, including an explicit probe in another process."""

    @wraps(operation)
    def run(self, *args, **kwargs):
        if not self.valid:
            raise TuyaError(
                "budget", "Contatore Casa non valido: aggiornamenti sospesi."
            )
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            descriptor = os.open(
                self.path.with_suffix(".lock"),
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
                0o600,
            )
            with os.fdopen(descriptor, "a") as guard:
                fcntl.flock(guard, fcntl.LOCK_EX)
                if self.path.exists():
                    latest = RequestBudget(
                        self.path, self.scope, self.allocation, self.clock
                    )
                    if not latest.valid:
                        self.valid = False
                        raise TuyaError(
                            "budget",
                            "Contatore Casa non valido: aggiornamenti sospesi.",
                        )
                    self.data = latest.data
                return operation(self, *args, **kwargs)
        except OSError:
            self.valid = False
            raise TuyaError(
                "budget", "Contatore non scrivibile: nessuna nuova chiamata inviata."
            ) from None

    return run


class RequestBudget:
    """Durable pre-send accounting; corruption/clock rollback never grants calls."""

    def __init__(self, path: Path, scope: str, allocation=None, clock=time.time):
        self.path, self.scope, self.clock = path, scope, clock
        self.allocation = allocation or {}
        self.valid = True
        self.data = {
            "version": 1,
            "scope": scope,
            "periodStart": 0,
            "periodEnd": 0,
            "requests": 0,
            "highWater": 0,
            "boostDay": "",
            "boostSeconds": 0,
        }
        if path.exists():
            try:
                raw = read_json(path)
                if (
                    not isinstance(raw, dict)
                    or raw.get("version") != 1
                    or raw.get("scope") != scope
                    or any(
                        not _finite(raw.get(k)) or raw[k] < 0
                        for k in (
                            "periodStart",
                            "periodEnd",
                            "requests",
                            "highWater",
                            "boostSeconds",
                        )
                    )
                    or type(raw["requests"]) is not int
                    or not isinstance(raw.get("boostDay"), str)
                ):
                    raise ValueError
                self.data = {k: raw[k] for k in self.data}
            except (OSError, ValueError, KeyError, TypeError):
                self.valid = False

    def _period(self, now):
        if not self.valid:
            raise TuyaError(
                "budget",
                "Contatore Casa non valido: verificare il consumo prima di ripristinarlo.",
            )
        if not _finite(now) or now <= 0 or now < self.data["highWater"] - 5:
            raise TuyaError("budget", "Ora arretrata: aggiornamenti Casa sospesi.")
        p = self.allocation
        if p:
            if not p["periodStart"] <= now < min(p["periodEnd"], p["serviceExpiresAt"]):
                raise TuyaError(
                    "budget",
                    "Periodo quota o servizio scaduto: aggiornare la configurazione Casa.",
                )
            if self.data["periodStart"] != p["periodStart"]:
                if self.data["periodEnd"] and p["periodStart"] < self.data["periodEnd"]:
                    raise TuyaError(
                        "budget",
                        "Il periodo quota non può essere azzerato anticipatamente.",
                    )
                # Switching from manual mode retains its already counted calls.
                requests = self.data["requests"] if not self.data["periodStart"] else 0
                self.data.update(
                    periodStart=p["periodStart"],
                    periodEnd=p["periodEnd"],
                    requests=requests,
                )
        elif self.data["periodStart"]:
            raise TuyaError(
                "budget", "Quota configurata non più leggibile: aggiornamenti sospesi."
            )

    def remaining(self):
        p = self.allocation
        ceiling = (
            max(0, int(p["apiAllowance"] * 0.8) - p["consumedBeforeStart"])
            if p
            else MANUAL_LIMIT
        )
        requests = self.data["requests"]
        if (
            p
            and self.data["periodStart"]
            and p["periodStart"] >= self.data["periodEnd"]
        ):
            requests = 0
        return max(0, ceiling - requests) if self.valid else 0

    @serialized_budget
    def charge(self):
        now = self.clock()
        self._period(now)
        if self.remaining() < 1:
            raise TuyaError(
                "budget", "Budget Casa esaurito: nessuna nuova chiamata inviata."
            )
        self.data.update(
            requests=self.data["requests"] + 1,
            highWater=max(now, self.data["highWater"]),
        )
        try:
            atomic_json(self.path, self.data)
        except OSError:
            self.valid = False
            raise TuyaError(
                "budget", "Contatore non scrivibile: nessuna nuova chiamata inviata."
            ) from None

    @serialized_budget
    def boost(self, seconds: float, page_count: int):
        now = self.clock()
        self._period(now)
        if not self.allocation or not _finite(seconds) or seconds < 0:
            return False
        day = datetime.fromtimestamp(now, timezone.utc).date().isoformat()
        if day != self.data["boostDay"]:
            if day < self.data["boostDay"]:
                return False
            self.data.update(boostDay=day, boostSeconds=0)
        self.data["boostSeconds"] = min(86400, self.data["boostSeconds"] + seconds)
        self.data["highWater"] = max(now, self.data["highWater"])
        try:
            atomic_json(self.path, self.data)
        except OSError:
            self.valid = False
            return False
        days_left = max(
            0,
            (
                min(self.allocation["periodEnd"], self.allocation["serviceExpiresAt"])
                - now
            )
            / 86400,
        )
        # Reserve 480 polls/day plus auth, schema reads and retries. All pages count.
        projected = math.ceil(days_left * (480 * max(1, page_count) + 24))
        return self.data["boostSeconds"] < 7200 and self.remaining() >= projected

    def automatic_available(self):
        now, p = self.clock(), self.allocation
        return bool(
            self.valid
            and p
            and _finite(now)
            and now >= self.data["highWater"] - 5
            and p["periodStart"] <= now < min(p["periodEnd"], p["serviceExpiresAt"])
            and (
                self.data["periodStart"] == p["periodStart"]
                or not self.data["periodEnd"]
                or p["periodStart"] >= self.data["periodEnd"]
            )
            and self.remaining() > 0
        )

    def can_boost(self, page_count):
        if not self.automatic_available():
            return False
        now = self.clock()
        day = datetime.fromtimestamp(now, timezone.utc).date().isoformat()
        used = self.data["boostSeconds"] if day == self.data["boostDay"] else 0
        days = max(
            0,
            (
                min(self.allocation["periodEnd"], self.allocation["serviceExpiresAt"])
                - now
            )
            / 86400,
        )
        return (
            used < 7200
            and day >= self.data["boostDay"]
            and self.remaining() >= math.ceil(days * (480 * max(1, page_count) + 24))
        )


def clean_specification(raw: dict) -> dict:
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("status"), list)
        or len(raw["status"]) > 128
    ):
        raise TuyaError("invalid", "Specifiche Casa non valide.")
    result, seen = [], set()
    for row in raw["status"]:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("code"), str)
            or not CODE.fullmatch(row["code"])
            or row["code"] in seen
        ):
            raise TuyaError("invalid", "Codici specifiche Casa non validi.")
        seen.add(row["code"])
        values = row.get("values", "{}")
        try:
            values = json.loads(values) if isinstance(values, str) else values
            if not isinstance(values, dict):
                raise ValueError
        except (ValueError, TypeError):
            values = {}
        selected = {}
        for key in ("scale", "min", "max"):
            if type(values.get(key)) is int and abs(values[key]) <= 10**15:
                selected[key] = values[key]
        if isinstance(values.get("unit"), str):
            selected["unit"] = _text(values["unit"], 24)
        if isinstance(values.get("range"), list) and len(values["range"]) <= 128:
            selected["range"] = [
                _text(v, 120) for v in values["range"] if isinstance(v, str)
            ]
        result.append(
            {
                "code": row["code"],
                "type": _text(row.get("type"), 24),
                "values": selected,
            }
        )
    return {"status": result}


def empty_snapshot(scope):
    return {
        "version": 1,
        "scope": scope,
        "checkedAt": 0,
        "devices": [],
        "specifications": {},
        "favourites": [],
        "seeded": False,
        "pollingRequested": True,
    }


def clean_snapshot(raw, scope):
    """Rebuild an allowlisted schema on disk reads as well as network writes."""
    if (
        not isinstance(raw, dict)
        or raw.get("version") != 1
        or raw.get("scope") != scope
        or not _finite(raw.get("checkedAt"))
        or raw["checkedAt"] < 0
        or not isinstance(raw.get("devices"), list)
        or len(raw["devices"]) > MAX_DEVICES
        or not isinstance(raw.get("specifications"), dict)
    ):
        raise ValueError("snapshot")
    result = empty_snapshot(scope)
    result.update(
        checkedAt=raw["checkedAt"],
        seeded=raw.get("seeded") is True,
        pollingRequested=raw.get("pollingRequested", True) is True,
    )
    seen = set()
    for row in raw["devices"]:
        if not isinstance(row, dict):
            raise ValueError("device")
        device = normalize_device(
            {
                **row,
                "product_id": row.get("productId"),
                "gateway_id": row.get("gatewayId"),
                "sub": row.get("subDevice"),
            }
        )
        if (
            device["id"] in seen
            or type(row.get("missingCount", 0)) is not int
            or not 0 <= row.get("missingCount", 0) <= 2
        ):
            raise ValueError("identity")
        seen.add(device["id"])
        device.update(
            present=row.get("present") is True,
            missingCount=row.get("missingCount", 0),
            states=[],
        )
        states = row.get("states", [])
        if not isinstance(states, list) or len(states) > 128:
            raise ValueError("states")
        codes = set()
        for metric in states:
            if (
                not isinstance(metric, dict)
                or not isinstance(metric.get("code"), str)
                or not CODE.fullmatch(metric["code"])
                or metric["code"] in codes
                or not _finite(metric.get("checkedAt"))
                or metric["checkedAt"] < 0
                or metric.get("quality") not in ("reported", "unverified")
            ):
                raise ValueError("metric")
            codes.add(metric["code"])
            value = metric.get("value")
            if not (
                value is None
                or type(value) is bool
                or _finite(value)
                or isinstance(value, str)
            ):
                raise ValueError("value")
            if metric["quality"] == "unverified":
                value = None
            device["states"].append(
                {
                    "code": metric["code"],
                    "type": _text(metric.get("type"), 24),
                    "value": _text(value, 120) if isinstance(value, str) else value,
                    "unit": _text(metric.get("unit"), 24),
                    "quality": metric["quality"],
                    "checkedAt": metric["checkedAt"],
                    "stale": metric.get("stale") is True,
                }
            )
        result["devices"].append(device)
    favourites = raw.get("favourites", [])
    if (
        not isinstance(favourites, list)
        or len(favourites) > 4
        or any(
            not isinstance(i, str) or not ID.fullmatch(i) or i not in seen
            for i in favourites
        )
        or len(set(favourites)) != len(favourites)
    ):
        raise ValueError("favourites")
    result["favourites"] = favourites[:]
    for identity, entry in raw["specifications"].items():
        if identity not in seen:
            continue
        if (
            not isinstance(entry, dict)
            or not _finite(entry.get("checkedAt"))
            or entry["checkedAt"] < 0
        ):
            raise ValueError("specification")
        observed = entry.get("observedCodes", [])
        if (
            not isinstance(observed, list)
            or len(observed) > 128
            or any(
                not isinstance(code, str) or not CODE.fullmatch(code)
                for code in observed
            )
        ):
            raise ValueError("observedCodes")
        result["specifications"][identity] = {
            "productId": _text(entry.get("productId")),
            "model": _text(entry.get("model")),
            "checkedAt": entry["checkedAt"],
            "observedCodes": sorted(set(observed)),
            **clean_specification(entry),
        }
    return result


def load_snapshot(path, scope):
    try:
        return clean_snapshot(read_json(path), scope)
    except (OSError, ValueError, TypeError, KeyError, TuyaError):
        return empty_snapshot(scope)


def acquire(client: CloudClient, previous: dict, cancelled=lambda: False):
    """One complete cloud scan. Specifications only for selected devices."""
    devices = client.smart_inventory()
    if cancelled():
        raise TuyaError("cancelled", "Acquisizione Casa interrotta.")
    now = client.clock()
    if not _finite(now) or now <= 0:
        raise TuyaError("invalid", "Ora Casa non valida.")
    result = empty_snapshot(client.scope)
    result.update(
        checkedAt=now,
        seeded=previous["seeded"],
        favourites=previous["favourites"][:],
        pollingRequested=previous.get("pollingRequested", True),
    )
    old = {d["id"]: d for d in previous["devices"]}
    # Initial candidates are editable defaults, chosen by verified capability.
    if not result["seeded"]:
        for category in ("wsdcg", "cz", "dj", "pir"):
            row = next(
                (
                    d
                    for d in devices
                    if d["category"] == category and d["reportedStates"]
                ),
                None,
            )
            if row:
                result["favourites"].append(row["id"])
        result["seeded"] = True
    for device in devices:
        identity = device["id"]
        reported = device.pop("reportedStates")
        entry = previous["specifications"].get(identity)
        codes = {r["code"] for r in reported}
        changed = entry is None or (entry["productId"], entry["model"]) != (
            device["productId"],
            device["model"],
        )
        need = (
            changed
            or not codes <= set(entry.get("observedCodes", []))
            or now - entry["checkedAt"] >= 86400
        )
        if identity in result["favourites"] and need:
            if cancelled():
                raise TuyaError("cancelled", "Acquisizione Casa interrotta.")
            entry = {
                **clean_specification(
                    client._get("/v1.2/iot-03/devices/" + identity + "/specification")
                ),
                "productId": device["productId"],
                "model": device["model"],
                "checkedAt": now,
                "observedCodes": sorted(codes),
            }
        if entry and not changed:
            result["specifications"][identity] = entry
        elif entry and identity in result["favourites"]:
            result["specifications"][identity] = entry
        else:
            entry = {"status": []}
        states = [
            {**r, "checkedAt": now, "stale": False}
            for r in normalize_status(reported, entry)
        ]
        # Validate integer bounds in addition to type/scale; outliers stay unknown.
        specs = {r["code"]: r for r in entry["status"]}
        for metric, raw in zip(states, reported):
            v = specs.get(metric["code"], {}).get("values", {})
            if (
                metric["type"] in ("integer", "value")
                and _finite(raw["value"])
                and (
                    _finite(v.get("min"))
                    and raw["value"] < v["min"]
                    or _finite(v.get("max"))
                    and raw["value"] > v["max"]
                )
            ):
                metric.update(value=None, quality="unverified")
        new_codes = {s["code"] for s in states}
        if not changed:
            states += [
                {**s, "stale": True}
                for s in old.get(identity, {}).get("states", [])
                if s["code"] not in new_codes
            ]
        device.update(states=states, present=True, missingCount=0)
        result["devices"].append(device)
    present = {d["id"] for d in devices}
    for identity, device in old.items():
        if identity not in present:
            missing = min(2, device["missingCount"] + 1)
            if missing < 2 or identity in result["favourites"]:
                result["devices"].append(
                    {
                        **device,
                        "present": False,
                        "missingCount": missing,
                        "states": [{**r, "stale": True} for r in device["states"]],
                    }
                )
    return clean_snapshot(result, client.scope)


def metric_text(metric):
    value = metric["value"]
    if value is None or metric["quality"] != "reported":
        return "Non disponibile"
    if type(value) is bool:
        return "Acceso" if value else "Spento"
    if metric["code"] == "pir":
        return {"pir": "Movimento riportato", "none": "Nessun movimento riportato"}.get(
            value, "Evento non interpretato"
        )
    if _finite(value):
        value = f"{value:g}".replace(".", ",")
    return str(value) + (
        (" " + metric["unit"].replace("℃", "°C")) if metric["unit"] else ""
    )


def display_devices(snapshot, source_status):
    result = []
    fresh = source_status == "active"
    for d in snapshot["devices"]:
        availability = (
            "Non più disponibile"
            if d["missingCount"] >= 2
            else "Non trovato"
            if not d["present"]
            else "Offline"
            if d["online"] is False
            else "Online secondo Tuya"
            if d["online"] is True
            else "Disponibilità sconosciuta"
        )
        current = fresh and d["present"] and d["online"] is True
        metrics = [
            {
                **m,
                "label": METRIC_LABELS.get(m["code"], m["code"]),
                "displayText": metric_text(m),
                "previous": not current or m["stale"],
            }
            for m in d["states"]
            if m["code"] in METRIC_LABELS
        ]
        primary = next(
            (
                m
                for code in (
                    "va_temperature",
                    "temp_current",
                    "switch_led",
                    "switch_1",
                    "switch",
                    "pir",
                )
                for m in metrics
                if m["code"] == code
            ),
            None,
        )
        secondary = next(
            (m for m in metrics if m["code"] in ("va_humidity", "humidity_value")), None
        )
        result.append(
            {
                **d,
                "favourite": d["id"] in snapshot["favourites"],
                "availability": availability,
                "availabilityPrevious": not fresh,
                "previous": not current
                or any(m and m["previous"] for m in (primary, secondary)),
                "metrics": metrics,
                "primaryText": primary["displayText"]
                if primary
                else "Stato non disponibile",
                "secondaryText": ("Umidità " + secondary["displayText"])
                if secondary
                else "",
                "iconId": {
                    "wsdcg": "casa.temperature",
                    "cz": "casa.plug",
                    "dj": "casa.light",
                    "pir": "casa.motion",
                }.get(d["category"], "status.unavailable"),
            }
        )
    return result
