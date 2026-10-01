"""Serie A adapters, validated persistent snapshots and event policy (no Qt).

Provider IDs remain separate from canonical identities. Missing data stays None.
Network/JSON work is called by the Qt worker, never by QML.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import logging
import math
import os
from pathlib import Path
import re
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROME = ZoneInfo('Europe/Rome')
CACHE_VERSION = 1
LIVE_STATES = ('live', 'half_time')
MATCH_STATES = (*LIVE_STATES, 'scheduled', 'finished', 'postponed', 'cancelled', 'unknown')
FOTMOB = 'https://www.fotmob.com/api/data/'
ESPN = 'https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/'


@dataclass(frozen=True)
class Competition:
    id: str
    name: str
    fotmob_id: int
    espn_id: str
    expected_teams: int


COMPETITIONS = {'serie_a': Competition('serie_a', 'Serie A', 55, 'ita.1', 20)}


def season_for(now: float) -> str:
    date = datetime.fromtimestamp(now, ROME)
    year = date.year if date.month >= 7 else date.year - 1
    return f'{year}/{year + 1}'


def text(value, limit=100) -> str:
    return str(value or '').strip()[:limit]


def mapping(value) -> dict:
    """Optional provider objects may explicitly be JSON null."""
    return value if isinstance(value, dict) else {}


def items(value) -> list:
    return value if isinstance(value, list) else []


def number(value, *, signed=False):
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
        if not math.isfinite(result) or result != int(result) or (not signed and result < 0):
            return None
        return int(result)
    except (ValueError, TypeError, OverflowError):
        return None


def timestamp(value):
    if type(value) in (int, float):
        return float(value) if math.isfinite(value) and value > 0 else None
    if not isinstance(value, str):
        return None
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return date.timestamp() if date.tzinfo else None
    except ValueError:
        return None


def club_id(name: str) -> str:
    plain = unicodedata.normalize('NFKD', text(name)).encode('ascii', 'ignore').decode().lower()
    slug = re.sub(r'[^a-z0-9]+', '_', plain).strip('_')
    return {'internazionale': 'inter', 'inter_milan': 'inter', 'fc_internazionale_milano': 'inter',
            'ac_milan': 'milan', 'as_roma': 'roma', 'ss_lazio': 'lazio', 'verona': 'hellas_verona',
            'hellas_verona_fc': 'hellas_verona', 'juventus_fc': 'juventus'}.get(slug, slug)


def fotmob_status(status: dict, ongoing=None) -> str:
    reason = text(mapping(status.get('reason')).get('short')).upper()
    reason_key = text(mapping(status.get('reason')).get('shortKey')).lower()
    if reason in ('PP', 'P-P', 'POSTPONED') or 'postpon' in reason_key:
        return 'postponed'
    if status.get('cancelled') is True:
        return 'cancelled' if reason in ('CANC', 'CANCELLED') or 'cancel' in reason_key else 'unknown'
    if status.get('finished') is True:
        return 'finished'
    if reason == 'HT':
        return 'half_time'
    if reason in ('SUSP', 'ABANDONED', 'ABD') or 'suspend' in reason_key or 'abandon' in reason_key:
        return 'unknown'
    if status.get('started') is True and ongoing is not False:
        return 'live'
    if status.get('started') is False:
        return 'scheduled'
    return 'unknown'


def espn_status(status: dict) -> str:
    kind = mapping(status.get('type'))
    name = kind.get('name', '')
    explicit = {'STATUS_POSTPONED': 'postponed', 'STATUS_CANCELED': 'cancelled',
                'STATUS_CANCELLED': 'cancelled', 'STATUS_HALFTIME': 'half_time',
                'STATUS_SUSPENDED': 'unknown', 'STATUS_ABANDONED': 'unknown'}
    if name in explicit:
        return explicit[name]
    if kind.get('completed') is True and kind.get('state') == 'post':
        return 'finished'
    if kind.get('state') == 'in':
        return 'live'
    if kind.get('state') == 'pre':
        return 'scheduled'
    return 'unknown'


def make_match(home, away, *, provider, provider_id, season, kickoff, status, scores, round_name='', minute='', raw=None):
    home_name, away_name = text(home.get('name')), text(away.get('name'))
    hid, aid = club_id(home_name), club_id(away_name)
    if not hid or not aid or hid == aid or not provider_id:
        raise ValueError('Identità partita non valida')
    if status not in MATCH_STATES:
        raise ValueError('Stato partita non valido')
    score = [number(v) for v in scores] if status in (*LIVE_STATES, 'finished') else [None, None]
    if len(score) != 2 or any(v is not None and v > 99 for v in score):
        raise ValueError('Punteggio non valido')
    return {'sport': 'football', 'competitionId': 'serie_a', 'season': season,
            'canonicalMatchId': f'serie_a:{season}:{hid}:{aid}', 'provider': provider,
            'providerMatchId': str(provider_id), 'homeTeamId': hid, 'awayTeamId': aid,
            'homeProviderId': str(home.get('id', '')), 'awayProviderId': str(away.get('id', '')),
            'homeTeam': home_name, 'awayTeam': away_name, 'kickoffUtc': kickoff,
            'round': text(round_name, 40), 'status': status, 'rawStatus': raw or {},
            'homeScore': score[0], 'awayScore': score[1], 'minute': text(minute, 30),
            'venue': '', 'events': [], 'stats': [], 'lineups': [], 'pendingVAR': None,
            'sourceDataAt': None, 'fetchedAt': 0, 'dataChangedAt': 0}


def parse_fotmob_fixture(raw: dict, season: str) -> dict:
    status = raw.get('status', {})
    score = re.fullmatch(r'\s*(\d+)\s*[-–]\s*(\d+)\s*', text(status.get('scoreStr')))
    return make_match(raw.get('home', {}), raw.get('away', {}), provider='fotmob',
                      provider_id=raw.get('id'), season=season, kickoff=timestamp(status.get('utcTime')),
                      status=fotmob_status(status), scores=score.groups() if score else [None, None],
                      round_name=raw.get('round', raw.get('roundName', '')),
                      minute=status.get('liveTime', {}).get('short', '') if isinstance(status.get('liveTime'), dict) else '', raw=status)


def parse_espn_event(raw: dict, season: str) -> dict:
    competitions = raw.get('competitions', [])
    if len(competitions) != 1:
        raise ValueError('Competizione ESPN non valida')
    competition = competitions[0]
    sides = {c.get('homeAway'): c for c in competition.get('competitors', [])}
    if set(sides) != {'home', 'away'}:
        raise ValueError('Squadre ESPN non valide')
    home, away = sides['home'], sides['away']
    status = competition.get('status', raw.get('status', {}))
    match = make_match({'name': home['team']['displayName'], 'id': home['team']['id']},
                       {'name': away['team']['displayName'], 'id': away['team']['id']},
                       provider='espn', provider_id=raw.get('id'), season=season,
                       kickoff=timestamp(competition.get('date', raw.get('date'))) if competition.get('timeValid', True) else None,
                       status=espn_status(status), scores=[home.get('score'), away.get('score')],
                       minute=status.get('displayClock', ''), raw=status)
    match['venue'] = text(mapping(competition.get('venue')).get('fullName'))
    return match


def parse_fotmob_league(raw: dict, season: str) -> dict:
    details = raw.get('details', {})
    if details.get('id') != 55 or details.get('selectedSeason') != season:
        raise ValueError('Campionato o stagione FotMob errati')
    fixtures = raw.get('fixtures', {}).get('allMatches')
    if not isinstance(fixtures, list) or not fixtures or len(fixtures) > 600:
        raise ValueError('Calendario FotMob incompleto')
    matches = [parse_fotmob_fixture(item, season) for item in fixtures]
    tables = raw.get('table', [])
    rows = [row for table in tables for row in table.get('data', {}).get('table', {}).get('all', [])]
    standings = [{'teamId': club_id(row.get('name')), 'team': text(row.get('name')),
                  'position': number(row.get('idx')), 'played': number(row.get('played')),
                  'points': number(row.get('pts')), 'goalDifference': number(row.get('goalConDiff'), signed=True)} for row in rows]
    snapshot = {'competitionId': 'serie_a', 'competitionName': 'Serie A', 'season': season,
                'provider': 'fotmob', 'calendarScope': 'season', 'fixtures': matches,
                'standings': standings, 'fetchedAt': 0, 'standingsFetchedAt': 0}
    validate_snapshot(snapshot, require_time=False)
    return snapshot


def parse_espn_standings(raw: dict, season: str) -> list:
    rows = []
    for child in raw.get('children', []):
        table = child.get('standings', {})
        if str(table.get('season')) != season.split('/')[0]:
            raise ValueError('Stagione classifica ESPN errata')
        for row in table.get('entries', []):
            stats = {stat.get('name'): stat.get('value') for stat in row.get('stats', [])}
            name = row.get('team', {}).get('displayName', '')
            rows.append({'teamId': club_id(name), 'team': text(name), 'position': number(stats.get('rank')),
                         'played': number(stats.get('gamesPlayed')), 'points': number(stats.get('points')),
                         'goalDifference': number(stats.get('pointDifferential'), signed=True)})
    if len(rows) != 20:
        raise ValueError('Classifica ESPN incompleta')
    return sorted(rows, key=lambda row: row['position'] or 99)


def lineup_squad(team):
    squad = []
    for group, starter in [('starters', True), ('subs', False)]:
        for value in items(team.get(group))[:30]:
            player = mapping(value)
            if not text(player.get('name')): continue
            substitutions = items(mapping(player.get('performance')).get('substitutionEvents'))
            entered = next((s for s in substitutions if mapping(s).get('type') == 'subIn'), {})
            exited = next((s for s in substitutions if mapping(s).get('type') == 'subOut'), {})
            squad.append({'id': str(player.get('id', '')), 'name': text(player.get('name')), 'firstName': text(player.get('firstName')),
                          'lastName': text(player.get('lastName')), 'shirtNumber': number(player.get('shirtNumber')), 'starter': starter,
                          'role': {0:'P',1:'D',2:'C',3:'A'}.get(number(player.get('usualPlayingPositionId')), ''),
                          'subIn': bool(entered), 'subOut': bool(exited), 'inMinute': number(entered.get('time')), 'outMinute': number(exited.get('time'))})
    return squad


def fotmob_detail(raw: dict, original: dict) -> dict:
    general = mapping(raw.get('general'))
    league_ids = [general.get('leagueId')]
    if original.get('competitionId', '').startswith('football:'):
        league_ids.append(general.get('parentLeagueId'))
    if str(general.get('matchId')) != original['providerMatchId'] or original.get('providerLeagueId', 55) not in league_ids:
        raise ValueError('Dettaglio FotMob di un altro incontro')
    header = mapping(raw.get('header'))
    teams = items(header.get('teams'))
    team_identity = [str(mapping(t).get('id')) for t in teams] if original.get('competitionId', '').startswith('football:') else [club_id(mapping(t).get('name')) for t in teams]
    expected = [original['homeProviderId'], original['awayProviderId']] if original.get('competitionId', '').startswith('football:') else [original['homeTeamId'], original['awayTeamId']]
    if len(teams) != 2 or team_identity != expected:
        raise ValueError('Identità dettaglio FotMob errata')
    result = deepcopy(original)
    if original.get('competitionId') == 'serie_a' or original.get('providerLeagueId') == 55:
        match_round = number(general.get('matchRound'))
        if match_round is not None and 1 <= match_round <= 38:
            result['round'] = str(match_round)
    status = mapping(header.get('status'))
    result['events'], result['stats'], result['lineups'] = [], [], []
    result['status'] = fotmob_status(status, raw.get('ongoing'))
    result['rawStatus'] = status
    if 'utcTime' in status:
        prior_status = mapping(original.get('rawStatus')) if original.get('competitionId', '').startswith('football:') else {}
        tentative = status.get('matchDateTbd', prior_status.get('matchDateTbd')) is True or status.get('matchTimeTbd', prior_status.get('matchTimeTbd')) is True
        result['kickoffUtc'] = None if tentative else timestamp(status['utcTime'])
        if original.get('competitionId', '').startswith('football:'):
            result['dateTentative'] = tentative
            result['dateLabel'] = text(status.get('utcTime'))[:10] if status.get('matchDateTbd', prior_status.get('matchDateTbd')) is not True else ''
    if result['status'] in (*LIVE_STATES, 'finished'):
        result['homeScore'], result['awayScore'] = [number(t.get('score')) for t in teams]
    else:
        result['homeScore'] = result['awayScore'] = None
    result['pendingVAR'] = raw.get('hasPendingVAR') if isinstance(raw.get('hasPendingVAR'), bool) else None
    live_time = status.get('liveTime')
    result['minute'] = text(live_time.get('short', '') if isinstance(live_time, dict) else live_time, 30)
    events = mapping(header.get('events'))
    for side, key in [('home', 'homeTeamGoals'), ('away', 'awayTeamGoals')]:
        for goals in mapping(events.get(key)).values():
            for event in items(goals):
                event = mapping(event)
                if event.get('isPenaltyShootoutEvent') or not event.get('eventId'):
                    continue
                result['events'].append({'id': str(event['eventId']), 'type': 'goal', 'side': side,
                                         'player': text(event.get('fullName', event.get('nameStr'))),
                                         'minute': str(event.get('timeStr', '')) + (f"+{event['overloadTime']}" if event.get('overloadTime') else ''),
                                         'score': event.get('newScore'), 'confirmed': result['pendingVAR'] is False})
    content = mapping(raw.get('content'))
    keys = {'BallPossesion': 'Possesso', 'expected_goals': 'xG', 'ShotsOnTarget': 'Tiri in porta'}
    all_stats = mapping(mapping(mapping(content.get('stats')).get('Periods')).get('All'))
    for group in items(all_stats.get('stats')):
        for stat in items(mapping(group).get('stats')):
            stat = mapping(stat)
            values = items(stat.get('stats'))
            if stat.get('key') in keys and len(values) == 2 and all(type(v) in (str, float, int) for v in values):
                result['stats'].append({'label': keys[stat['key']], 'home': str(values[0]), 'away': str(values[1])})
    result['stats'] = list({row['label']: row for row in result['stats']}.values())
    lineup = mapping(content.get('lineup'))
    for side in ('home', 'away'):
        team = mapping(lineup.get(side + 'Team'))
        players = items(team.get('starters'))
        names = [text(mapping(p).get('name')) for p in players[:11]]
        if any(names):
            result['lineups'].append({'side': side, 'formation': text(team.get('formation'), 30),
                                      'players': names, 'squad': lineup_squad(team)})
    info = mapping(mapping(content.get('matchFacts')).get('infoBox'))
    if mapping(info.get('Match Date')).get('isDateCorrect') is False:
        result['kickoffUtc'] = None
    result['events'].sort(key=lambda event: tuple(int(part) for part in re.findall(r'\d+', event['minute'])) or (999,))
    stadium = info.get('Stadium')
    result['venue'] = text(stadium.get('name') if isinstance(stadium, dict) else stadium)
    return result


def espn_detail(raw: dict, original: dict) -> dict:
    header = mapping(raw.get('header'))
    event = dict(header, competitions=items(header.get('competitions')))
    result = parse_espn_event(event, original['season'])
    if result['providerMatchId'] != original['providerMatchId'] or result['canonicalMatchId'] != original['canonicalMatchId']:
        raise ValueError('Identità dettaglio ESPN errata')
    result['round'] = original.get('round', '')
    for event in items(raw.get('keyEvents')):
        event = mapping(event)
        if not event.get('scoringPlay') or event.get('shootout') or not event.get('id'):
            continue
        participants = items(event.get('participants'))
        result['events'].append({'id': str(event['id']), 'type': 'goal',
                                 'side': 'home' if str(mapping(event.get('team')).get('id')) == result['homeProviderId'] else 'away',
                                 'player': text(mapping(mapping(participants[0]).get('athlete')).get('displayName')) if participants else text(event.get('shortText')),
                                 'minute': text(mapping(event.get('clock')).get('displayValue'), 30),
                                 'confirmed': False, 'score': None})
    teams = items(mapping(raw.get('boxscore')).get('teams'))
    stats = {str(mapping(t.get('team')).get('id')): {s.get('name'): s.get('displayValue') for s in items(t.get('statistics')) if isinstance(s, dict)} for t in teams if isinstance(t, dict)}
    for key, label in [('possessionPct', 'Possesso'), ('shotsOnTarget', 'Tiri in porta')]:
        home = stats.get(result['homeProviderId'], {}).get(key)
        away = stats.get(result['awayProviderId'], {}).get(key)
        if home is not None and away is not None:
            result['stats'].append({'label': label, 'home': str(home), 'away': str(away)})
    return result


class ProviderError(Exception):
    def __init__(self, message, *, retry_after=0, http_status=0):
        super().__init__(message)
        self.retry_after = retry_after
        self.http_status = http_status


class HTTPClient:
    def __init__(self, *, allow_lists=False):
        self.allow_lists = allow_lists
        self.cache = {}
        self.cooldowns = {}
        self.request_count = {}

    def get(self, url: str) -> tuple[dict, float]:
        now = time.time()
        cooldown = self.cooldowns.get(url)
        if cooldown and cooldown[0] > now:
            raise ProviderError(cooldown[2], retry_after=cooldown[0]-now, http_status=cooldown[1])
        if url in self.cache and self.cache[url][0] > now:
            _, data, acquired = self.cache[url]
            return deepcopy(data), acquired
        # Use urllib's normal UA for ESPN, whose CDN rejected our app UA in
        # this implementation check. This is not a guarantee of CDN access.
        headers = {'Accept': 'application/json'}
        if 'espn.com' not in url:
            headers['User-Agent'] = 'SmartPC-Dashboard/0.6'
        self.request_count[url.split('?')[0]] = self.request_count.get(url.split('?')[0], 0) + 1
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=12) as response:
                body = response.read(4_000_001)
                if len(body) > 4_000_000:
                    raise ProviderError('Risposta Sport troppo grande')
                data = json.loads(body)
                if not isinstance(data, (dict, list) if self.allow_lists else dict):
                    raise ProviderError('Formato Sport non valido')
                age = number(response.headers.get('Age')) or 0
                maxage = re.search(r'(?:^|,)\s*max-age=(\d+)', response.headers.get('Cache-Control', ''))
                ttl = min(int(maxage[1]), 21600) if maxage else 0
                acquired = time.time() - age
                self.cache[url] = (time.time() + max(0, ttl - age), data, acquired)
                if len(self.cache) > 50:
                    self.cache.pop(next(iter(self.cache)))
                return deepcopy(data), acquired
        except urllib.error.HTTPError as error:
            retry = error.headers.get('Retry-After', '')
            seconds = number(retry)
            if seconds is None:
                try:
                    seconds = max(0, parsedate_to_datetime(retry).timestamp() - time.time())
                except (ValueError, TypeError):
                    seconds = 0
            if error.code in (403, 429) or seconds:
                seconds = seconds or (300 if error.code == 403 else 60)
                self.cooldowns[url] = (time.time() + seconds, error.code, f'Fonte Sport HTTP {error.code}')
            raise ProviderError(f'Fonte Sport HTTP {error.code}', retry_after=seconds, http_status=error.code) from error
        except (OSError, ValueError) as error:
            raise ProviderError('Fonte Sport non raggiungibile o risposta non valida') from error


def validate_snapshot(snapshot: dict, *, require_time=True):
    if not isinstance(snapshot, dict) or snapshot.get('competitionId') not in COMPETITIONS:
        raise ValueError('Formato cache Sport non valido')
    if snapshot.get('provider') not in ('fotmob', 'espn') or not re.fullmatch(r'\d{4}/\d{4}', snapshot.get('season', '')):
        raise ValueError('Fonte/stagione cache Sport non valida')
    if require_time and (timestamp(snapshot.get('fetchedAt')) is None or snapshot['fetchedAt'] > time.time() + 300):
        raise ValueError('Data cache Sport non valida')
    fixtures, standings = snapshot.get('fixtures'), snapshot.get('standings')
    if not isinstance(fixtures, list) or not 1 <= len(fixtures) <= 600:
        raise ValueError('Calendario Sport incompleto')
    if not isinstance(standings, list) or len(standings) != COMPETITIONS[snapshot['competitionId']].expected_teams:
        raise ValueError('Classifica Sport incompleta')
    if len({row.get('teamId') for row in standings}) != len(standings) or {row.get('position') for row in standings} != set(range(1, 21)):
        raise ValueError('Classifica Sport non valida')
    for row in standings:
        if not row.get('team') or not row.get('teamId') or number(row.get('points')) is None or number(row.get('played')) is None:
            raise ValueError('Riga classifica Sport non valida')
    ids = set()
    for match in fixtures:
        if not isinstance(match, dict) or match.get('status') not in MATCH_STATES or match.get('provider') != snapshot['provider']:
            raise ValueError('Partita cache Sport non valida')
        if match.get('season') != snapshot['season'] or match.get('competitionId') != snapshot['competitionId']:
            raise ValueError('Partita di una stagione diversa')
        for key in ('homeTeam', 'awayTeam', 'homeTeamId', 'awayTeamId'):
            if not isinstance(match.get(key), str) or not match[key] or len(match[key]) > 100:
                raise ValueError('Squadra cache Sport non valida')
        start = match.get('kickoffUtc')
        if start is not None and (type(start) not in (int, float) or timestamp(start) is None):
            raise ValueError('Orario cache Sport non valido')
        if not str(match.get('providerMatchId', '')).isdigit():
            raise ValueError('ID provider Sport non valido')
        identity = match.get('canonicalMatchId')
        if not identity or identity in ids or not match.get('providerMatchId'):
            raise ValueError('Identità cache Sport duplicata')
        ids.add(identity)
        for key in ('homeScore', 'awayScore'):
            if match.get(key) is not None and (number(match[key]) is None or match[key] > 99):
                raise ValueError('Punteggio cache Sport non valido')


def read_cache(path: Path) -> dict | None:
    try:
        if path.stat().st_size > 2_000_000:
            return None
        raw = json.loads(path.read_text())
        if raw.get('schemaVersion') != CACHE_VERSION:
            return None
        snapshot = raw.get('snapshot')
        validate_snapshot(snapshot)
        return snapshot
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def save_cache(path: Path, snapshot: dict):
    validate_snapshot(snapshot)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='sport-', suffix='.tmp', delete=False) as stream:
            name = stream.name
            json.dump({'schemaVersion': CACHE_VERSION, 'snapshot': snapshot}, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def merge_fixtures(snapshot: dict, updates: list, acquired: float):
    indexed = {m['canonicalMatchId']: m for m in snapshot['fixtures']}
    for match in updates:
        old = indexed.get(match['canonicalMatchId'])
        if old and old.get('fetchedAt', 0) > acquired:
            if match.get('detailFetchedAt') and all(old.get(k) == match.get(k) for k in ('status', 'homeScore', 'awayScore')):
                for key in ('events', 'stats', 'lineups', 'venue', 'detailFetchedAt'):
                    old[key] = deepcopy(match.get(key))
            continue
        match['fetchedAt'] = acquired
        match['dataChangedAt'] = acquired if not old or any(old.get(k) != match.get(k) for k in ('status', 'homeScore', 'awayScore', 'minute')) else old.get('dataChangedAt', acquired)
        if old and old['provider'] == match['provider']:
            for key in ('round', 'venue'):
                match[key] = match.get(key) or old.get(key, '')
            if not match.get('detailFetchedAt') and all(old.get(k) == match.get(k) for k in ('status', 'homeScore', 'awayScore')):
                for key in ('events', 'stats', 'lineups', 'detailFetchedAt'):
                    match[key] = deepcopy(old.get(key, [] if key != 'detailFetchedAt' else 0))
        indexed[match['canonicalMatchId']] = match
    snapshot['fixtures'] = list(indexed.values())


def refresh_snapshot(client: HTTPClient, previous: dict | None, now: float, *, selected_id='', full=False, requested_season=None):
    """One bounded poll. Fallback snapshots retain their own source and scope."""
    season = requested_season or season_for(now)
    historical = season != season_for(now)
    try:
        if full or historical or not previous or previous.get('provider') != 'fotmob' or previous.get('season') != season:
            raw, acquired = client.get(FOTMOB + 'leagues?' + urllib.parse.urlencode({'id': 55, 'ccode3': 'ITA', 'season': season}))
            snapshot = parse_fotmob_league(raw, season)
            snapshot['fetchedAt'] = snapshot['standingsFetchedAt'] = acquired
            for match in snapshot['fixtures']:
                match['fetchedAt'] = acquired
        else:
            snapshot = deepcopy(previous)
            # Include UTC yesterday around midnight; local date is explicit.
            dates = {datetime.fromtimestamp(now, ROME).strftime('%Y%m%d'), datetime.fromtimestamp(now - 6 * 3600, timezone.utc).strftime('%Y%m%d')}
            for date in sorted(dates):
                raw, acquired = client.get(FOTMOB + 'matches?date=' + date)
                leagues = raw.get('leagues')
                if not isinstance(leagues, list):
                    raise ValueError('Scoreboard FotMob non valido')
                league = next((l for l in leagues if str(l.get('id')) == '55'), None)
                if league:
                    updates = [parse_fotmob_fixture(m, season) for m in league.get('matches', [])]
                    merge_fixtures(snapshot, updates, acquired)
                snapshot['fetchedAt'] = max(snapshot['fetchedAt'], acquired)
        provider_error = ''
    except (ProviderError, ValueError, KeyError, TypeError, AttributeError) as error:
        if isinstance(error, ProviderError) and error.retry_after and error.http_status != 403:
            raise  # Honor Retry-After instead of trying another source immediately.
        provider_error = text(error, 120)
        snapshot = deepcopy(previous) if previous and previous.get('provider') == 'espn' and previous.get('season') == season else None
        date = f'{season.split("/")[1]}0531' if historical else datetime.fromtimestamp(now, ROME).strftime('%Y%m%d')
        raw, acquired = client.get(ESPN + 'scoreboard?dates=' + date)
        leagues = raw.get('leagues', [])
        if not leagues or leagues[0].get('slug') != 'ita.1' or str(leagues[0].get('season', {}).get('year')) != season.split('/')[0]:
            raise ValueError('Scoreboard ESPN di altra competizione/stagione')
        if not isinstance(raw.get('events'), list):
            raise ValueError('Scoreboard ESPN non valido')
        updates = [parse_espn_event(e, season) for e in raw['events']]
        if snapshot is None or full:
            table, table_at = client.get('https://site.api.espn.com/apis/v2/sports/soccer/ita.1/standings?season=' + season.split('/')[0])
            rows = parse_espn_standings(table, season)
            snapshot = {'competitionId': 'serie_a', 'competitionName': 'Serie A', 'season': season,
                        'provider': 'espn', 'calendarScope': 'nearby', 'fixtures': [], 'standings': rows,
                        'fetchedAt': acquired, 'standingsFetchedAt': table_at}
            # Bounded fetch of nearest known game dates, not 365 daily calls.
            dates = sorted({value[:10].replace('-', '') for value in leagues[0].get('calendar', [])})
            past = [d for d in dates if d < date][-3:]
            future = [d for d in dates if d > date][:3]
            for other in past + future:
                extra, extra_at = client.get(ESPN + 'scoreboard?dates=' + other)
                updates += [parse_espn_event(e, season) for e in extra.get('events', [])]
        merge_fixtures(snapshot, updates, acquired)
        snapshot['fetchedAt'] = acquired
    snapshot['checkedAt'] = now
    snapshot['fallbackReason'] = provider_error
    return refresh_detail(client, snapshot, now, selected_id)


def refresh_detail(client, previous, now, selected_id=''):
    """Load only the selected fixture; do not refetch the calendar on OK."""
    snapshot = deepcopy(previous)
    match = next((m for m in snapshot['fixtures'] if m['canonicalMatchId'] == selected_id), None)
    if match is None and not selected_id:
        match = next((m for m in snapshot['fixtures'] if m['status'] in LIVE_STATES), None)
    snapshot['detailError'] = ''
    snapshot['detailErrorMatchId'] = selected_id
    if match:
        try:
            if snapshot['provider'] == 'fotmob':
                raw, detail_at = client.get(FOTMOB + 'matchDetails?matchId=' + match['providerMatchId'])
                detail = fotmob_detail(raw, match)
            else:
                raw, detail_at = client.get(ESPN + 'summary?event=' + match['providerMatchId'])
                detail = espn_detail(raw, match)
            detail['detailFetchedAt'] = detail_at
            merge_fixtures(snapshot, [detail], detail_at)
        except (ProviderError, ValueError, KeyError, TypeError, AttributeError) as error:
            logging.getLogger(__name__).warning('Sport detail %s: %s', match['providerMatchId'], error)
            snapshot['detailErrorMatchId'] = match['canonicalMatchId']
            snapshot['detailError'] = 'Dettaglio non disponibile. Riprova tra poco.'
    validate_snapshot(snapshot)
    return snapshot


def poll_interval(snapshot: dict | None, now: float) -> int:
    if not snapshot:
        return 60
    if snapshot.get('season') != season_for(now):
        return 21600
    interval = 21600
    for match in snapshot.get('fixtures', []):
        start = match.get('kickoffUtc')
        if not start:
            continue
        delta = start - now
        if match['status'] in LIVE_STATES and -900 <= now - start < 6 * 3600:
            interval = min(interval, 30)
        elif match['status'] == 'scheduled' and -3 * 3600 < delta <= 600:
            interval = min(interval, 30)
        elif match['status'] == 'scheduled' and 600 < delta <= 3600:
            interval = min(interval, 900)
        elif match['status'] == 'finished' and 0 <= now - start < 26 * 3600:
            interval = min(interval, 900 if now - start < 4 * 3600 else 3600)
    return interval


def presentation(snapshot: dict | None, now: float, *, from_cache=False, verified=False, favourite='') -> dict:
    if not snapshot:
        return {'fixtures': [], 'upcoming': [], 'activeMatches': [], 'lastFinished': [], 'standings': [], 'teams': [], 'hasLiveView': False}
    data = deepcopy(snapshot)
    matches = sorted(data['fixtures'], key=lambda m: (m.get('kickoffUtc') or float('inf'), m['canonicalMatchId']))
    for match in matches:
        start = match.get('kickoffUtc')
        match['when'] = datetime.fromtimestamp(start, ROME).strftime('%d/%m · %H:%M') if start else 'Orario da confermare'
        age = now - match.get('fetchedAt', 0)
        match['fresh'] = not from_cache and 0 <= age <= 90
        match['isLive'] = verified and match['fresh'] and match['status'] in LIVE_STATES and start is not None and -900 <= now - start <= 6 * 3600
        match['scoreText'] = f"{match['homeScore']} – {match['awayScore']}" if match.get('homeScore') is not None and match.get('awayScore') is not None else '—'
        match['statusText'] = {'scheduled': 'In programma', 'live': 'In corso', 'half_time': 'Intervallo',
                               'finished': 'Terminata', 'postponed': 'Rinviata', 'cancelled': 'Annullata', 'unknown': 'Stato da verificare'}[match['status']]
    active = [m for m in matches if m['status'] in LIVE_STATES and m.get('kickoffUtc') and -900 <= now - m['kickoffUtc'] <= 6 * 3600]
    upcoming = [m for m in matches if m['status'] == 'scheduled' and (not m.get('kickoffUtc') or m['kickoffUtc'] >= now - 3 * 3600)]
    finished = [m for m in matches if m['status'] == 'finished']
    last_round = finished[-1]['round'] if finished else ''
    last = [m for m in matches if m['round'] == last_round] if last_round else finished[-10:]
    last = [m for m in last if m['status'] != 'scheduled']
    data.update(fixtures=matches, upcoming=upcoming, activeMatches=active, lastFinished=last,
                resultsRound=last_round, hasLiveView=bool(active), liveVerified=verified, fromCache=from_cache,
                teams=[{'id': r['teamId'], 'name': r['team']} for r in sorted(data['standings'], key=lambda r: r['team'])])
    data['historical'] = data.get('season') != season_for(now)
    data['favouriteMatch'] = next((m for m in upcoming if favourite in (m['homeTeamId'], m['awayTeamId'])), {}) if favourite else {}
    return data


def home_event(data: dict, favourite: str, enabled: bool, now: float) -> list:
    match = data.get('favouriteMatch', {})
    start = match.get('kickoffUtc')
    if not enabled or not favourite or data.get('historical') or data.get('fromCache') or not start or not 0 < start - now <= 7 * 86400:
        return []
    return [{'version': 1, 'id': 'sport:next:' + match['canonicalMatchId'], 'source': 'sport',
             'sourceLabel': 'Sport · ' + data.get('provider', ''), 'category': 'sport', 'priority': 1,
             'title': match['homeTeam'] + ' – ' + match['awayTeam'], 'detail': 'Serie A · ' + match['when'],
             'issuedAt': data.get('fetchedAt', now), 'startsAt': start, 'expiresAt': start + 3 * 3600,
             'revision': str(start), 'showOnHome': True}]


class GoalTracker:
    """Persisted baseline; opt-in only after real-session qualification.

    A provider change/reconnect resets the baseline. A confirmed event must have
    the expected new score; pending VAR and unknown confirmations stay silent.
    """
    def __init__(self, path: Path):
        self.path = path
        self.baseline = {}
        self.connected = False
        self.notices = {}
        self._persisted = None
        try:
            if path.stat().st_size > 64000:
                raise ValueError('Registro gol troppo grande')
            raw = json.loads(path.read_text())
            if raw.get('version') == 1 and isinstance(raw.get('notices'), dict):
                from event_core import validate_event
                self.notices = {key: validate_event(value) for key, value in raw['notices'].items() if isinstance(key, str)}
        except (OSError, ValueError, AttributeError):
            pass

    def disconnect(self):
        self.connected = False

    def update(self, data: dict, now: float, enabled: bool) -> list:
        current = {}
        for match in data.get('activeMatches', []):
            identity = match['canonicalMatchId']
            key = identity + ':' + match['provider']
            events = {e['id']: e for e in match.get('events', []) if e.get('type') == 'goal'}
            score = [match.get('homeScore'), match.get('awayScore')]
            old = self.baseline.get(key)
            current[key] = old if old and self.connected and match.get('pendingVAR') is not False else {'ids': list(events), 'score': score}
            if enabled and self.connected and match.get('isLive') and match.get('pendingVAR') is False:
                old = self.baseline.get(key)
                if old and None not in score and None not in old['score']:
                    for event_id, event in events.items():
                        notice_id = 'sport:goal:' + identity + ':' + event_id
                        new_score = event.get('score')
                        if event_id not in old['ids'] and event.get('confirmed') and new_score == score and sum(score) > sum(old['score']):
                            self.notices.setdefault(notice_id, {'version': 1, 'id': notice_id, 'source': 'sport',
                                'sourceLabel': 'Sport · ' + match['provider'], 'category': 'sport', 'priority': 2,
                                'bannerSize': 'large', 'title': 'GOL · ' + event.get('player', ''),
                                'detail': match['homeTeam'] + ' ' + match['scoreText'] + ' ' + match['awayTeam'],
                                'issuedAt': now, 'startsAt': now, 'expiresAt': now + 120, 'showOnHome': False,
                                'revision': event_id, '_match': identity, '_event': event_id, '_score': score})
            for notice_id, notice in list(self.notices.items()):
                if notice.get('_match') == identity and (notice.get('_event') not in events or sum(v or 0 for v in score) < sum(v or 0 for v in notice.get('_score', []))):
                    self.notices.pop(notice_id)
        self.baseline = current
        self.connected = True
        self.notices = {key: value for key, value in self.notices.items() if value.get('expiresAt', 0) > now}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            encoded = json.dumps({'version': 1, 'notices': self.notices}, sort_keys=True)
            if encoded != self._persisted:
                with temporary.open('w') as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
                self._persisted = encoded
        except OSError:
            pass
        return [{k: v for k, v in n.items() if not k.startswith('_')} for n in self.notices.values()] if enabled else []
