"""Anonymous live feed, season discovery and conservative provisional scoring.

Descriptor decoding adapted from Andrea Grillo (2023), Apache-2.0;
see third_party/fantacalcio-live-NOTICE.md. No Node runtime or login required.
"""

from copy import deepcopy
import json
import math
import os
from pathlib import Path
import re
import struct
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from fantacalcio_core import (
    BASE,
    SOURCE,
    Client,
    grade,
    page_key,
    presentation,
    validate,
)
from sport_core import ProviderError, club_id

ROOT = "https://api.fantacalcio.it/v1"
SIGN = "https://www.fantacalcio.it/api/v1/SignedUri"
DESCRIPTOR = "https://www.fantacalcio.it/js/proto/live.txt"
# Field names/types are checked against the provider descriptor before downloading.
PLAYER = [
    ("id", "uint32"),
    ("name", "string"),
    ("position", "string"),
    ("vote", "double"),
    ("events", "int32", True),
    ("eventsMinutes", "int32", True),
    ("stampId", "int32"),
    ("index", "uint32"),
    ("substitutionId", "uint32"),
]
MATCH = [
    ("matchId", "uint32"),
    ("stampMatch", "int32"),
    ("teamIdHome", "uint32"),
    ("teamIdAway", "uint32"),
    ("goalHome", "uint32"),
    ("goalAway", "uint32"),
    ("fhDate", "uint64"),
    ("shDate", "uint64"),
    ("matchDate", "uint64"),
    ("status", "uint32"),
    ("trendHome", "string"),
    ("trendAway", "string"),
    ("teamHome", "string"),
    ("teamAway", "string"),
    ("playersHome", "Player", True),
    ("playersAway", "Player", True),
]
SCHEMAS = {
    "LiveMessage": [("protoData", "Protodata", True)],
    "Player": PLAYER,
    "Protodata": MATCH,
}


def check_descriptor(encoded):
    seed, chars = 98, []
    for char in encoded:
        if char == "\r":
            continue
        x = math.sin(seed) * 10000
        chars.append(chr(ord(char) - (math.floor((x - math.floor(x)) * 2) - 1)))
        seed += 1
    descriptor = json.loads("".join(chars))["nested"]["LiveMessage"]
    for name, fields in SCHEMAS.items():
        actual = (descriptor if name == "LiveMessage" else descriptor["nested"][name])[
            "fields"
        ]
        expected = {
            f[0]: dict(id=i, type=f[1], **({"rule": "repeated"} if len(f) == 3 else {}))
            for i, f in enumerate(fields, 1)
        }
        if actual != expected:
            raise ValueError("Schema live Fantacalcio cambiato")


def varint(data, offset):
    value = 0
    for shift in range(0, 70, 7):
        if offset >= len(data):
            raise ValueError("Protobuf troncato")
        byte = data[offset]
        offset += 1
        value |= (byte & 127) << shift
        if not byte & 128:
            if value >= 1 << 64:
                raise ValueError("Intero protobuf troppo grande")
            return value, offset
    raise ValueError("Varint protobuf troppo lungo")


def decode_message(data, name="LiveMessage"):
    """Bounded decoder for the three verified provider message types only."""
    if len(data) > 1_000_000:
        raise ValueError("Feed troppo grande")
    fields, result, offset, count = SCHEMAS[name], {}, 0, 0
    while offset < len(data):
        count += 1
        if count > 10000:
            raise ValueError("Troppi campi protobuf")
        tag, offset = varint(data, offset)
        field, wire = tag >> 3, tag & 7
        if not field:
            raise ValueError("Campo protobuf nullo")
        if wire == 0:
            raw, offset = varint(data, offset)
        elif wire in (1, 2, 5):
            size, offset = (
                varint(data, offset) if wire == 2 else (8 if wire == 1 else 4, offset)
            )
            end = offset + size
            if end > len(data):
                raise ValueError("Campo protobuf troncato")
            raw, offset = data[offset:end], end
        else:
            raise ValueError("Wire type protobuf non supportato")
        if field > len(fields):
            continue  # Forward-compatible unknown fields never become votes.
        spec = fields[field - 1]
        key, kind = spec[:2]
        repeated = len(spec) == 3
        wanted = (
            1 if kind == "double" else 2 if kind == "string" or kind in SCHEMAS else 0
        )
        if repeated and wanted == 0 and wire == 2:
            items, at = [], 0
            while at < len(raw):
                value, at = varint(raw, at)
                items.append(value)
                if len(items) > 100:
                    raise ValueError("Troppi eventi live")
        else:
            if wire != wanted:
                raise ValueError("Tipo campo live cambiato")
            if kind in SCHEMAS:
                value = decode_message(raw, kind)
            elif kind == "string":
                value = raw.decode("utf-8")
                if len(value) > 200:
                    raise ValueError("Testo live troppo lungo")
            elif kind == "double":
                value = struct.unpack("<d", raw)[0]
            else:
                value = raw
            items = [value]
        if kind == "int32":
            items = [
                (v & 0xFFFFFFFF) - (1 << 32) if v & (1 << 31) else v for v in items
            ]
        if kind == "uint32" and any(v > 0xFFFFFFFF for v in items):
            raise ValueError("Intero live fuori intervallo")
        if repeated:
            result.setdefault(key, []).extend(items)
            limit = 20 if name == "LiveMessage" else 40 if kind == "Player" else 100
            if len(result[key]) > limit:
                raise ValueError("Lista live troppo grande")
        elif key in result:
            raise ValueError("Campo live duplicato")
        else:
            result[key] = items[0]
    return result


def live_window(match, now=None):
    now = time.time() if now is None else now
    kickoff = match.get("kickoffUtc") or 0
    delta = now - kickoff
    status = match.get("status")
    return bool(page_key(match)) and (
        status in ("live", "half_time")
        and -900 <= delta <= 4 * 3600
        or status == "scheduled"
        and -900 <= delta <= 0
        or status == "finished"
        and 0 <= delta <= 3 * 3600
    )


def estimated_fantavote(vote, events):
    """Common classic bonuses; ambiguous/variant events yield missing FV.

    This is explicitly a calculated estimate, never the published fantasy grade.
    Penalty+goal duplicates, canceled goals and assist variants are withheld.
    """
    bonuses = {1: -0.5, 2: -1, 3: 3, 4: -1, 7: 3, 8: -3, 9: 3, 10: -2, 22: 1}
    neutral = {11, 12, 14, 15, 17, 26, 1015, 1017}
    if vote is None or any(e not in bonuses and e not in neutral for e in events):
        return None
    if (1 in events and 2 in events) or (3 in events and 9 in events):
        return None
    value = vote + sum(bonuses.get(e, 0) for e in events)
    return value if -20 <= value <= 50 else None


def normalize_live(decoded, key, acquired):
    teams = []
    for match in decoded.get("protoData", []):
        home, away = club_id(match.get("teamHome", "")), club_id(
            match.get("teamAway", "")
        )
        if not home or not away or home == away or not match.get("matchId"):
            raise ValueError("Identità incontro live mancante")
        kickoff = match.get("matchDate", 0) / 1000
        for side, team in (("Home", home), ("Away", away)):
            players = []
            for p in match.get("players" + side, []):
                if p.get("position") == "ALL":
                    continue
                raw = p.get("vote")
                if raw is None or raw in (0, 55, 56):
                    vote, label = None, "—"
                else:
                    # Encoded tens are supported except documented placeholders.
                    vote, label = grade(
                        str(raw / 10 if 30 < raw <= 100 else raw), base=True
                    )
                events = p.get("events", [])
                fv = estimated_fantavote(vote, events)
                players.append(
                    dict(
                        id=str(p.get("id", "")),
                        name=p.get("name", ""),
                        role=p.get("position", ""),
                        vote=vote,
                        voteText=label,
                        fantavote=fv,
                        fantavoteText=grade(str(fv))[1] if fv is not None else "—",
                        subIn=15 in events,
                        subOut=14 in events,
                    )
                )
            teams.append(
                dict(
                    teamId=team,
                    homeTeamId=home,
                    awayTeamId=away,
                    kickoffUtc=kickoff,
                    players=players,
                )
            )
    page = dict(
        key=key,
        source=SOURCE,
        url=BASE + key,
        fetchedAt=acquired,
        teams=teams,
        provisional=True,
    )
    validate(page)
    return page


class LiveClient:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.seasons = self._load_seasons()
        self.pages = {}
        self.cooldowns = {}
        self.descriptor_ok = False
        self.requests = 0

    def _load_seasons(self):
        try:
            path = self.directory / "fantacalcio-seasons.json"
            if path.stat().st_size > 16000:
                return {}
            data = json.loads(path.read_text())
            if data.get("schemaVersion") != 1:
                return {}
            return {
                s: i
                for s, i in data["seasons"].items()
                if re.fullmatch(r"\d{4}-\d{2}", s) and type(i) is int and 0 < i < 1000
            }
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return {}

    def _request(self, url, payload=None):
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode() if payload else None,
            headers={
                "User-Agent": "SmartPC-Dashboard/0.6",
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
            },
        )
        self.requests += 1
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                data = response.read(4_000_001)
                if len(data) > 4_000_000:
                    raise ProviderError("Risposta live troppo grande")
                age = float(response.headers.get("Age", "0"))
                if not math.isfinite(age) or age < 0:
                    raise ValueError("Età feed errata")
                return data, time.time() - age
        except urllib.error.HTTPError as error:
            raise ProviderError(
                "Live Fantacalcio HTTP " + str(error.code),
                http_status=error.code,
                retry_after=120,
            ) from error

    def season_id(self, key):
        if not re.fullmatch(r"\d{4}-\d{2}/(?:[1-9]|[12]\d|3[0-8])", key):
            raise ValueError("Stagione/giornata errata")
        season, week = key.split("/")
        if season in self.seasons:
            return self.seasons[season]
        html = self._request(BASE + key)[0].decode()
        # Verify the requested archive rather than silently accepting a redirect.
        from fantacalcio_core import PageParser

        parser = PageParser()
        parser.feed(html)
        if not any(
            n.attrs.get("property") == "og:url"
            and n.attrs.get("content", "").rstrip("/") == BASE + key
            for n in parser.root.all("meta")
        ):
            raise ValueError("Stagione Fantacalcio non confermata")
        ids = {
            int(m[1])
            for n in parser.root.all("a")
            if (
                m := re.search(
                    r"/api/v1/Excel/votes/(\d+)/" + week + r"$", n.attrs.get("href", "")
                )
            )
        }
        if len(ids) != 1 or not 0 < next(iter(ids)) < 1000:
            raise ValueError("Identificativo stagione non trovato")
        seasons = dict(self.seasons, **{season: ids.pop()})
        self.directory.mkdir(parents=True, exist_ok=True)
        name = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", dir=self.directory, prefix="fanta-seasons-", delete=False
            ) as stream:
                name = stream.name
                json.dump(dict(schemaVersion=1, seasons=seasons), stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.directory / "fantacalcio-seasons.json")
        finally:
            if name and os.path.exists(name):
                os.unlink(name)
        self.seasons = seasons
        return seasons[season]

    def get(self, key):
        now = time.time()
        if key in self.pages and now - self.pages[key]["fetchedAt"] < 30:
            return deepcopy(self.pages[key])
        cooldown, status = self.cooldowns.get(key, (0, 0))
        if cooldown > now:
            raise ProviderError(
                "Feed live momentaneamente non disponibile",
                retry_after=120,
                http_status=status,
            )
        try:
            season = self.season_id(key)
            resource = f"{ROOT}/st/{season}/matches/live/{key.split('/')[1]}.dat"
            response = json.loads(self._request(SIGN, {"resourcesUri": [resource]})[0])
            entry = (
                next(iter(response.values()))
                if isinstance(response, dict) and len(response) == 1
                else None
            )
            if not isinstance(entry, dict):
                raise ValueError("Firma live non riconosciuta")
            if entry.get("errors"):
                code = entry["errors"][0].get("statusCode", 0)
                raise ProviderError(
                    (
                        "Risorsa live non disponibile"
                        if code == 404
                        else "Accesso feed live non riuscito"
                    ),
                    http_status=code,
                    retry_after=120,
                )
            signed = entry["resources"][0]["signedUri"]
            # Signed tokens remain in this worker only: never cache/log them.
            uri = urllib.parse.urlsplit(signed)
            if (
                uri.scheme != "https"
                or uri.hostname != "api.fantacalcio.it"
                or uri.path != urllib.parse.urlsplit(resource).path
            ):
                raise ValueError("URL firmato live inatteso")
            if not self.descriptor_ok:
                check_descriptor(self._request(DESCRIPTOR)[0].decode())
                self.descriptor_ok = True
            body, acquired = self._request(signed)
            if now - acquired > 120:
                raise ValueError("Feed live scaduto")
            page = normalize_live(decode_message(body), key, acquired)
            self.pages = {key: page}
            return deepcopy(page)
        except (
            OSError,
            ValueError,
            KeyError,
            IndexError,
            TypeError,
            ProviderError,
        ) as error:
            self.cooldowns[key] = (
                time.time() + max(120, getattr(error, "retry_after", 0)),
                getattr(error, "http_status", 0),
            )
            raise ProviderError(
                "Feed live non disponibile",
                http_status=getattr(error, "http_status", 0),
                retry_after=120,
            ) from error


class FantasyClient(Client):
    """Published pages retain their durable history; live samples stay in RAM."""

    def __init__(self, directory):
        super().__init__()
        self.live = LiveClient(directory)

    def get_for_match(self, key, ttl, match):
        live_error = None
        if live_window(match):
            # Published grades always take precedence for a completed match.
            if match.get("status") == "finished":
                try:
                    page = self.get(key, 300)
                    data = presentation(page, match)
                    if data.get("matched") and data.get("published"):
                        return page
                except ProviderError:
                    pass
            try:
                page = self.live.get(key)
                if not presentation(page, match).get("matched"):
                    raise ValueError("Partita assente nel feed live")
                return page
            except (ProviderError, ValueError) as error:
                live_error = error
        page = self.get(key, max(ttl, 300) if live_window(match) else ttl)
        if live_error:
            page["liveNotice"] = (
                "Accesso live rifiutato · mostro i voti pubblicati disponibili"
                if getattr(live_error, "http_status", 0) in (401, 403)
                else "Feed live in attesa · mostro i voti pubblicati disponibili"
            )
        return page
