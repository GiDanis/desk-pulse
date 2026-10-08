"""Small, optional motorsport details. No accounts, telemetry streams or Qt."""

import math
import time
import urllib.parse
from copy import deepcopy

from sport_core import mapping, items, number, text, timestamp, ProviderError

OPENF1 = "https://api.openf1.org/v1/"
OPEN_NAMES = {
    "FP1": "Practice 1",
    "FP2": "Practice 2",
    "FP3": "Practice 3",
    "SQ": "Sprint Qualifying",
    "Q": "Qualifying",
    "SPR": "Sprint",
    "RAC": "Race",
}


def preserve_driver_details(rows, previous):
    """Keep separately fetched driver data when refreshing classification."""
    previous = {row["id"]: row for row in previous}
    for row in rows:
        old = previous.get(row["id"], {})
        for field in (
            "pitStops",
            "lapTimes",
            "lapTimesPartial",
            "stints",
            "extraAt",
            "extraError",
            "stintsAt",
            "lapsAt",
            "pitsAt",
        ):
            if field in old:
                row[field] = deepcopy(old[field])


def results_fresh(session, now):
    # Recent results may still receive corrections; settled history is slower.
    ttl = 600 if now - (session.get("start") or now) < 86400 else 21600
    age = now - session.get("resultsAt", 0)
    return bool(session.get("results") and session.get("resultsAt") and 0 <= age < ttl)


def country(value):
    return {
        "UAE": "United Arab Emirates",
        "USA": "United States",
        "UK": "United Kingdom",
    }.get(value, value)


def metric(label, value):
    if value is None or value == "":
        return None
    return {
        "label": label,
        "value": (
            f"{value:g}"
            if isinstance(value, (int, float)) and not isinstance(value, bool)
            else str(value)
        ),
    }


def metrics(*pairs):
    return [row for label, value in pairs if (row := metric(label, value))]


def decimal(value):
    try:
        v = float(value)
        return v if math.isfinite(v) and v >= 0 else None
    except (TypeError, ValueError):
        return None


def seconds(value):
    v = decimal(value)
    if v is None or v == 0:
        return ""
    return f"{int(v // 60)}:{v % 60:06.3f}"


def enrich_f1(row):
    lap = mapping(row.get("FastestLap"))
    grid = number(row.get("grid"))
    finish = number(row.get("position"))
    return {
        "number": number(row.get("number")),
        "nationality": text(mapping(row.get("Driver")).get("nationality")),
        "grid": grid,
        "gridChange": grid - finish if grid and finish else None,
        "fastestLap": text(mapping(lap.get("Time")).get("time")),
        "fastestLapNumber": number(lap.get("lap")),
        "qualifying": {key: text(row.get(key)) for key in ("Q1", "Q2", "Q3")},
    }


def moto_circuit(raw, event):
    circuit = mapping(raw.get("circuit"))
    track = next(
        (t for t in items(circuit.get("tracks")) if t.get("is_active") is True), {}
    )
    category = next(
        (
            c
            for c in items(raw.get("event_categories"))
            if c.get("category_timing_id") == 3
        ),
        {},
    )
    event["circuitData"] = {
        "country": text(circuit.get("country")),
        "city": text(circuit.get("city")),
        "length": decimal(track.get("lenght")),
        "leftCorners": number(track.get("left_corners")),
        "rightCorners": number(track.get("right_corners")),
        "straight": number(track.get("longest_straight")),
        "raceLaps": number(category.get("num_laps")),
        "sprintLaps": number(category.get("sprint_num_laps")),
        "distance": decimal(mapping(category.get("distance")).get("kiloMeters")),
    }


def open_session(client, snapshot, event, session):
    """Match one exact session by season, kind and scheduled time, never 'latest'."""
    start = session.get("start")
    if snapshot["year"] < 2023 or not start or start > time.time() - 7200:
        return None
    name = OPEN_NAMES.get(session["kind"])
    if not name:
        return None
    # The endpoint does not decode '+' as a space in session names. Query the
    # small season/session list using %20, then validate timestamps ourselves.
    query = urllib.parse.urlencode(
        {"year": snapshot["year"], "session_name": name}, quote_via=urllib.parse.quote
    )
    raw, _ = client.get(OPENF1 + "sessions?" + query)
    matches = [
        s
        for s in items(raw)
        if s.get("year") == snapshot["year"]
        and s.get("session_name") == name
        and timestamp(s.get("date_start"))
        and abs(timestamp(s["date_start"]) - start) <= 21600
        and (
            not mapping(event.get("circuitData")).get("country")
            or country(s.get("country_name"))
            == country(event["circuitData"]["country"])
        )
    ]
    if len(matches) != 1:
        raise ValueError("Identità sessione OpenF1 non univoca")
    match = matches[0]
    end = timestamp(match.get("date_end"))
    if not end or end > time.time() - 1800 or not number(match.get("session_key")):
        return None
    return match


def open_results(client, snapshot, event, session, *, force=False):
    if (
        session.get("openSessionKey")
        and session.get("results")
        and results_fresh(session, time.time())
        and not force
    ):
        return
    match = open_session(client, snapshot, event, session)
    if not match:
        return
    key = match["session_key"]
    raw, at = client.get(OPENF1 + "session_result?session_key=" + str(key))
    drivers, _ = client.get(OPENF1 + "drivers?session_key=" + str(key))
    driver_map = {
        d.get("driver_number"): d for d in items(drivers) if d.get("session_key") == key
    }
    rows = []
    for row in items(raw):
        d = driver_map.get(row.get("driver_number"), {})
        if row.get("session_key") != key or not d or not number(row.get("position")):
            continue
        duration = row.get("duration")
        times = duration if isinstance(duration, list) else [duration]
        best = next((seconds(t) for t in reversed(times) if seconds(t)), "")
        rows.append(
            {
                "id": "openf1:" + str(row["driver_number"]),
                "number": row["driver_number"],
                "position": number(row["position"]),
                "name": text(d.get("full_name")),
                "team": text(d.get("team_name")),
                "value": best or "—",
                "points": None,
                "laps": number(row.get("number_of_laps")),
                "status": "Ritirato" if row.get("dnf") else "",
                "qualifying": (
                    {"Q" + str(i + 1): seconds(v) for i, v in enumerate(times)}
                    if session["kind"] == "SQ"
                    else {}
                ),
            }
        )
    if not rows or len(rows) > 30:
        raise ValueError("Risultati OpenF1 incompleti")
    preserve_driver_details(rows, session.get("results", []))
    session.update(
        results=sorted(rows, key=lambda r: r["position"]),
        resultsAt=at,
        resultSource="OpenF1",
        openSessionKey=key,
        state="finished",
    )


def load_driver(client, snapshot, event_id, session_id, driver_id, *, force=False):
    event = next((e for e in snapshot["events"] if e["id"] == event_id), {})
    session = next((s for s in event.get("sessions", []) if s["id"] == session_id), {})
    row = next((r for r in session.get("results", []) if r["id"] == driver_id), None)
    if not row or snapshot["kind"] != "f1" or session.get("state") != "finished":
        return snapshot
    if not force and row.get("extraAt") and 0 <= time.time() - row["extraAt"] < 21600:
        return snapshot
    try:
        if session["kind"] == "RAC" and not driver_id.startswith("openf1:"):
            from motorsport_core import JOLPICA, f1_table

            base = (
                JOLPICA
                + f'{snapshot["year"]}/{event["round"]}/drivers/{urllib.parse.quote(driver_id, safe="")}/'
            )
            for route, dest, source in [
                ("pitstops", "pitStops", "PitStops"),
                ("laps", "lapTimes", "Laps"),
            ]:
                raw, at = client.get(base + route + ".json?limit=100")
                table = f1_table(raw, "RaceTable", snapshot["year"])
                races = items(table.get("Races"))
                if any(str(r.get("round")) != event["round"] for r in races):
                    raise ValueError("Dettagli di un altro GP")
                values = []
                for race in races:
                    for item in items(race.get(source)):
                        if route == "pitstops" and item.get("driverId") == driver_id:
                            values.append(
                                {
                                    "label": "Pit lane "
                                    + text(item.get("stop"))
                                    + " · giro "
                                    + text(item.get("lap")),
                                    "value": text(item.get("duration")) + " s",
                                }
                            )
                        elif route == "laps":
                            timing = next(
                                (
                                    t
                                    for t in items(item.get("Timings"))
                                    if t.get("driverId") == driver_id
                                ),
                                {},
                            )
                            if timing:
                                values.append(
                                    {
                                        "label": "Giro " + text(item.get("number")),
                                        "value": text(timing.get("time")),
                                    }
                                )
                row[dest] = values
                row["pitsAt" if route == "pitstops" else "lapsAt"] = at
                if route == "laps":
                    row["lapTimesPartial"] = (
                        number(mapping(raw.get("MRData")).get("total")) or 0
                    ) > 100
        if snapshot["year"] >= 2023 and row.get("number"):
            match = (
                {"session_key": session["openSessionKey"]}
                if session.get("openSessionKey")
                else open_session(client, snapshot, event, session)
            )
            if match:
                raw, at = client.get(
                    OPENF1
                    + "stints?"
                    + urllib.parse.urlencode(
                        {
                            "session_key": match["session_key"],
                            "driver_number": row["number"],
                        }
                    )
                )
                stints = [
                    s
                    for s in items(raw)
                    if s.get("session_key") == match["session_key"]
                    and s.get("driver_number") == row["number"]
                ]
                row["stints"] = metrics(
                    *[
                        (
                            "Stint "
                            + str(s.get("stint_number"))
                            + " · "
                            + text(s.get("compound")),
                            "Giri "
                            + str(s.get("lap_start"))
                            + "–"
                            + str(s.get("lap_end"))
                            + (
                                " · inizio: "
                                + (
                                    "nuove"
                                    if s["tyre_age_at_start"] == 0
                                    else str(s["tyre_age_at_start"]) + " giri"
                                )
                                if s.get("tyre_age_at_start") is not None
                                else ""
                            ),
                        )
                        for s in stints
                    ]
                )
                row["stintsAt"] = at
            else:
                row["extraError"] = (
                    "Gomme disponibili dopo la chiusura della finestra live."
                )
                return snapshot
        row["extraAt"] = time.time()
        row["extraError"] = ""
    except (ProviderError, ValueError, KeyError, TypeError, AttributeError):
        row["extraError"] = "Dettagli aggiuntivi non disponibili. Risultati conservati."
    return snapshot


def decorate(event, kind):
    c = mapping(event.get("circuitData"))
    event["infoRows"] = metrics(
        ("Circuito", event.get("circuit")),
        ("Paese", c.get("country")),
        ("Località", c.get("city")),
        ("Lunghezza", f'{c["length"]/1000:g} km' if c.get("length") else None),
        (
            "Curve",
            (
                f'{c["leftCorners"]} sinistra · {c["rightCorners"]} destra'
                if c.get("leftCorners") is not None
                and c.get("rightCorners") is not None
                else None
            ),
        ),
        ("Rettilineo", str(c["straight"]) + " m" if c.get("straight") else None),
        (
            "Gara / Sprint",
            (
                str(c["raceLaps"]) + " / " + str(c.get("sprintLaps") or "—") + " giri"
                if c.get("raceLaps")
                else None
            ),
        ),
        ("Distanza gara", str(c["distance"]) + " km" if c.get("distance") else None),
    )
    event["infoRows"].sort(
        key=lambda r: [
            "Circuito",
            "Lunghezza",
            "Curve",
            "Rettilineo",
            "Gara / Sprint",
            "Distanza gara",
            "Paese",
            "Località",
        ].index(r["label"])
    )
    summary = []
    for s in event["sessions"]:
        conditions = mapping(s.get("conditions"))
        s["infoRows"] = metrics(
            ("Orario italiano", s.get("when")),
            ("Stato", s.get("statusText")),
            (
                "Pista",
                {"Dry": "Asciutta", "Wet": "Bagnata"}.get(
                    conditions.get("track"), conditions.get("track")
                ),
            ),
            (
                "Aria / asfalto",
                (
                    " / ".join(text(conditions.get(k)) for k in ("air", "ground"))
                    if conditions
                    else None
                ),
            ),
            ("Umidità", conditions.get("humidity")),
            ("Meteo della sessione", conditions.get("weather")),
        )
        s["infoRows"].sort(
            key=lambda r: [
                "Pista",
                "Aria / asfalto",
                "Umidità",
                "Meteo della sessione",
                "Orario italiano",
                "Stato",
            ].index(r["label"])
        )
        if s.get("results"):
            summary.extend(metrics((s["name"] + " · primo", s["results"][0]["name"])))
        for record in items(s.get("records")):
            if record.get("type") in ("bestLap", "poleLap"):
                summary.extend(
                    metrics(
                        (
                            "Record "
                            + ("giro" if record["type"] == "bestLap" else "pole"),
                            text(mapping(record.get("rider")).get("full_name"))
                            + " · "
                            + text(mapping(record.get("bestLap")).get("time"))
                            + " · "
                            + str(record.get("year") or ""),
                        )
                    )
                )
        for row in s.get("results", []):
            change = row.get("gridChange")
            row["detailRows"] = metrics(
                ("Team", row.get("team")),
                ("Moto", row.get("bike")),
                ("Numero", row.get("number")),
                ("Nazionalità", row.get("nationality")),
                ("Posizione finale", row.get("position")),
                ("Tempo / distacco", row.get("value")),
                ("Punti", row.get("points")),
                ("Giri completati", row.get("laps")),
                ("Griglia", "Pit lane" if row.get("grid") == 0 else row.get("grid")),
                (
                    "Variazione griglia → arrivo",
                    f"{change:+d}" if change is not None else None,
                ),
                ("Giro veloce", row.get("fastestLap")),
                ("Al giro", row.get("fastestLapNumber")),
                (
                    "Velocità media",
                    (
                        str(row["averageSpeed"]) + " km/h"
                        if row.get("averageSpeed")
                        else None
                    ),
                ),
                (
                    "Stato",
                    {
                        "Finished": "Arrivato",
                        "INSTND": "Classificato",
                        "DNS": "Non partito",
                        "DNF": "Ritirato",
                        "DSQ": "Squalificato",
                    }.get(row.get("status"), row.get("status")),
                ),
                *[(k, v) for k, v in mapping(row.get("qualifying")).items()],
            )
            order = [
                "Posizione finale",
                "Tempo / distacco",
                "Punti",
                "Griglia",
                "Variazione griglia → arrivo",
                "Q1",
                "Q2",
                "Q3",
                "Giro veloce",
                "Al giro",
                "Velocità media",
                "Giri completati",
                "Stato",
                "Team",
                "Moto",
                "Numero",
                "Nazionalità",
            ]
            row["detailRows"].sort(
                key=lambda r: (
                    order.index(r["label"]) if r["label"] in order else len(order)
                )
            )
    # The same circuit records may occur in several session responses.
    event["summaryRows"] = list({(r["label"], r["value"]): r for r in summary}.values())
