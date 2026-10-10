"""Validated F1/Jolpica and MotoGP/PulseLive adapters; no Qt or credentials."""

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import time
import urllib.parse
from racing_details import (
    enrich_f1,
    moto_circuit,
    open_results,
    decorate,
    OPENF1,
    preserve_driver_details,
    results_fresh,
)
from sport_core import (
    HTTPClient,
    ProviderError,
    mapping,
    items,
    number,
    text,
    timestamp,
    ROME,
)

JOLPICA = "https://api.jolpi.ca/ergast/f1/"
MOTO = "https://api.motogp.pulselive.com/motogp/v1/"
SESSION_NAMES = {
    "FP1": "Libere 1",
    "FP2": "Libere 2",
    "FP3": "Libere 3",
    "PR": "Practice",
    "Q1": "Qualifiche 1",
    "Q2": "Qualifiche 2",
    "Q": "Qualifiche",
    "SPR": "Sprint",
    "RAC": "Gara",
    "WUP": "Warm Up",
    "SQ": "Qualifiche Sprint",
}


def stamp(value):
    if not value:
        return "Orario da confermare"
    date = datetime.fromtimestamp(value, ROME)
    return ("Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom")[
        date.weekday()
    ] + date.strftime(" %d/%m · %H:%M")


def points(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        if result < 0 or result > 10000 or result != result or result == float("inf"):
            return None
        return result
    except (TypeError, ValueError):
        return None


def display(value):
    return f"{value:g}" if isinstance(value, (int, float)) else "—"


def session(
    identity,
    kind,
    start,
    *,
    end=None,
    state="scheduled",
    provider_id="",
    timing_id=None,
):
    return {
        "id": identity,
        "kind": kind,
        "name": SESSION_NAMES.get(kind, kind),
        "start": start,
        "end": end,
        "state": state,
        "providerId": provider_id,
        "timingId": timing_id,
        "results": [],
        "resultsAt": 0,
    }


def f1_table(raw, table, year):
    root = mapping(mapping(raw).get("MRData"))
    data = mapping(root.get(table))
    if root.get("series") != "f1" or str(data.get("season")) != str(year):
        raise ValueError("Stagione o competizione Jolpica errata")
    return data


def f1_calendar(raw, year):
    rows = items(f1_table(raw, "RaceTable", year).get("Races"))
    if not rows or len(rows) > 50:
        raise ValueError("Calendario F1 incompleto")
    events = []
    for race in rows:
        if str(race.get("season")) != str(year) or not number(race.get("round")):
            raise ValueError("Identità GP F1 non valida")
        identity = f'f1:{year}:{race["round"]}'

        def dt(block):
            return timestamp(
                str(block.get("date", "")) + "T" + str(block.get("time", ""))
            )  # no invented midnight

        start = dt(race)
        sessions = []
        for key, kind in [
            ("FirstPractice", "FP1"),
            ("SecondPractice", "FP2"),
            ("ThirdPractice", "FP3"),
            ("SprintQualifying", "SQ"),
            ("Qualifying", "Q"),
            ("Sprint", "SPR"),
        ]:
            if isinstance(race.get(key), dict):
                sessions.append(session(identity + ":" + kind, kind, dt(race[key])))
        sessions.append(session(identity + ":RAC", "RAC", start))
        circuit = mapping(race.get("Circuit"))
        events.append(
            {
                "id": identity,
                "round": text(race["round"]),
                "name": text(race.get("raceName")),
                "circuit": text(circuit.get("circuitName")),
                "circuitData": {
                    "country": text(mapping(circuit.get("Location")).get("country")),
                    "city": text(mapping(circuit.get("Location")).get("locality")),
                },
                "start": start,
                "end": start + 4 * 3600 if start else None,
                "dateLabel": text(race.get("date")),
                "status": "scheduled",
                "sessions": sorted(sessions, key=lambda s: s["start"] or float("inf")),
            }
        )
    return events


def f1_standings(raw, year, constructors=False):
    data = f1_table(raw, "StandingsTable", year)
    tables = items(data.get("StandingsLists"))
    if not tables:
        if isinstance(data.get("StandingsLists"), list):
            return [], ""
        raise ValueError("Classifica F1 incompleta")
    key = "ConstructorStandings" if constructors else "DriverStandings"
    result = []
    for row in items(tables[0].get(key)):
        person = mapping(row.get("Constructor" if constructors else "Driver"))
        name = (
            text(person.get("name"))
            if constructors
            else text(person.get("givenName")) + " " + text(person.get("familyName"))
        )
        teams = items(row.get("Constructors"))
        result.append(
            {
                "id": text(person.get("constructorId" if constructors else "driverId")),
                "position": number(row.get("position")),
                "name": name.strip(),
                "team": text(mapping(teams[0]).get("name")) if teams else "",
                "points": points(row.get("points")),
                "wins": number(row.get("wins")),
                "number": number(person.get("permanentNumber")),
            }
        )
    if len(result) > 60:
        raise ValueError("Classifica F1 vuota")
    return result, text(tables[0].get("round", data.get("round")))


def f1_result_rows(race, key):
    result = []
    for row in items(race.get(key)):
        driver = mapping(row.get("Driver"))
        value = (
            (row.get("Q3") or row.get("Q2") or row.get("Q1"))
            if key == "QualifyingResults"
            else mapping(row.get("Time")).get("time") or row.get("status")
        )
        result.append(
            {
                "id": text(driver.get("driverId")),
                "position": number(row.get("position")),
                "name": (
                    text(driver.get("givenName")) + " " + text(driver.get("familyName"))
                ).strip(),
                "team": text(mapping(row.get("Constructor")).get("name")),
                "value": text(value) or "—",
                "points": points(row.get("points")),
                "laps": number(row.get("laps")),
                "status": text(row.get("status")),
                **enrich_f1(row),
            }
        )
    return result


def apply_f1_results(snapshot, raw, kind, expected_round=None):
    rows = items(f1_table(raw, "RaceTable", snapshot["year"]).get("Races"))
    key = {"RAC": "Results", "Q": "QualifyingResults", "SPR": "SprintResults"}[kind]
    for race in rows:
        if str(race.get("season")) != str(snapshot["year"]) or (
            expected_round and str(race.get("round")) != str(expected_round)
        ):
            raise ValueError("Risultato di un altro GP F1")
        event = next(
            (e for e in snapshot["events"] if e["round"] == str(race.get("round"))),
            None,
        )
        if not event:
            raise ValueError("GP F1 assente dal calendario")
        target = next((s for s in event["sessions"] if s["kind"] == kind), None)
        if target:
            previous = target.get("results", [])
            target["results"] = f1_result_rows(race, key)
            preserve_driver_details(target["results"], previous)
            target["resultSource"] = "Jolpica"
            if target["results"]:
                target["state"] = "finished"
                target["resultsAt"] = snapshot["detailAt"]
                if kind == "RAC":
                    event["status"] = "finished"


def moto_calendar(raw, year):
    if not isinstance(raw, list):
        raise ValueError("Calendario MotoGP non valido")
    result = []
    for event in raw:
        if event.get("test"):
            continue
        if mapping(event.get("season")).get("year") != year:
            raise ValueError("Stagione MotoGP errata")
        identity = text(event.get("id"))
        if not identity:
            raise ValueError("Identità MotoGP mancante")
        # Date-only boundaries are for weekend selection, never displayed as race start.
        start = timestamp(text(event.get("date_start")) + "T00:00:00Z")
        end = timestamp(text(event.get("date_end")) + "T23:59:59Z")
        result.append(
            {
                "id": "motogp:" + str(year) + ":" + identity,
                "providerId": identity,
                "broadcastId": text(event.get("toad_api_uuid")),
                "name": text(event.get("sponsored_name") or event.get("name")),
                "shortName": text(event.get("short_name")),
                "circuit": text(mapping(event.get("circuit")).get("name")),
                "start": start,
                "end": end,
                "dateLabel": text(event.get("date_start"))
                + " / "
                + text(event.get("date_end")),
                "status": (
                    "finished" if event.get("status") == "FINISHED" else "scheduled"
                ),
                "sessions": [],
            }
        )
    result.sort(key=lambda e: e["start"] or float("inf"))
    for i, event in enumerate(result):
        event["round"] = str(i + 1)
    return result


def moto_standings(raw, year):
    if not isinstance(mapping(raw).get("classification"), list):
        raise ValueError("Classifica MotoGP non valida")
    result = []
    for row in items(mapping(raw).get("classification")):
        team = mapping(row.get("team"))
        season = mapping(team.get("season"))
        if season and season.get("year") != year:
            raise ValueError("Classifica MotoGP di un’altra stagione")
        rider = mapping(row.get("rider"))
        result.append(
            {
                "id": text(rider.get("id")),
                "position": number(row.get("position")),
                "name": text(rider.get("full_name")),
                "team": text(team.get("name")),
                "points": points(row.get("points")),
                "wins": number(row.get("race_wins")),
            }
        )
    if len(result) > 80:
        raise ValueError("Classifica MotoGP incompleta")
    return result


def moto_programme(raw, event, year):
    if (
        raw.get("id") != event["broadcastId"]
        or mapping(raw.get("season")).get("year") != year
    ):
        raise ValueError("Programma di un altro GP")
    moto_circuit(raw, event)
    sessions = []
    for row in items(raw.get("broadcasts")):
        if (
            mapping(row.get("category")).get("name") != "MotoGP"
            or row.get("type") != "SESSION"
        ):
            continue
        kind = text(row.get("shortname"))
        start, end = timestamp(row.get("date_start")), timestamp(row.get("date_end"))
        sessions.append(
            session(
                event["id"] + ":" + kind,
                kind,
                start,
                end=end if end and start and end > start else None,
                timing_id=row.get("timing_id"),
                state="finished" if row.get("status") == "FINISHED" else "scheduled",
            )
        )
        sessions[-1]["broadcastActive"] = row.get("is_live_timing") is True
        sessions[-1]["broadcastState"] = text(row.get("status"))
        old = next((s for s in event["sessions"] if s["id"] == sessions[-1]["id"]), {})
        for field in (
            "results",
            "resultsAt",
            "providerId",
            "conditions",
            "infoAt",
            "records",
            "resultSource",
        ):
            if field in old:
                sessions[-1][field] = deepcopy(old[field])
        if old.get("results") and old.get("state") == "finished":
            sessions[-1]["state"] = "finished"
    event["sessions"] = sorted(sessions, key=lambda s: s["start"] or float("inf"))
    race = next((s for s in sessions if s["kind"] == "RAC"), None)
    if race and race["start"]:
        event["end"] = race["end"] or race["start"] + 3 * 3600


def moto_sessions(raw, event, category):
    if not isinstance(raw, list):
        raise ValueError("Sessioni MotoGP non valide")
    result = []
    for row in raw:
        if (
            mapping(row.get("category")).get("id") != category
            or mapping(row.get("event")).get("id") != event["providerId"]
        ):
            raise ValueError("Sessione di altro evento/categoria")
        kind = text(row.get("type"))
        if kind in ("FP", "Q"):
            kind += str(number(row.get("number")) or "")
        provider_id = text(row.get("id"))
        result.append(
            session(
                event["id"] + ":" + kind,
                kind,
                timestamp(row.get("date")),
                state=(
                    "finished"
                    if row.get("status") in ("FINISHED", "Official")
                    else "scheduled"
                ),
                provider_id=provider_id,
            )
        )
        result[-1]["conditions"] = deepcopy(mapping(row.get("condition")))
    if result:
        for s in result:
            broadcast = next(
                (old for old in event["sessions"] if old["id"] == s["id"]), {}
            )
            for key in ("end", "timingId", "broadcastActive", "broadcastState"):
                if key in broadcast:
                    s[key] = broadcast[key]
        event["sessions"] = sorted(result, key=lambda s: s["start"] or float("inf"))


def moto_result_rows(raw, kind="RAC"):
    if not isinstance(mapping(raw).get("classification"), list):
        raise ValueError("Classificazione MotoGP non valida")
    result = []
    for row in raw["classification"]:
        rider = mapping(row.get("rider"))
        gap = mapping(row.get("gap")).get("first")
        lap = mapping(row.get("best_lap")).get("time")
        value = (
            row.get("time")
            if number(row.get("position")) == 1
            else (
                "+" + text(gap)
                if gap not in (None, "0.000", "0", 0)
                else row.get("time")
            )
        )
        result.append(
            {
                "id": text(rider.get("id")),
                "position": number(row.get("position")),
                "name": text(rider.get("full_name")),
                "team": text(mapping(row.get("team")).get("name")),
                "points": points(row.get("points")),
                "laps": number(row.get("total_laps")),
                "status": text(row.get("status")),
                "value": text(
                    (lap if kind not in ("RAC", "SPR") else value) or row.get("status")
                )
                or "—",
                "number": number(rider.get("number")),
                "nationality": text(mapping(rider.get("country")).get("name")),
                "bike": text(mapping(row.get("constructor")).get("name")),
                "averageSpeed": points(row.get("average_speed")),
                "fastestLap": text(lap),
            }
        )
    return result


def validate(snapshot, kind=None):
    if (
        not isinstance(snapshot, dict)
        or snapshot.get("kind") not in ("f1", "motogp")
        or kind
        and snapshot["kind"] != kind
    ):
        raise ValueError("Cache motorsport non valida")
    if (
        not 1950 <= snapshot.get("year", 0) <= 2100
        or not 0 < snapshot.get("fetchedAt", 0) <= time.time() + 300
    ):
        raise ValueError("Data motorsport non valida")
    events = snapshot.get("events")
    rows = snapshot.get("standings")
    if (
        not isinstance(events, list)
        or not 1 <= len(events) <= 100
        or not isinstance(rows, list)
        or not 0 <= len(rows) <= 80
    ):
        raise ValueError("Dati motorsport incompleti")
    ids = set()
    for event in events:
        if not event.get("id") or event["id"] in ids or not event.get("name"):
            raise ValueError("Identità GP non valida")
        ids.add(event["id"])
        if event.get("status") not in ("scheduled", "finished") or not isinstance(
            event.get("round"), str
        ):
            raise ValueError("Stato o turno GP non valido")
        for key in ("start", "end"):
            if event.get(key) is not None and timestamp(event[key]) != event[key]:
                raise ValueError("Orario GP non valido")
        if not isinstance(event.get("sessions"), list) or len(event["sessions"]) > 30:
            raise ValueError("Sessioni non valide")
        session_ids = set()
        for s in event["sessions"]:
            if (
                not s.get("id")
                or s["id"] in session_ids
                or not s.get("name")
                or not s.get("kind")
                or s.get("state") not in ("scheduled", "finished")
            ):
                raise ValueError("Identita sessione non valida")
            session_ids.add(s["id"])
            for key in ("start", "end"):
                if s.get(key) is not None and timestamp(s[key]) != s[key]:
                    raise ValueError("Orario sessione non valido")
            if not isinstance(s.get("results"), list) or len(s["results"]) > 80:
                raise ValueError("Risultati non validi")
    for row in rows + snapshot.get("constructors", []):
        if not row.get("name") or not row.get("id") or row.get("position") is None:
            raise ValueError("Riga classifica non valida")


def read_cache(path, kind):
    try:
        if Path(path).stat().st_size > 2_000_000:
            return None
        raw = json.loads(Path(path).read_text())
        if raw.get("schemaVersion") != 1:
            return None
        validate(raw.get("snapshot"), kind)
        return raw["snapshot"]
    except (OSError, ValueError, TypeError, AttributeError, KeyError):
        return None


def save_cache(path, snapshot):
    # Reuse the same durable atomic file primitive, without football validation.
    import os, tempfile

    validate(snapshot)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=path.parent, prefix="motor-", suffix=".tmp", delete=False
        ) as stream:
            name = stream.name
            json.dump(
                {"schemaVersion": 1, "snapshot": snapshot},
                stream,
                ensure_ascii=False,
                allow_nan=False,
            )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


class MotorClient(HTTPClient):
    def __init__(self):
        super().__init__(allow_lists=True)
        self._jolpica_times = []
        self._last_jolpica = 0
        self._open_times = []

    def get(self, url):
        cooldown = self.cooldowns.get(url)
        if cooldown and cooldown[0] > time.time():
            # A blocked request must not consume either provider's budget.
            return super().get(url)
        if url.startswith(OPENF1) and not (
            url in self.cache and self.cache[url][0] > time.time()
        ):
            now = time.time()
            self._open_times = [t for t in self._open_times if now - t < 60]
            if len(self._open_times) >= 25:
                raise ProviderError(
                    "Budget OpenF1 in pausa",
                    retry_after=max(1, 60 - (now - self._open_times[0])),
                )
            if self._open_times:
                time.sleep(max(0, 0.4 - (now - self._open_times[-1])))
            self._open_times.append(time.time())
        if url.startswith(JOLPICA) and not (
            url in self.cache and self.cache[url][0] > time.time()
        ):
            now = time.time()
            self._jolpica_times = [t for t in self._jolpica_times if now - t < 3600]
            if len(self._jolpica_times) >= 400:
                raise ProviderError(
                    "Budget Jolpica in pausa",
                    retry_after=max(1, 3600 - (now - self._jolpica_times[0])),
                )
            delay = 0.3 - (time.monotonic() - self._last_jolpica)
            if delay > 0:
                time.sleep(delay)
            self._last_jolpica = time.monotonic()
            self._jolpica_times.append(time.time())
        return super().get(url)


def load_event(client, snapshot, event_id, session_id="", *, results=True, force=False):
    snapshot = deepcopy(snapshot)
    event = next((e for e in snapshot["events"] if e["id"] == event_id), None)
    snapshot["detailError"] = ""
    snapshot["detailErrorEventId"] = event_id
    if not event:
        return snapshot
    old_sessions = deepcopy(event["sessions"])
    now = time.time()
    try:
        if snapshot["kind"] == "f1":
            for kind, route in [
                ("RAC", "results"),
                ("Q", "qualifying"),
                ("SPR", "sprint"),
            ]:
                target = next((s for s in event["sessions"] if s["kind"] == kind), None)
                if (
                    not results
                    or not target
                    or not target["start"]
                    or target["start"] > now
                    or session_id
                    and target["id"] != session_id
                    or not force
                    and results_fresh(target, now)
                ):
                    continue
                raw, at = client.get(
                    JOLPICA
                    + str(snapshot["year"])
                    + "/"
                    + event["round"]
                    + "/"
                    + route
                    + ".json?limit=100"
                )
                snapshot["detailAt"] = at
                apply_f1_results(snapshot, raw, kind, event["round"])
            selected = next(
                (s for s in event["sessions"] if s["id"] == session_id), None
            )
            if results and selected and selected["kind"] in ("FP1", "FP2", "FP3", "SQ"):
                try:
                    open_results(client, snapshot, event, selected, force=force)
                    selected["extraError"] = ""
                except (ProviderError, ValueError, KeyError, TypeError, AttributeError):
                    selected["extraError"] = (
                        "Risultati aggiuntivi OpenF1 non disponibili."
                    )
        else:
            starts = [s["start"] for s in event["sessions"] if s.get("start")]
            first = min(starts or [event.get("start") or float("inf")])
            info_ttl = (
                60
                if event.get("end") and first - 3600 <= now <= event["end"] + 86400
                else 21600
            )
            if event.get("broadcastId") and (
                force
                or not event.get("programmeAt")
                or not 0 <= now - event["programmeAt"] < info_ttl
            ):
                raw, at = client.get(MOTO + "events/" + event["broadcastId"])
                moto_programme(raw, event, snapshot["year"])
                event["programmeAt"] = at
            if results and event["start"] and event["start"] < now:
                if (
                    force
                    or not event.get("sessionsAt")
                    or not 0 <= now - event["sessionsAt"] < info_ttl
                ):
                    raw, at = client.get(
                        MOTO
                        + "results/sessions?"
                        + urllib.parse.urlencode(
                            {
                                "eventUuid": event["providerId"],
                                "categoryUuid": snapshot["categoryId"],
                            }
                        )
                    )
                    moto_sessions(raw, event, snapshot["categoryId"])
                    event["sessionsAt"] = at
                    for s in event["sessions"]:
                        s["infoAt"] = at
                        old = next((o for o in old_sessions if o["id"] == s["id"]), {})
                        s.update(
                            results=old.get("results", []),
                            resultsAt=old.get("resultsAt", 0),
                        )
                        for field in ("records", "resultSource"):
                            if field in old:
                                s[field] = deepcopy(old[field])
                selected = next(
                    (s for s in event["sessions"] if s["id"] == session_id), None
                )
                targets = (
                    [selected]
                    if selected
                    else [
                        s
                        for s in event["sessions"]
                        if s["kind"] in ("RAC", "SPR", "Q2")
                    ]
                )
                for target in targets:
                    if (
                        not target
                        or target["state"] != "finished"
                        or not target["providerId"]
                        or not force
                        and results_fresh(target, now)
                    ):
                        continue
                    raw, at = client.get(
                        MOTO
                        + "results/session/"
                        + target["providerId"]
                        + "/classification?seasonYear="
                        + str(snapshot["year"])
                        + "&test=false"
                    )
                    target["results"] = moto_result_rows(raw, target["kind"])
                    target["resultsAt"] = at
                    target["resultSource"] = "PulseLive"
                    target["records"] = deepcopy(items(raw.get("records")))
                    if target["kind"] == "RAC" and target["results"]:
                        event["status"] = "finished"
        event["detailAt"] = time.time()
    except (ProviderError, ValueError, KeyError, TypeError, AttributeError) as error:
        import logging

        logging.getLogger(__name__).warning("%s detail: %s", snapshot["kind"], error)
        snapshot["detailError"] = (
            "Aggiornamento del dettaglio non riuscito. Dati precedenti disponibili."
        )
    validate(snapshot)
    return snapshot


def refresh(client, kind, year, previous=None):
    now = time.time()
    errors = []
    snapshot = {
        "kind": kind,
        "year": year,
        "events": [],
        "standings": [],
        "constructors": [],
        "fetchedAt": now,
        "detailAt": now,
        "detailError": "",
    }
    if kind == "f1":
        raw, at = client.get(JOLPICA + str(year) + ".json?limit=100")
        snapshot["events"] = f1_calendar(raw, year)
        snapshot["fetchedAt"] = at
        raw, at = client.get(JOLPICA + str(year) + "/driverStandings.json?limit=100")
        snapshot["standings"], snapshot["standingsRound"] = f1_standings(raw, year)
        snapshot["standingsAt"] = at
        raw, at = client.get(
            JOLPICA + str(year) + "/constructorStandings.json?limit=100"
        )
        snapshot["constructors"], _ = f1_standings(raw, year, True)
        for kind2, route in [
            ("RAC", "results"),
            ("Q", "qualifying"),
            ("SPR", "sprint"),
        ]:
            try:
                round_id = "last"
                if kind2 in ("Q", "SPR"):
                    completed_events = [
                        e
                        for e in snapshot["events"]
                        if any(
                            s["kind"] == kind2 and s["start"] and s["start"] < now
                            for s in e["sessions"]
                        )
                    ]
                    if not completed_events:
                        continue
                    round_id = completed_events[-1]["round"]
                raw, at = client.get(
                    JOLPICA
                    + str(year)
                    + "/"
                    + round_id
                    + "/"
                    + route
                    + ".json?limit=100"
                )
                snapshot["detailAt"] = at
                apply_f1_results(snapshot, raw, kind2, round_id if round_id != "last" else None)
            except (ProviderError, ValueError, KeyError, TypeError, AttributeError):
                errors.append("Ultimi risultati parziali")
    else:
        raw, _ = client.get(MOTO + "results/seasons")
        season = next((s for s in items(raw) if s.get("year") == year), None)
        if not season:
            raise ValueError("Stagione MotoGP non disponibile")
        raw, _ = client.get(MOTO + "results/categories?seasonUuid=" + season["id"])
        category = next(
            (
                c
                for c in items(raw)
                if c.get("legacy_id") == 3
                and text(c.get("name")).replace("™", "") == "MotoGP"
            ),
            None,
        )
        if not category:
            raise ValueError("Categoria MotoGP non disponibile")
        snapshot["categoryId"] = category["id"]
        snapshot["seasonId"] = season["id"]
        raw, at = client.get(MOTO + "results/events?seasonUuid=" + season["id"])
        snapshot["events"] = moto_calendar(raw, year)
        snapshot["fetchedAt"] = at
        raw, at = client.get(
            MOTO
            + "results/standings?seasonUuid="
            + season["id"]
            + "&categoryUuid="
            + category["id"]
        )
        snapshot["standings"] = moto_standings(raw, year)
        snapshot["standingsAt"] = at
        snapshot["standingsLabel"] = next(
            iter(text(mapping(raw).get("file")).split("/")[-4:-3]), ""
        )
    if previous and previous.get("year") == year:
        for event in snapshot["events"]:
            old = next((e for e in previous["events"] if e["id"] == event["id"]), None)
            if old:
                for s in event["sessions"]:
                    prior = next((x for x in old["sessions"] if x["id"] == s["id"]), {})
                    if s["results"]:
                        preserve_driver_details(s["results"], prior.get("results", []))
                    if not s["results"] and prior.get("results"):
                        s.update(
                            results=deepcopy(prior["results"]),
                            resultsAt=prior["resultsAt"],
                            state=prior["state"],
                        )
                        for field in ("openSessionKey", "resultSource", "extraError"):
                            if field in prior:
                                s[field] = deepcopy(prior[field])
                if not event["sessions"]:
                    event["sessions"] = deepcopy(old["sessions"])
                for field in ("circuitData", "programmeAt", "sessionsAt"):
                    if old.get(field) and not event.get(field):
                        event[field] = deepcopy(old[field])
    upcoming = [e for e in snapshot["events"] if e.get("end") and e["end"] >= now]
    past = [e for e in snapshot["events"] if e.get("end") and e["end"] < now]
    if kind == "motogp":
        for event in upcoming[:1] + past[-1:]:
            snapshot = load_event(client, snapshot, event["id"])
    snapshot["partialError"] = " · ".join(set(errors))
    validate(snapshot, kind)
    return snapshot


def bind_timing(snapshot, timing):
    """Bind provider timing to exactly one calendar session, including delays."""
    timing = timing.copy()
    if not snapshot or snapshot.get("kind") != "f1":
        return timing
    timing.pop("eventId", None)
    timing.pop("sessionId", None)
    kinds = {"Practice 1": "FP1", "Practice 2": "FP2", "Practice 3": "FP3",
             "Qualifying": "Q", "Sprint Qualifying": "SQ", "Sprint Shootout": "SQ",
             "Sprint": "SPR", "Race": "RAC"}
    start = timing.get("start")
    if snapshot and snapshot.get("kind") == "f1" and start:
        candidates = [(e, s) for e in snapshot["events"] for s in e["sessions"]
                      if e["name"].casefold() == timing.get("meeting", "").casefold()
                      and s["kind"] == kinds.get(timing.get("name")) and s.get("start")
                      and abs(s["start"] - start) <= 6 * 3600]
        if len(candidates) == 1:
            event, session = candidates[0]
            timing.update(eventId=event["id"], sessionId=session["id"])
    if not timing.get("sessionId"):
        timing.update(active=False, isLive=False)
    return timing


def present(snapshot, now, *, from_cache=False):
    if not snapshot:
        return {
            "events": [],
            "upcoming": [],
            "past": [],
            "standings": [],
            "constructors": [],
            "live": {},
            "year": datetime.fromtimestamp(now, ROME).year,
        }
    data = deepcopy(snapshot)
    for event in data["events"]:
        event["when"] = (
            event["dateLabel"] if data["kind"] == "motogp" else stamp(event["start"])
        )
        if data["kind"] == "motogp" and event["start"] and event["end"]:
            start = datetime.fromtimestamp(event["start"], ROME)
            end = datetime.fromtimestamp(event["end"], ROME)
            event["when"] = start.strftime("%d/%m") + " – " + end.strftime("%d/%m/%Y")
        for s in event["sessions"]:
            s["when"] = stamp(s["start"])
            s["statusText"] = (
                "Terminata"
                if s["state"] == "finished"
                else (
                    "Orario trascorso"
                    if s["start"] and s["start"] < now
                    else "In programma"
                )
            )
        decorate(event, data["kind"])
    data["upcoming"] = [
        e
        for e in data["events"]
        if e["status"] != "finished" and (not e["end"] or e["end"] >= now)
    ]
    data["past"] = list(
        reversed(
            [
                e
                for e in data["events"]
                if e["status"] == "finished" or e["end"] and e["end"] < now
            ]
        )
    )
    data["nextEvent"] = data["upcoming"][0] if data["upcoming"] else {}
    next_event = data["nextEvent"]
    data["nextSessions"] = [
        s
        for s in next_event.get("sessions", [])
        if s["start"] is None or s["start"] >= now - 1800
    ]
    data["lastEvent"] = data["past"][0] if data["past"] else {}
    for rows in (data["standings"], data["constructors"]):
        for row in rows:
            row["value"] = display(row.get("points")) + " PT"
    data["fromCache"] = from_cache
    return data
