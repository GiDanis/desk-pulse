"""Favourite club profile and multi-competition fixtures, isolated from Serie A."""

from copy import deepcopy
from datetime import datetime
import json
import os
from pathlib import Path
import re
import tempfile
import time
from sport_core import (
    FOTMOB,
    LIVE_STATES,
    ProviderError,
    fotmob_detail,
    make_match,
    mapping,
    items,
    number,
    text,
    timestamp,
    ROME,
    MATCH_STATES,
)

ROLES = {
    "keepers": "Portiere",
    "defenders": "Difensore",
    "midfielders": "Centrocampista",
    "attackers": "Attaccante",
}


def team_fixture(raw, team_id, season):
    home, away = mapping(raw.get("home")), mapping(raw.get("away"))
    if team_id not in (str(home.get("id")), str(away.get("id"))):
        raise ValueError("Partita di un’altra squadra")
    tournament = mapping(raw.get("tournament"))
    league_id = number(tournament.get("leagueId"))
    if not league_id or not text(tournament.get("name")):
        raise ValueError("Competizione assente")
    status = mapping(raw.get("status"))
    score = re.fullmatch(r"\s*(\d+)\s*[-–]\s*(\d+)\s*", text(status.get("scoreStr")))
    from sport_core import fotmob_status

    tentative = status.get("matchDateTbd") is True or status.get("matchTimeTbd") is True
    value = make_match(
        home,
        away,
        provider="fotmob",
        provider_id=raw.get("id"),
        season=season,
        kickoff=None if tentative else timestamp(status.get("utcTime")),
        status=fotmob_status(status),
        scores=score.groups() if score else [None, None],
        round_name=tournament.get("stage", ""),
        raw=status,
    )
    value.update(
        competitionId="football:" + str(league_id),
        competitionName={"Club Friendlies": "Amichevoli"}.get(
            text(tournament["name"]), text(tournament["name"])
        ),
        providerLeagueId=league_id,
        canonicalMatchId="team:foto:" + str(raw["id"]),
        dateTentative=tentative,
        dateLabel=(
            text(status.get("utcTime"))[:10]
            if status.get("matchDateTbd") is not True
            else ""
        ),
    )
    return value


def parse_team(raw, provider_id, team_id, acquired):
    details = mapping(raw.get("details"))
    overview = mapping(raw.get("overview"))
    if (
        str(details.get("id")) != provider_id
        or not text(details.get("name"))
        or details.get("type") != "team"
    ):
        raise ValueError("Identità squadra errata")
    season = text(overview.get("season") or details.get("latestSeason"), 20)
    if not re.fullmatch(r"\d{4}/\d{4}", season):
        raise ValueError("Stagione squadra non valida")
    raw_fixtures = mapping(mapping(raw.get("fixtures")).get("allFixtures")).get(
        "fixtures"
    )
    if not isinstance(raw_fixtures, list) or len(raw_fixtures) > 200:
        raise ValueError("Calendario squadra non valido")
    fixtures = [team_fixture(row, provider_id, season) for row in raw_fixtures]
    for fixture in fixtures:
        # Numeric provider IDs remain stable when club display names differ.
        side = "home" if fixture["homeProviderId"] == provider_id else "away"
        fixture[side + "TeamId"] = team_id
        fixture["fetchedAt"] = acquired
    venue = mapping(overview.get("venue"))
    widget = mapping(venue.get("widget"))
    stat_pairs = {
        pair[0]: pair[1]
        for pair in items(venue.get("statPairs"))
        if isinstance(pair, list) and len(pair) == 2
    }
    squad = []
    coach = ""
    for group in items(mapping(raw.get("squad")).get("squad")):
        group = mapping(group)
        title = text(group.get("title"))
        for player in items(group.get("members")):
            player = mapping(player)
            name = text(player.get("name"))
            if title == "coach":
                coach = name
                continue
            if name and player.get("id"):
                squad.append(
                    {
                        "id": str(player["id"]),
                        "name": name,
                        "role": ROLES.get(
                            title,
                            text(mapping(player.get("role")).get("fallback"))
                            or "Giocatore",
                        ),
                        "shirtNumber": number(player.get("shirtNumber")),
                        "age": number(player.get("age")),
                        "country": text(player.get("ccode")),
                    }
                )
    standing = {}
    for table in items(raw.get("table")):
        table = mapping(mapping(table).get("data"))
        if table.get("leagueId") != 55:
            continue
        row = next(
            (
                r
                for r in items(mapping(table.get("table")).get("all"))
                if str(r.get("id")) == provider_id
            ),
            None,
        )
        if row:
            goals = re.fullmatch(r"(\d+)\s*[-–]\s*(\d+)", text(row.get("scoresStr")))
            standing = {
                "position": number(row.get("idx")),
                "points": number(row.get("pts")),
                "played": number(row.get("played")),
                "wins": number(row.get("wins")),
                "draws": number(row.get("draws")),
                "losses": number(row.get("losses")),
                "goalsFor": number(goals[1]) if goals else None,
                "goalsAgainst": number(goals[2]) if goals else None,
                "goalDifference": number(row.get("goalConDiff"), signed=True),
            }
    data = {
        "teamId": team_id,
        "providerTeamId": provider_id,
        "name": text(details.get("name")),
        "season": season,
        "source": "FotMob",
        "fetchedAt": acquired,
        "calendarScope": "team",
        "fixtures": fixtures,
        "standing": standing,
        "stadium": text(widget.get("name")),
        "city": text(widget.get("city")),
        "capacity": number(stat_pairs.get("Capacity")),
        "opened": number(stat_pairs.get("Opened")),
        "country": text(details.get("country")),
        "coach": coach,
        "squad": squad,
        "detailError": "",
        "detailErrorMatchId": "",
    }
    validate(data)
    return data


def validate(data):
    if (
        not isinstance(data, dict)
        or not str(data.get("providerTeamId", "")).isdigit()
        or not data.get("teamId")
        or not data.get("name")
    ):
        raise ValueError("Profilo squadra non valido")
    if (
        timestamp(data.get("fetchedAt")) is None
        or data["fetchedAt"] > time.time() + 300
        or not re.fullmatch(r"\d{4}/\d{4}", data.get("season", ""))
    ):
        raise ValueError("Data profilo non valida")
    if (
        not isinstance(data.get("fixtures"), list)
        or not 0 <= len(data["fixtures"]) <= 200
        or not isinstance(data.get("squad"), list)
        or len(data["squad"]) > 100
    ):
        raise ValueError("Profilo incompleto")
    ids = set()
    for match in data["fixtures"]:
        if match.get("status") not in MATCH_STATES:
            raise ValueError("Stato calendario squadra errato")
        identity = match.get("canonicalMatchId")
        if (
            not identity
            or identity in ids
            or not str(match.get("providerMatchId", "")).isdigit()
            or data["providerTeamId"]
            not in (match.get("homeProviderId"), match.get("awayProviderId"))
        ):
            raise ValueError("Identità calendario squadra errata")
        ids.add(identity)
        if number(match.get("providerLeagueId")) is None or match.get(
            "competitionId"
        ) != "football:" + str(match["providerLeagueId"]):
            raise ValueError("Competizione squadra errata")
        if (
            match.get("kickoffUtc") is not None
            and timestamp(match["kickoffUtc"]) != match["kickoffUtc"]
        ):
            raise ValueError("Orario calendario errato")


def read_cache(path, provider_id, team_id):
    try:
        if Path(path).stat().st_size > 2_000_000:
            return None
        envelope = json.loads(Path(path).read_text())
        data = envelope["snapshot"]
        if (
            envelope.get("schemaVersion") != 1
            or data.get("providerTeamId") != provider_id
            or data.get("teamId") != team_id
        ):
            return None
        validate(data)
        return data
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None


def save_cache(path, data):
    validate(data)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=path.parent, prefix="team-", suffix=".tmp", delete=False
        ) as stream:
            name = stream.name
            json.dump(
                {"schemaVersion": 1, "snapshot": data},
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


def refresh(
    client, provider_id, team_id, previous=None, match_id="", detail_only=False
):
    if detail_only and previous:
        data = deepcopy(previous)
    else:
        raw, at = client.get(FOTMOB + "teams?id=" + provider_id + "&ccode3=ITA")
        data = parse_team(raw, provider_id, team_id, at)
        if previous and previous["season"] == data["season"]:
            for match in data["fixtures"]:
                old = next(
                    (
                        m
                        for m in previous["fixtures"]
                        if m["providerMatchId"] == match["providerMatchId"]
                    ),
                    {},
                )
                if old.get("detailFetchedAt") and all(
                    match.get(k) == old.get(k)
                    for k in ("status", "homeScore", "awayScore")
                ):
                    for key in (
                        "events",
                        "stats",
                        "lineups",
                        "venue",
                        "detailFetchedAt",
                    ):
                        match[key] = deepcopy(old.get(key))
    data["detailError"] = ""
    data["detailErrorMatchId"] = match_id
    match = next(
        (m for m in data["fixtures"] if m["canonicalMatchId"] == match_id), None
    )
    if match:
        try:
            raw, at = client.get(
                FOTMOB + "matchDetails?matchId=" + match["providerMatchId"]
            )
            detail = fotmob_detail(raw, match)
            detail["detailFetchedAt"] = at
            data["fixtures"][data["fixtures"].index(match)] = detail
        except (ProviderError, ValueError, TypeError, KeyError, AttributeError):
            data["detailError"] = (
                "Dettaglio non disponibile. Dati precedenti conservati."
            )
    validate(data)
    return data


def present(data, now, team_id="", from_cache=False):
    if not data:
        return {}
    result = deepcopy(data)
    fixtures = result["fixtures"]
    for match in fixtures:
        kickoff = match.get("kickoffUtc")
        match["when"] = (
            datetime.fromtimestamp(kickoff, ROME).strftime("%d/%m · %H:%M")
            if kickoff
            else (
                match.get("dateLabel", "") + " · orario da confermare"
                if match.get("dateLabel")
                else "Data da confermare"
            )
        )
        match["scoreText"] = (
            str(match["homeScore"]) + " – " + str(match["awayScore"])
            if match.get("homeScore") is not None and match.get("awayScore") is not None
            else "—"
        )
        match["statusText"] = {
            "scheduled": "In programma",
            "postponed": "Rinviata",
            "cancelled": "Annullata",
            "finished": "Terminata",
            "live": "In corso",
            "half_time": "Intervallo",
            "unknown": "Da verificare",
        }.get(match["status"], "Da verificare")
        match["isLive"] = False
        match["fresh"] = not from_cache and 0 <= now - match.get("fetchedAt", 0) <= 90
        match["side"] = "Casa" if team_id == match["homeTeamId"] else "Trasferta"
    fixtures.sort(
        key=lambda m: (m.get("kickoffUtc") or float("inf"), m["providerMatchId"])
    )
    result["upcoming"] = [
        m
        for m in fixtures
        if m["status"] == "postponed"
        or m["status"] == "scheduled"
        and (not m.get("kickoffUtc") or m["kickoffUtc"] >= now - 10800)
    ]
    result["active"] = [
        m
        for m in fixtures
        if m["status"] in LIVE_STATES
        and m.get("kickoffUtc")
        and -900 <= now - m["kickoffUtc"] <= 6 * 3600
    ]
    # Replays with unconfirmed dates sort after dated futures, but finished
    # matches without a time must not replace the known latest result.
    result["results"] = sorted(
        [m for m in fixtures if m["status"] == "finished"],
        key=lambda m: m.get("kickoffUtc") or 0,
        reverse=True,
    )
    form = []
    for match in reversed(result["results"][:5]):
        home = team_id == match["homeTeamId"]
        a, b = (
            (match.get("homeScore"), match.get("awayScore"))
            if home
            else (match.get("awayScore"), match.get("homeScore"))
        )
        form.append(
            "—" if a is None or b is None else "V" if a > b else "N" if a == b else "P"
        )
    result.update(form=" · ".join(form), fromCache=from_cache)
    return result


def league_fallback(league, team_id):
    row = next((r for r in league.get("standings", []) if r["teamId"] == team_id), {})
    team = next((t for t in league.get("teams", []) if t["id"] == team_id), {})
    matches = [
        deepcopy(m)
        for m in league.get("fixtures", [])
        if team_id in (m["homeTeamId"], m["awayTeamId"])
    ]
    if not team:
        return {}
    for match in matches:
        match.update(competitionName="Serie A", providerLeagueId=55)
    data = {
        "teamId": team_id,
        "name": team["name"],
        "season": league.get("season", ""),
        "source": "FotMob" if league.get("provider") == "fotmob" else "ESPN",
        "fetchedAt": league.get("fetchedAt", 0),
        "calendarScope": "league",
        "fixtures": matches,
        "standing": row,
        "squad": [],
        "stadium": "",
        "city": "",
        "country": "",
        "coach": "",
    }
    return present(
        data, time.time(), team_id, from_cache=league.get("fromCache", False)
    )


def profile_interval(matches, now):
    """Wake before the next kickoff, and poll only plausible active matches."""
    for match in matches:
        kickoff = match.get("kickoffUtc")
        if (
            kickoff
            and match.get("status") in LIVE_STATES
            and -900 <= now - kickoff <= 21600
        ):
            return 60
    starts = [
        m["kickoffUtc"]
        for m in matches
        if m.get("status") == "scheduled" and m.get("kickoffUtc")
    ]
    if any(-10800 <= start - now <= 3600 for start in starts):
        return 120
    next_checks = [start - now - 3600 for start in starts if start > now + 3600]
    return int(min(21600, max(60, min(next_checks)))) if next_checks else 21600
