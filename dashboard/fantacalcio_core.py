"""Public Redazione Fantacalcio grades; source identity and Serie A only."""

from copy import deepcopy
from datetime import datetime
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
from sport_core import ROME, ProviderError, club_id, mapping, number, text

SOURCE = "Redazione Fantacalcio"
BASE = "https://www.fantacalcio.it/voti-fantacalcio-serie-a/"


def eligible(match):
    return (
        match.get("competitionId") == "serie_a"
        or match.get("competitionId") == "football:55"
        and match.get("providerLeagueId") == 55
    )


def page_key(match):
    season, week = match.get("season", ""), number(match.get("round"))
    if (
        not eligible(match)
        or not re.fullmatch(r"\d{4}/\d{4}", season)
        or week is None
        or not 1 <= week <= 38
    ):
        return ""
    a, b = map(int, season.split("/"))
    return f"{a}-{b%100:02}/{week}" if b == a + 1 else ""


class Node:
    def __init__(self, tag="", attrs=()):
        self.tag, self.attrs, self.children, self.parts = tag, dict(attrs), [], []

    def has(self, value):
        return value in self.attrs.get("class", "").split()

    def all(self, tag=None, cls=None):
        for child in self.children:
            if (tag is None or child.tag == tag) and (cls is None or child.has(cls)):
                yield child
            yield from child.all(tag, cls)

    def first(self, tag=None, cls=None):
        return next(self.all(tag, cls), Node())

    def value(self):
        return " ".join(" ".join(self.parts).split())


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in (
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        ):
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                break

    def handle_data(self, value):
        # No scripts are executed or needed by this adapter.
        if self.stack[-1].tag not in ("script", "style"):
            for node in self.stack:
                node.parts.append(value)


def grade(value, *, base=False):
    token = text(value, 20).lower().replace(",", ".")
    if token in ("sv", "s.v.", "s.v", "s/v"):
        return None, "SV"
    if token in ("", "-", "--", "—", "55", "56"):
        return None, "—"  # Provider placeholders, never numeric votes.
    if not re.fullmatch(r"-?\d+(?:\.\d+)?\*?", token):
        raise ValueError("Formato voto Fantacalcio non riconosciuto")
    result = float(token.rstrip("*"))
    if not math.isfinite(result) or not (
        0 <= result <= 10 if base else -20 <= result <= 50
    ):
        raise ValueError("Voto Fantacalcio fuori intervallo")
    return result, f"{result:g}".replace(".", ",") + (
        "*" if token.endswith("*") else ""
    )


def parse_page(html, key, acquired):
    if len(html) > 4_000_000:
        raise ValueError("Pagina voti troppo grande")
    parser = PageParser()
    parser.feed(html)
    root = parser.root
    url = BASE + key
    if not any(
        n.attrs.get("property") == "og:url"
        and n.attrs.get("content", "").rstrip("/") == url
        for n in root.all("meta")
    ):
        raise ValueError("Stagione/giornata Fantacalcio diversa dalla richiesta")
    teams = []
    for block in root.all("li", "team-table"):
        table = block.first("table", "grades-table")
        team = club_id(table.first("a", "team-name").value())
        spans = list(block.first("div", "match-score").all("span"))
        if not team or len(spans) != 5:
            raise ValueError("Identità tabellino Fantacalcio assente")
        home, away = club_id(spans[0].value()), club_id(spans[4].value())
        if home == away or team not in (home, away):
            raise ValueError("Squadre del tabellino errate")
        date_text = block.first("div", "match-date").value()
        kickoff = (
            datetime.strptime(date_text, "%d/%m/%Y - %H:%M")
            .replace(tzinfo=ROME)
            .timestamp()
        )
        headers = [
            g
            for g in table.first("thead").all("div", "group")
            if len(list(g.all("img"))) > 1
        ]
        if len(headers) != 1:
            raise ValueError("Intestazioni fonti voto non riconosciute")
        titles = [i.attrs.get("title", "") for i in headers[0].all("img")]
        if titles.count(SOURCE) != 1:
            raise ValueError("Redazione Fantacalcio non identificata")
        editorial = titles.index(SOURCE)
        players = []
        for row in table.first("tbody").all("tr"):
            link = row.first("a", "player-link")
            if not link.attrs:
                continue  # Coaches are not footballers.
            pid = link.attrs.get("href", "").rstrip("/").rsplit("/", 1)[-1]
            if not pid.isdigit():
                raise ValueError("Identità calciatore Fantacalcio errata")
            cells = [n for n in row.children if n.tag == "td"]
            pills = list(cells[1].all("div", "pill")) if len(cells) > 1 else []
            if len(pills) != len(titles):
                raise ValueError("Colonne voto non riconosciute")
            pill = pills[editorial]
            base = pill.first("span", "player-grade")
            fantasy = pill.first("span", "player-fanta-grade")
            if not base.attrs or not fantasy.attrs:
                raise ValueError("Colonne voto mancanti")
            vote, vote_label = grade(base.attrs.get("data-value"), base=True)
            fv, fv_label = grade(fantasy.attrs.get("data-value"))
            subs = [i.attrs.get("title", "") for i in row.all("img", "player-icon")]
            players.append(
                {
                    "id": pid,
                    "name": text(link.value()),
                    "role": text(
                        row.first("span", "role").attrs.get("data-value")
                    ).upper(),
                    "vote": vote,
                    "fantavote": fv,
                    "voteText": vote_label,
                    "fantavoteText": fv_label,
                    "subIn": "Subentrato" in subs,
                    "subOut": "Sostituito" in subs,
                }
            )
        teams.append(
            {
                "teamId": team,
                "homeTeamId": home,
                "awayTeamId": away,
                "kickoffUtc": kickoff,
                "players": players,
            }
        )
    page = {
        "key": key,
        "source": SOURCE,
        "url": url,
        "fetchedAt": acquired,
        "teams": teams,
    }
    validate(page)
    return page


def validate(page):
    if (
        page.get("source") != SOURCE
        or not re.fullmatch(r"\d{4}-\d{2}/(?:[1-9]|[12]\d|3[0-8])", page.get("key", ""))
        or page.get("url") != BASE + page["key"]
    ):
        raise ValueError("Fonte cache Fantacalcio errata")
    at = page.get("fetchedAt")
    teams = page.get("teams")
    if (
        type(at) not in (float, int)
        or not math.isfinite(at)
        or not 0 < at <= time.time() + 300
        or not isinstance(teams, list)
        or len(teams) > 20
    ):
        raise ValueError("Cache Fantacalcio non valida")
    seen = set()
    for team in teams:
        identity = (
            team["teamId"],
            team["homeTeamId"],
            team["awayTeamId"],
            team["kickoffUtc"],
        )
        if (
            identity in seen
            or team["teamId"] not in (team["homeTeamId"], team["awayTeamId"])
            or team["homeTeamId"] == team["awayTeamId"]
        ):
            raise ValueError("Identità squadra Fantacalcio errata")
        seen.add(identity)
        if (
            type(team["kickoffUtc"]) not in (float, int)
            or not math.isfinite(team["kickoffUtc"])
            or team["kickoffUtc"] <= 0
            or not isinstance(team.get("players"), list)
            or len(team["players"]) > 40
        ):
            raise ValueError("Rosa Fantacalcio errata")
        players = set()
        for p in team["players"]:
            if not str(p["id"]).isdigit() or p["id"] in players or not text(p["name"]):
                raise ValueError("Identità calciatore duplicata")
            players.add(p["id"])
            for k, limits in [("vote", (0, 10)), ("fantavote", (-20, 50))]:
                v = p[k]
                if v is not None and (
                    type(v) not in (int, float)
                    or not math.isfinite(v)
                    or not limits[0] <= v <= limits[1]
                ):
                    raise ValueError("Voto cache non valido")


def read_cache(path, key):
    try:
        if Path(path).stat().st_size > 500_000:
            return None
        envelope = json.loads(Path(path).read_text())
        page = envelope["page"]
        if envelope.get("schemaVersion") != 1 or page.get("key") != key:
            return None
        validate(page)
        return page
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def save_cache(path, page):
    validate(page)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=path.parent, prefix="fanta-", suffix=".tmp", delete=False
        ) as stream:
            name = stream.name
            json.dump(
                {"schemaVersion": 1, "page": page},
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


class Client:
    def __init__(self):
        self.pages = {}
        self.requests = 0

    def get(self, key, ttl=300):
        if key in self.pages and time.time() - self.pages[key]["fetchedAt"] < ttl:
            return deepcopy(self.pages[key])
        request = urllib.request.Request(
            BASE + key,
            headers={"Accept": "text/html", "User-Agent": "SmartPC-Dashboard/0.6"},
        )
        self.requests += 1
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                body = response.read(4_000_001)
                if len(body) > 4_000_000:
                    raise ProviderError("Pagina Fantacalcio troppo grande")
                age = number(response.headers.get("Age")) or 0
                page = parse_page(body.decode("utf-8"), key, time.time() - age)
            self.pages[key] = page
            if len(self.pages) > 4:
                self.pages.pop(next(iter(self.pages)))
            return deepcopy(page)
        except urllib.error.HTTPError as error:
            raise ProviderError(
                "Fantacalcio HTTP " + str(error.code),
                http_status=error.code,
                retry_after=number(error.headers.get("Retry-After")) or 0,
            ) from error
        except (OSError, ValueError, UnicodeError) as error:
            raise ProviderError("Voti Fantacalcio non disponibili") from error


def normalized(value):
    return re.sub(
        r"[^a-z0-9]",
        "",
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower(),
    )


def aliases(player):
    first, last = text(player.get("firstName")), text(player.get("lastName"))
    values = {normalized(text(player.get("name")))}
    if last:
        values.add(normalized(last))
        for size in (1, 2, 3):
            values.add(normalized(last + first[:size]))
        values.add(normalized(last + "".join(p[0] for p in first.split() if p)))
    return values - {""}


def presentation(page, match):
    result = {
        "eligible": eligible(match),
        "teams": [],
        "published": False,
        "warning": "",
    }
    if not result["eligible"]:
        return result
    key = page_key(match)
    kickoff = match.get("kickoffUtc")
    selected = []
    if page and page.get("key") == key and kickoff:
        selected = [
            t
            for t in page["teams"]
            if (t["homeTeamId"], t["awayTeamId"])
            == (match.get("homeTeamId"), match.get("awayTeamId"))
            and abs(t["kickoffUtc"] - kickoff) <= 1800
        ]
    for side in ("home", "away"):
        roster = next(
            (l for l in match.get("lineups", []) if l.get("side") == side), {}
        )
        source = next(
            (t for t in selected if t["teamId"] == match.get(side + "TeamId")), None
        )
        votes = source["players"] if source else []
        squad = roster.get("squad", [])
        players = []
        used = set()
        for player in squad:
            matches = [v for v in votes if normalized(v["name"]) in aliases(player)]
            # A name must also uniquely identify one player in this team.
            vote = (
                matches[0]
                if len(matches) == 1
                and sum(normalized(matches[0]["name"]) in aliases(p) for p in squad)
                == 1
                else None
            )
            if vote and vote["id"] in used:
                vote = None
            if vote:
                used.add(vote["id"])
            row = dict(
                player,
                vote=vote.get("vote") if vote else None,
                fantavote=vote.get("fantavote") if vote else None,
                voteText=vote.get("voteText", "—") if vote else "—",
                fantavoteText=vote.get("fantavoteText", "—") if vote else "—",
                group=(
                    "Titolari"
                    if player.get("starter")
                    else "Subentrati" if player.get("subIn") else "Panchina"
                ),
                role=(
                    vote.get("role") or player.get("role", "")
                    if vote
                    else player.get("role", "")
                ),
                ratingSource=SOURCE if vote else "",
            )
            players.append(row)
        for vote in votes:
            if vote["id"] not in used:
                row = dict(
                    vote,
                    group=(
                        "Voti fonte"
                        if squad
                        else "Subentrati" if vote["subIn"] else "Titolari"
                    ),
                    ratingSource=SOURCE,
                )
                players.append(row)
                if squad:
                    result["warning"] = (
                        "Nomi non abbinati: voti mostrati separatamente."
                    )
        order = {"Titolari": 0, "Subentrati": 1, "Panchina": 2, "Voti fonte": 3}
        players.sort(key=lambda p: order[p["group"]])
        result["teams"].append(
            {
                "side": side,
                "name": match.get(side + "Team", ""),
                "formation": roster.get("formation", ""),
                "players": players,
            }
        )
    result["published"] = any(
        p.get("vote") is not None
        or p.get("fantavote") is not None
        or p.get("voteText") == "SV"
        for t in result["teams"]
        for p in t["players"]
    )
    result["matched"] = len(selected) == 2
    return result
