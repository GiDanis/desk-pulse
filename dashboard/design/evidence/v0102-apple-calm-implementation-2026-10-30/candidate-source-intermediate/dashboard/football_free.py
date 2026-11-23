"""BSD free Serie A acquisition, independent of navigation, with bounded REST work.

No token: no requests. No advertised paid WebSocket is used. Timelines never
turn `varDecision.confirmed` into a generic goal confirmation.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import hashlib
import os
from pathlib import Path
import re
import stat
import time
import urllib.error
import urllib.parse
import urllib.request

from sport_core import ProviderError, season_for

BASE = 'https://sports.bzzoiro.com/api/v2/'
LIVE = {'inprogress', '1st_half', 'halftime', '2nd_half', 'extratime', 'penalties'}
FINAL = {'finished', 'aet'}


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.pending')
    try:
        with temporary.open('w', encoding='utf-8') as stream:
            os.chmod(temporary, 0o600)
            json.dump(value, stream, ensure_ascii=False, separators=(',', ':'))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_private(path):
    p = Path(path)
    if not p.exists():
        return None
    if p.stat().st_size > 4096 or stat.S_IMODE(p.stat().st_mode) & 0o077:
        raise ValueError('Configurazione BSD non privata')
    value = json.loads(p.read_text())
    token = value.get('token')
    if not isinstance(token, str) or not 8 <= len(token) <= 256 or not re.fullmatch(r'[A-Za-z0-9._-]+', token):
        raise ValueError('Token BSD non valido')
    return {'token': token}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class BSDClient:
    def __init__(self, token, directory, transport=None):
        self.token = token
        self.path = Path(directory) / 'football-quota.json'
        self.transport = transport or self._read
        self.requests = 0
        self.bytes = 0
        self.blocked_until = 0
        self._quota = {}
        if self.path.exists():
            try:
                self._quota = json.loads(self.path.read_text())
                if not isinstance(self._quota, dict):
                    raise ValueError()
            except (OSError, ValueError):
                # Unknown persisted consumption must not reset today's budget.
                self._quota = {'day': self.day(time.time()), 'used': 7000}

    @staticmethod
    def day(now):
        return datetime.fromtimestamp(now, timezone.utc).date().isoformat()

    def _read(self, url):
        request = urllib.request.Request(url, headers={'Authorization': 'Token ' + self.token,
                                                       'Accept': 'application/json', 'User-Agent': 'SmartPC/0.8.8'})
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=12) as response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ProviderError('Risposta BSD oltre il limite')
            self.bytes += len(raw)
            return json.loads(raw), dict(response.headers)

    def get(self, path, **query):
        now = time.time()
        day = self.day(now)
        if now < self.blocked_until:
            raise ProviderError('Fonte calcio in attesa', retry_after=self.blocked_until - now)
        if self._quota.get('day') != day:
            self._quota = {'day': day, 'used': 0}
        if self._quota.get('used', 7000) >= 7000:
            midnight = (datetime.fromtimestamp(now, timezone.utc) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            raise ProviderError('Budget gratuito calcio esaurito', retry_after=midnight - now)
        self._quota['used'] += 1
        atomic_json(self.path, self._quota)  # Reserve before sending, including failed GETs.
        self.requests += 1
        url = BASE + path + ('?' + urllib.parse.urlencode(query) if query else '')
        try:
            value, headers = self.transport(url)
        except urllib.error.HTTPError as exc:
            wait = 300
            try:
                wait = max(wait, min(86400, float(exc.headers.get('Retry-After', 300))))
            except (ValueError, TypeError):
                pass
            if exc.code in (401, 403):
                wait = 21600
            self.blocked_until = now + wait
            exc.close()
            raise ProviderError('Accesso BSD non disponibile', retry_after=wait) from None
        except (OSError, ValueError):
            raise ProviderError('Dati BSD non disponibili') from None
        remaining = re.search(r'\br=(\d+)', headers.get('RateLimit', headers.get('ratelimit', '')))
        if remaining and int(remaining[1]) <= 500:
            self._quota['used'] = 7000
            atomic_json(self.path, self._quota)
        return value


def collection(value, key='results'):
    if not isinstance(value, dict) or not isinstance(value.get(key), list):
        raise ValueError('Collezione BSD non valida')
    count = value.get('count')
    if type(count) is not int or count != len(value[key]):
        raise ValueError('Collezione BSD incompleta')
    return value[key]


def fixture(raw, league, season):
    if not isinstance(raw, dict) or type(raw.get('id')) is not int:
        raise ValueError('Identità partita BSD assente')
    if raw.get('league_id') != league or raw.get('season_id') != season:
        raise ValueError('Competizione/stagione BSD diversa')
    value = {k: raw.get(k) for k in ('id', 'home_team', 'away_team', 'home_team_id', 'away_team_id',
                                    'event_date', 'status', 'home_score', 'away_score', 'current_minute', 'round_number',
                                    'last_updated', 'fetchedAt', 'dataChangedAt', 'sourceDataAt')}
    for side in ('home', 'away'):
        if type(value[side + '_team_id']) is not int or not isinstance(value[side + '_team'], str) or not value[side + '_team']:
            raise ValueError('Squadre BSD non valide')
        score = value[side + '_score']
        if score is not None and (type(score) is not int or not 0 <= score <= 30):
            raise ValueError('Punteggio BSD non valido')
    at = datetime.fromisoformat(value['event_date'].replace('Z', '+00:00'))
    if at.tzinfo is None:
        raise ValueError('Orario BSD senza fuso')
    value['kickoff'] = at.timestamp()
    if value['status'] not in LIVE | FINAL | {'notstarted', 'delayed', 'postponed', 'cancelled', 'unresolved'}:
        raise ValueError('Stato BSD sconosciuto')
    return value


class FootballFeed:
    def __init__(self, client, directory):
        self.client = client
        self.path = Path(directory) / 'football-feed.json'
        self.matches = {}
        self.notices = {}
        self.league = self.season = None
        self.season_name = ''
        self.last_schedule = self.last_received = 0
        self.details_at = {}
        self.baseline = True
        self.sequence = 0
        self.last_full = 0
        self.standings = []
        self.details = {}
        self.incident_keys = {}
        self.persisted = None
        self.last_persisted = 0
        try:
            if self.path.stat().st_size > 2_000_000:
                raise ValueError('Registro BSD troppo grande')
            saved = json.loads(self.path.read_text())
            from event_core import validate_event
            self.notices = {v['id']: validate_event(v) for v in saved['notices'] if v['expiresAt'] > time.time() and v['source'] == 'football'}
            sequence = saved.get('sequence', 0)
            self.sequence = sequence if type(sequence) is int and sequence >= 0 else 0
        except (OSError, ValueError, KeyError, TypeError):
            pass

    def disconnect(self):
        self.baseline = True

    def discover(self, now):
        leagues = collection(self.client.get('leagues/', country='Italy', is_women='false', limit=200))
        candidates = [v for v in leagues if v.get('name') == 'Serie A' and v.get('country') == 'Italy'
                      and v.get('is_women') is False and v.get('is_active') is True]
        if len(candidates) != 1:
            raise ValueError('Serie A BSD non univoca')
        league = candidates[0]
        current = league.get('current_season') or {}
        expected = season_for(now)
        name = str(current.get('name', '')).replace('-', '/')
        short = expected[2:5] + expected[-2:]
        if (name not in (expected, expected[:5] + expected[-2:], 'Serie A ' + short)
                or current.get('year') != int(expected[:4]) or current.get('is_current') is not True
                or type(current.get('id')) is not int):
            raise ValueError('Stagione corrente BSD da verificare')
        self.league, self.season, self.season_name = league['id'], current['id'], expected
        self.matches = {}
        self.last_schedule = 0
        self.baseline = True

    def notice(self, match, title, now, kind, priority=2):
        self.sequence += 1
        identity = f"bsd:{match['id']}:{kind}:{self.sequence}"
        scores = f"{match['home_score']}–{match['away_score']}" if match['home_score'] is not None and match['away_score'] is not None else 'risultato in attesa'
        item = {'version': 1, 'id': identity, 'source': 'football', 'sourceLabel': 'BSD · Serie A',
                'category': 'serie_a', 'priority': priority, 'bannerSize': 'large', 'title': title,
                'detail': f"{match['home_team']} – {match['away_team']} · {scores}"[:240],
                'issuedAt': now, 'startsAt': now, 'expiresAt': now + 21600,
                'bannerUntil': now + 180, 'revision': str(self.sequence), 'matchId': str(match['id']),
                'type': kind, 'showOnHome': False, 'sourceUrl': 'https://sports.bzzoiro.com/'}
        self.notices[identity] = item

    def compare(self, previous, current, incidents, now, silent=False):
        if silent or not previous:
            return
        old_score = (previous['home_score'], previous['away_score'])
        new_score = (current['home_score'], current['away_score'])
        if previous['status'] not in LIVE and current['status'] in LIVE:
            self.notice(current, 'Serie A · Partita iniziata', now, 'start')
        if new_score != old_score and all(type(v) is int for v in old_score + new_score):
            correction = any(b < a for a, b in zip(old_score, new_score))
            if correction:
                # Remove overturned score notices from the full active snapshot;
                # EventEngine retains them as revoked in history.
                self.notices = {key: value for key, value in self.notices.items()
                                if value.get('matchId') != str(current['id']) or value.get('type') != 'score'}
            goals = [v for v in incidents if v.get('type') == 'goal'
                     and (v.get('home_score'), v.get('away_score')) == new_score]
            single = not correction and sum(new_score) - sum(old_score) == 1
            title = 'Serie A · Risultato corretto' if correction else 'Serie A · Gol segnalato dalla fonte' if single and len(goals) == 1 else 'Serie A · Risultato aggiornato'
            self.notice(current, title, now, 'correction' if correction else 'score')
        if previous['status'] not in FINAL and current['status'] in FINAL:
            self.notice(current, 'Serie A · Partita conclusa', now, 'end')

    def read_detail(self, identity, now):
        if identity not in self.matches:
            raise ValueError('Dettaglio BSD senza identità')
        cached = self.details.get(identity, {})
        if now - cached.get('detailFetchedAt', 0) < 120:
            return cached
        stats = self.client.get(f'events/{identity}/stats/')
        lineups = self.client.get(f'events/{identity}/lineups/')
        incidents = self.client.get(f'events/{identity}/incidents/')
        if any(v.get('event_id') != identity for v in (stats, lineups, incidents)):
            raise ValueError('Identità dettaglio BSD diversa')
        result = {'stats': [], 'lineups': [], 'events': [], 'detailFetchedAt': now}
        bag = stats.get('stats') or {}
        for key, label in [('ball_possession','Possesso'), ('total_shots','Tiri'), ('shots_on_target','Tiri in porta'),
                           ('corner_kicks','Calci d’angolo'), ('fouls','Falli'), ('yellow_cards','Ammonizioni'), ('red_cards','Espulsioni')]:
            home, away = bag.get('home', {}).get(key), bag.get('away', {}).get(key)
            if type(home) in (int, float) and type(away) in (int, float):
                result['stats'].append({'label':label, 'home':str(home), 'away':str(away)})
        if lineups.get('lineup_status') == 'confirmed':
            for side in ('home','away'):
                team = (lineups.get('lineups') or {}).get(side, {})
                if team.get('team_id') != self.matches[identity][side + '_team_id']:
                    raise ValueError('Squadra formazione BSD diversa')
                squad = []
                for group, starter in [('players', True), ('substitutes', False)]:
                    for player in team.get(group, [])[:30]:
                        squad.append({'id': str(player['id']), 'name': str(player['name'])[:100],
                            'firstName':'', 'lastName':'', 'shirtNumber':player.get('jersey_number'),
                            'starter': starter, 'role': {'G':'P','D':'D','M':'C','F':'A'}.get(player.get('position'),''),
                            'subIn':False, 'subOut':False, 'inMinute':None, 'outMinute':None})
                result['lineups'].append({'side':side, 'formation':str(team.get('formation') or '')[:30],
                    'players':[p['name'] for p in squad if p['starter']], 'squad':squad})
        for value in incidents.get('incidents', []):
            if value.get('type') == 'goal':
                identity_key = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:24]
                result['events'].append({'id':identity_key,'type':'goal', 'side':'home' if value.get('is_home') is True else 'away',
                    'player':str(value.get('player') or '')[:100], 'minute':str(value.get('minute') or ''),
                    'confirmed':False, 'score':[value.get('home_score'),value.get('away_score')]})
        self.details[identity] = result
        return result

    def refresh(self, now=None):
        now = time.time() if now is None else now
        if self.season_name != season_for(now):
            self.discover(now)
        silent = self.baseline or now - self.last_received > 90
        matches = deepcopy(self.matches)
        acquired = set()
        day = datetime.fromtimestamp(now, timezone.utc).date()
        if not self.matches or now - self.last_full >= 21600:
            all_rows = []
            total = None
            for offset in range(0, 600, 200):
                page = self.client.get('events/', league_id=self.league, season_id=self.season, limit=200, offset=offset)
                if not isinstance(page, dict) or type(page.get('count')) is not int or not isinstance(page.get('results'), list):
                    raise ValueError('Calendario BSD non valido')
                if total is not None and page['count'] != total:
                    raise ValueError('Calendario BSD variato durante la paginazione')
                total = page['count']
                all_rows.extend(page['results'])
                if len(all_rows) >= total:
                    break
            if len(all_rows) != total or not 1 <= total <= 600:
                raise ValueError('Calendario BSD incompleto')
            matches = {v['id']: fixture(v, self.league, self.season) for v in all_rows}
            if len(matches) != total:
                raise ValueError('Calendario BSD con duplicati')
            table = self.client.get(f'leagues/{self.league}/standings/', season_id=self.season)
            if (table.get('league_id') != self.league or table.get('season', {}).get('id') != self.season
                    or table.get('grouped') is not False or len(table.get('standings', [])) != 20):
                raise ValueError('Classifica BSD incompleta')
            acquired.update(matches)
            self.standings = deepcopy(table['standings'])
            self.last_full = now
        if not self.matches or now - self.last_schedule >= 900:
            raw = self.client.get('events/', league_id=self.league, season_id=self.season,
                                  date_from=(day - timedelta(days=1)).isoformat(),
                                  date_to=(day + timedelta(days=7)).isoformat(), limit=200)
            window = {v['id']: fixture(v, self.league, self.season) for v in collection(raw)}
            matches.update(window)
            acquired.update(window)
            self.last_schedule = now
        active = [v for v in matches.values() if v['status'] in LIVE or -300 <= now - v['kickoff'] <= 14400 and v['status'] not in FINAL | {'cancelled', 'postponed'}]
        if active:
            response = self.client.get('events/live/', league_id=self.league, season_id=self.season)
            live = collection(response, 'events')
            seen = set()
            for raw in live:
                identity = raw.get('id')
                if type(identity) is not int or identity <= 0:
                    raise ValueError('Identità live BSD non valida')
                if identity not in matches:
                    # Resolve identities using the detail, never by fuzzy team names.
                    full = self.client.get(f'events/{identity}/')
                    matches[identity] = fixture(full, self.league, self.season)
                merged = {**matches[identity], **raw, 'league_id': self.league, 'season_id': self.season}
                # A compact item must not override known identity fields.
                if raw.get('league_id', self.league) != self.league or raw.get('season_id', self.season) != self.season:
                    raise ValueError('Competizione live BSD diversa')
                matches[identity] = fixture(merged, self.league, self.season)
                acquired.add(identity)
                seen.add(identity)
            for old in active:
                if old['id'] not in seen:
                    matches[old['id']] = fixture(self.client.get(f"events/{old['id']}/"), self.league, self.season)
                    acquired.add(old['id'])
        for identity in acquired:
            match = matches[identity]
            previous = self.matches.get(identity, {})
            match['fetchedAt'] = now
            fields = ('status', 'home_score', 'away_score', 'current_minute', 'kickoff')
            match['dataChangedAt'] = now if any(previous.get(k) != match.get(k) for k in fields) else previous.get('dataChangedAt', now)
            try:
                stamp = datetime.fromisoformat(str(match.get('last_updated')).replace('Z', '+00:00'))
                match['sourceDataAt'] = stamp.timestamp() if stamp.tzinfo and stamp.timestamp() <= now + 300 else None
            except ValueError:
                match['sourceDataAt'] = None
        details = {}
        for identity, match in matches.items():
            old = self.matches.get(identity)
            changed = old and (old['home_score'], old['away_score'], old['status']) != (match['home_score'], match['away_score'], match['status'])
            if match['status'] in LIVE | FINAL and (changed or match['status'] in LIVE and now - self.details_at.get(identity, 0) >= 120):
                raw = self.client.get(f'events/{identity}/incidents/')
                if raw.get('event_id') != identity or not isinstance(raw.get('incidents'), list) or any(not isinstance(v, dict) for v in raw['incidents']):
                    raise ValueError('Cronologia BSD non valida')
                details[identity] = raw['incidents']
                self.details_at[identity] = now
        before = deepcopy(self.notices), self.sequence
        try:
            self.notices = {k: v for k, v in self.notices.items() if v['expiresAt'] > now}
            for identity, match in matches.items():
                self.compare(self.matches.get(identity), match, details.get(identity, []), now, silent)
                if identity in details:
                    keys = {hashlib.sha256(json.dumps({k:v.get(k) for k in ('decision','minute','added_time','period_second','is_home','player_id','home_score','away_score')}, sort_keys=True).encode()).hexdigest(): v
                            for v in details[identity] if v.get('type') == 'varDecision'}
                    previous_keys = self.incident_keys.get(identity)
                    if not silent and previous_keys is not None:
                        for key, value in keys.items():
                            if key not in previous_keys and value.get('decision') in ('goalNotAwarded', 'goalAwarded'):
                                self.notice(match, 'VAR · Gol non assegnato dalla fonte' if value['decision'] == 'goalNotAwarded' else 'VAR · Gol assegnato dalla fonte', now, 'var')
                    self.incident_keys[identity] = set(keys)
            payload = {'notices': list(self.notices.values()), 'sequence': self.sequence,
                       'matches': list(matches.values()), 'checkedAt': now,
                       'leagueId': self.league, 'seasonId': self.season, 'seasonName': self.season_name, 'standings': self.standings}
            comparable = deepcopy(payload)
            comparable.pop('checkedAt')
            for item in comparable['matches']:
                item.pop('fetchedAt', None)
            if comparable != self.persisted or now - self.last_persisted >= 300:
                atomic_json(self.path, payload)
                self.persisted, self.last_persisted = comparable, now
        except Exception:
            self.notices, self.sequence = before
            raise
        self.matches, self.last_received, self.baseline = matches, now, False
        return {'notices': list(self.notices.values()), 'matches': list(matches.values()), 'checkedAt': now,
                'nextSeconds': self.interval(now), 'requests': self.client.requests, 'bytes': self.client.bytes,
                'status': 'attiva · conferma gol non qualificata', 'standings': deepcopy(self.standings)}

    def interval(self, now):
        upcoming = [v['kickoff'] for v in self.matches.values() if v['status'] not in FINAL | {'cancelled', 'postponed'}]
        if any(v['status'] in LIVE for v in self.matches.values()) or any(-300 <= now - v <= 14400 for v in upcoming):
            return 30
        return max(30, min([900] + [v - now - 300 for v in upcoming if v - now > 300]))
