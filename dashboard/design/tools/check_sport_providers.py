#!/usr/bin/env python3
"""Bounded, read-only research checks; no credentials or dashboard dependencies.

This records HTTP and schema evidence, not live latency or provider uptime.
Connection cookies/tokens and complete response bodies are never exported.
"""
import argparse
import hashlib
import io
import json
import platform
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

UA = "SmartPC-Dashboard/0.6 (private research)"
records = []


def now():
    return datetime.now(timezone.utc).isoformat()


def fetch(name, url, ua=UA, method="GET", json_response=True):
    headers = {"Accept": "application/json" if json_response else "*/*"}
    if ua is not None:
        headers["User-Agent"] = ua
    record = {"name": name, "url": url, "method": method,
              "user_agent": ua or "urllib default", "requested_at": now()}
    started = time.monotonic()
    response = None
    data = None
    try:
        request = urllib.request.Request(url, headers=headers, method=method)
        try:
            response = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            record["http_status"] = response.status
            record["headers"] = {
                key: response.headers[key] for key in
                ("Content-Type", "Cache-Control", "Age", "Date", "Last-Modified", "ETag", "Server", "Retry-After")
                if response.headers.get(key) is not None
            }
            body = response.read(4_000_001)
            record["bytes"] = len(body)
            record["body_sha256"] = hashlib.sha256(body).hexdigest()
            if len(body) > 4_000_000:
                record["error"] = "response exceeds research size limit"
            elif 200 <= response.status < 300 and json_response:
                try:
                    data = json.loads(body)
                    record["json_type"] = type(data).__name__
                    record["top_keys"] = list(data)[:25] if isinstance(data, dict) else []
                    if isinstance(data, list):
                        record["items"] = len(data)
                except (ValueError, UnicodeDecodeError):
                    record["error"] = "success HTTP response is not JSON"
            elif 200 <= response.status < 300:
                data = body
    except (OSError, ValueError) as error:
        record["error"] = type(error).__name__ + ": " + str(error)[:150]
    record["elapsed_ms"] = round((time.monotonic() - started) * 1000, 1)
    record["completed_at"] = now()
    records.append(record)
    return data, record


def espn_events(data):
    return [{"id": event.get("id"), "name": event.get("name"),
             "date": event.get("date"), "status": event.get("status", {}).get("type", {}).get("name"),
             "teams": [{"name": c.get("team", {}).get("displayName"),
                        "side": c.get("homeAway"), "score": c.get("score")}
                       for c in event.get("competitions", [{}])[0].get("competitors", [])]}
            for event in data.get("events", [])] if isinstance(data, dict) else []


def club_name(name):
    normalized = re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()
    return {"inter": "internazionale", "as roma": "roma", "ac milan": "milan"}.get(normalized, normalized)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="pc")
    parser.add_argument("--output")
    args = parser.parse_args()
    started = now()
    espn = "https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/"
    fotmob = "https://www.fotmob.com/api/data/"
    # Same URL and transport: this does not determine a CDN's TLS policy.
    for prefix, url in [("espn", espn + "scoreboard"), ("fotmob", fotmob + "tltable?leagueId=55")]:
        for label, ua in [("default", None), ("app", UA), ("mozilla", "Mozilla/5.0")]:
            data, rec = fetch(prefix + "_ua_" + label, url, ua=ua)
            if prefix == "espn":
                rec["events"] = espn_events(data)
            if prefix == "fotmob" and isinstance(data, list):
                rec["table_entries"] = sum(len(t.get("data", {}).get("table", {}).get("all", [])) for t in data)
    data, rec = fetch("espn_standings_wrong_path", espn + "standings")
    data, rec = fetch("espn_standings", "https://site.api.espn.com/apis/v2/sports/soccer/ita.1/standings")
    if isinstance(data, dict):
        rec["season"] = data.get("season")
        rec["entries"] = sum(len(c.get("standings", {}).get("entries", [])) for c in data.get("children", []))
    league, rec = fetch("fotmob_serie_a_current", fotmob + "leagues?id=55&ccode3=ITA&season=2026%2F2027")
    if isinstance(league, dict):
        matches = league.get("fixtures", {}).get("allMatches", [])
        rec["fixtures"] = len(matches)
        rec["seasons"] = league.get("allAvailableSeasons", [])
        finished = [m for m in matches if m.get("status", {}).get("finished")]
        rec["finished"] = len(finished)
        if finished:
            match = finished[0]
            rec["sample"] = match
            detail, dr = fetch("fotmob_finished_detail", fotmob + "matchDetails?matchId=" + str(match["id"]))
            if isinstance(detail, dict):
                content = detail.get("content", {})
                dr["header"] = detail.get("header")
                dr["content_blocks"] = {k: {"type": type(v).__name__, "populated": bool(v)} for k, v in content.items()}
                date = match.get("status", {}).get("utcTime", "")[:10].replace("-", "")
                board, br = fetch("espn_same_fixture_day", espn + "scoreboard?dates=" + date)
                br["events"] = espn_events(board)
                if isinstance(board, dict) and board.get("events"):
                    # Matching evidence only; no automatic cross-provider identity fusion.
                    for event in board["events"]:
                        sides = {c.get("homeAway"): club_name(c.get("team", {}).get("displayName", ""))
                                 for c in event.get("competitions", [{}])[0].get("competitors", [])}
                        same_sides = all(sides.get(side) == club_name(match.get(side, {}).get("name", ""))
                                         for side in ("home", "away"))
                        if same_sides and event.get("date", "")[:16] == match.get("status", {}).get("utcTime", "")[:16]:
                            summary, sr = fetch("espn_finished_detail", espn + "summary?event=" + str(event["id"]))
                            if isinstance(summary, dict):
                                sr["header"] = summary.get("header")
                                sr["blocks"] = {k: {"type": type(summary.get(k)).__name__, "populated": bool(summary.get(k))}
                                                for k in ["boxscore", "commentary", "keyEvents", "rosters", "standings"]}
                            break
    old, rec = fetch("fotmob_previous_season", fotmob + "leagues?id=55&ccode3=ITA&season=2024%2F2025")
    if isinstance(old, dict):
        rec["fixtures"] = len(old.get("fixtures", {}).get("allMatches", []))
    fetch("fotmob_old_route", "https://www.fotmob.com/api/leagues?id=55")
    for package in ["pyfotmob", "mobfot"]:
        meta, rec = fetch(package + "_metadata", "https://pypi.org/pypi/" + package + "/json")
        if isinstance(meta, dict):
            rec["version"] = meta["info"]["version"]
            wheel = next((x for x in meta["urls"] if x["filename"].endswith(".whl")), None)
            if wheel:
                body, wr = fetch(package + "_source_wheel", wheel["url"], json_response=False)
                wr["uploaded"] = wheel["upload_time_iso_8601"]
                if isinstance(body, bytes):
                    with zipfile.ZipFile(io.BytesIO(body)) as archive:
                        wr["source_routes"] = [{"file": name, "line": line.strip()}
                                               for name in archive.namelist() if name.endswith(".py")
                                               for line in archive.read(name).decode().splitlines()
                                               if "fotmob.com" in line]
    fetch("bsd_coverage", "https://sports.bzzoiro.com/api/v2/coverage/")
    fetch("bsd_without_token", "https://sports.bzzoiro.com/api/v2/events/live/?league_id=4")
    fetch("football_data_without_token", "https://api.football-data.org/v4/competitions/SA/matches")
    for path in ["current.json?limit=100", "current/last/results.json", "current/last/qualifying.json",
                 "current/driverStandings.json", "current/constructorStandings.json", "1950/1/results.json"]:
        data, rec = fetch("jolpica_" + path.split("?")[0], "https://api.jolpi.ca/ergast/f1/" + path)
        if isinstance(data, dict):
            mr = data.get("MRData", {})
            rec["total"] = mr.get("total")
            table = mr.get("RaceTable", mr.get("StandingsTable", {}))
            rec["season"] = table.get("season")
            rec["races"] = len(table.get("Races", []))
    data, rec = fetch("espn_f1", "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard")
    rec["events"] = espn_events(data)
    fetch("f1_static_index", "https://livetiming.formula1.com/static/2026/Index.json")
    # Negotiation evidence only; no token values are stored, no stream subscription.
    legacy_params = urllib.parse.urlencode({"clientProtocol": "1.5", "connectionData": '[{"name":"Streaming"}]'})
    data, rec = fetch("f1_legacy_negotiate", "https://livetiming.formula1.com/signalr/negotiate?" + legacy_params)
    if isinstance(data, dict):
        rec["protocol"] = data.get("ProtocolVersion")
        rec["supports_websocket"] = data.get("TryWebSockets")
    data, rec = fetch("f1_core_negotiate", "https://livetiming.formula1.com/signalrcore/negotiate?negotiateVersion=1", method="POST")
    if isinstance(data, dict):
        rec["available_transports"] = data.get("availableTransports")
    moto = "https://api.motogp.pulselive.com/motogp/v1/"
    seasons, rec = fetch("motogp_seasons", moto + "results/seasons")
    if isinstance(seasons, list) and seasons:
        rec["years"] = [s.get("year") for s in seasons]
        season = next((s for s in seasons if s.get("current")), seasons[0])
        cats, cr = fetch("motogp_categories", moto + "results/categories?seasonUuid=" + season["id"])
        if isinstance(cats, list):
            cr["categories"] = cats
            cat = next((c for c in cats if c.get("name", "").replace("™", "") == "MotoGP"), None)
            if cat:
                standing, sr = fetch("motogp_standings", moto + "results/standings?seasonUuid=" + season["id"] + "&categoryUuid=" + cat["id"])
                if isinstance(standing, dict):
                    sr["classification_count"] = len(standing.get("classification", []))
        events, er = fetch("motogp_events", moto + "results/events?seasonUuid=" + season["id"])
        if isinstance(events, list):
            er["event_count"] = len(events)
        past, pr = fetch("motogp_1949_events", moto + "results/events?seasonUuid=" + seasons[-1]["id"])
        if isinstance(past, list):
            pr["event_count"] = len(past)
    data, rec = fetch("motogp_lite", moto + "timing-gateway/livetiming-lite")
    if isinstance(data, dict):
        rec["head"] = data.get("head")
        riders = data.get("rider", {})
        rec["rider_count"] = len(riders)
        rec["rider_sample"] = next(iter(riders.values()), None) if isinstance(riders, dict) else None
    result = {"schema_version": 1, "label": args.label, "started_at": started,
              "completed_at": now(), "python": platform.python_version(), "machine": platform.machine(),
              "scope": "bounded HTTP/schema/source checks; no live latency, no load or uptime measurement", "checks": records}
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output)
    else:
        sys.stdout.write(output)
    statuses = {}
    for record in records:
        key = str(record.get("http_status", "network_error"))
        statuses[key] = statuses.get(key, 0) + 1
    print(json.dumps({"label": args.label, "requests": len(records), "http_statuses": statuses}), file=sys.stderr)


if __name__ == "__main__":
    main()
