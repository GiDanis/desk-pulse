"""Meaningful Sport regressions: malformed feeds, persistence, freshness and VAR.

The bundled excerpts are historical samples, never production data.
"""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from sport_core import (GoalTracker, HTTPClient, ProviderError, club_id, fotmob_detail, fotmob_status, espn_status,
                        merge_fixtures, parse_fotmob_league, poll_interval, presentation, read_cache,
                        refresh_detail, parse_espn_event, espn_detail, refresh_snapshot, save_cache, season_for, validate_snapshot)

FIXTURES = Path(__file__).with_name('fixtures')


def sample(now=None):
    now = time.time() if now is None else now
    data = parse_fotmob_league(json.loads((FIXTURES / 'sport-fotmob-sample.json').read_text()), '2026/2027')
    data['fetchedAt'] = data['standingsFetchedAt'] = now
    for match in data['fixtures']:
        match['fetchedAt'] = now
    return data


class SportChecks(unittest.TestCase):
    def test_real_payload_and_detail(self):
        data = sample()
        detail = fotmob_detail(json.loads((FIXTURES / 'sport-fotmob-detail-sample.json').read_text()), data['fixtures'][0])
        self.assertEqual((detail['homeScore'], detail['awayScore']), (4, 1))
        self.assertEqual(len(detail['events']), 5)
        self.assertEqual(next(s for s in detail['stats'] if s['label'] == 'xG')['home'], '1.05')
        self.assertEqual(len({s['label'] for s in detail['stats']}), len(detail['stats']))
        self.assertEqual(club_id('Internazionale'), club_id('Inter'))
        wrong = deepcopy(detail)
        wrong['providerMatchId'] = 'wrong'
        with self.assertRaises(ValueError):
            fotmob_detail(json.loads((FIXTURES / 'sport-fotmob-detail-sample.json').read_text()), wrong)

    def test_upcoming_real_response_and_nullable_blocks(self):
        snapshot = json.loads((FIXTURES / 'sport-normalized-sample.json').read_text())
        original = next(m for m in snapshot['fixtures'] if m['providerMatchId'] == '5749693')
        raw = json.loads((FIXTURES / 'sport-fotmob-upcoming-detail.json').read_text())
        detail = fotmob_detail(raw, original)
        self.assertEqual(detail['status'], 'scheduled')
        self.assertIsNone(detail['homeScore'])
        self.assertIsNone(detail['awayScore'])
        self.assertEqual((detail['events'], detail['stats'], detail['lineups']), ([], [], []))
        self.assertEqual(detail['venue'], 'Stadio Comunale Luigi Ferraris')
        for content in (None, {'stats': {'Periods': None}, 'lineup': None, 'matchFacts': {'infoBox': None}},
                        {'stats': {'Periods': {'All': {'stats': [None, {'stats': None}]}}}}):
            raw['content'] = content
            self.assertEqual(fotmob_detail(raw, original)['stats'], [])
        raw['header']['status']['reason'] = None
        self.assertEqual(fotmob_detail(raw, original)['status'], 'scheduled')

    def test_espn_scheduled_null_optional_sections(self):
        event = {'id': '123', 'competitions': [{'date': '2026-10-10T13:00:00Z', 'venue': None,
                 'status': {'type': {'state': 'pre'}}, 'competitors': [
                     {'homeAway': 'home', 'team': {'id': '1', 'displayName': 'Genoa'}, 'score': '0'},
                     {'homeAway': 'away', 'team': {'id': '2', 'displayName': 'Fiorentina'}, 'score': '0'}]}]}
        original = parse_espn_event(event, '2026/2027')
        detail = espn_detail({'header': event, 'keyEvents': None, 'boxscore': None}, original)
        self.assertEqual(detail['events'], [])
        self.assertEqual(detail['stats'], [])
        self.assertIsNone(detail['homeScore'])

    def test_detail_only_fetch_age_and_safe_error(self):
        snapshot = json.loads((FIXTURES / 'sport-normalized-sample.json').read_text())
        original = next(m for m in snapshot['fixtures'] if m['providerMatchId'] == '5749693')
        now = time.time()
        original['fetchedAt'] = now
        raw = json.loads((FIXTURES / 'sport-fotmob-upcoming-detail.json').read_text())
        class Client:
            def get(self, url):
                assert 'matchDetails?matchId=5749693' in url
                return raw, now - 10  # Detail CDN age can exceed scoreboard age.
        result = refresh_detail(Client(), snapshot, now, original['canonicalMatchId'])
        selected = next(m for m in result['fixtures'] if m['providerMatchId'] == '5749693')
        self.assertEqual(selected['detailFetchedAt'], now - 10)
        self.assertEqual(selected['venue'], 'Stadio Comunale Luigi Ferraris')
        updated = deepcopy(selected)
        updated.update(events=[], stats=[], lineups=[])
        updated.pop('detailFetchedAt')
        merge_fixtures(result, [updated], now + 1)
        self.assertEqual(next(m for m in result['fixtures'] if m['providerMatchId'] == '5749693')['detailFetchedAt'], now - 10)
        with patch.object(Client, 'get', side_effect=AttributeError("'NoneType' object has no attribute 'get'")):
            error = refresh_detail(Client(), result, now, original['canonicalMatchId'])
        self.assertNotIn('NoneType', error['detailError'])
        self.assertEqual(error['detailErrorMatchId'], original['canonicalMatchId'])

    def test_state_precedence_missing_and_zero(self):
        self.assertEqual(fotmob_status({'started': False, 'reason': {'short': 'PP'}}), 'postponed')
        self.assertEqual(fotmob_status({'started': True, 'reason': {'short': 'HT'}}), 'half_time')
        self.assertEqual(fotmob_status({'started': True, 'cancelled': True}), 'unknown')
        self.assertEqual(espn_status({'type': {'state': 'pre', 'name': 'STATUS_POSTPONED'}}), 'postponed')
        self.assertEqual(espn_status({'type': {'state': 'in', 'name': 'STATUS_SUSPENDED'}}), 'unknown')
        raw = json.loads((FIXTURES / 'sport-fotmob-sample.json').read_text())
        first = raw['fixtures']['allMatches'][0]
        first['status'] = {'started': False, 'finished': False, 'scoreStr': '0 - 0'}
        data = parse_fotmob_league(raw, '2026/2027')
        self.assertIsNone(data['fixtures'][0]['homeScore'])
        first['status']['started'] = True
        data = parse_fotmob_league(raw, '2026/2027')
        self.assertEqual(data['fixtures'][0]['homeScore'], 0)

    def test_cache_atomicity_and_invalid_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sport.json'
            good = sample()
            save_cache(path, good)
            before = path.read_bytes()
            with patch('sport_core.os.replace', side_effect=OSError('disk')):
                with self.assertRaises(OSError):
                    save_cache(path, good)
            self.assertEqual(before, path.read_bytes())
            self.assertEqual(read_cache(path)['fixtures'], good['fixtures'])
            bad = deepcopy(good)
            bad['standings'] = bad['standings'][:-1]
            with self.assertRaises(ValueError):
                save_cache(path, bad)
            self.assertEqual(before, path.read_bytes())
            path.write_text('{broken')
            self.assertIsNone(read_cache(path))
            path.write_text(json.dumps({'schemaVersion': 999, 'snapshot': good}))
            self.assertIsNone(read_cache(path))

    def test_freshness_window_ordering_and_offline(self):
        now = time.time()
        data = sample(now)
        active = data['fixtures'][-1]
        active.update(status='live', kickoffUtc=now-1800, homeScore=0, awayScore=0)
        shown = presentation(data, now, verified=True)
        self.assertTrue(shown['activeMatches'][0]['isLive'])
        self.assertEqual(poll_interval(data, now), 30)
        self.assertFalse(presentation(data, now, from_cache=True, verified=True)['activeMatches'][0]['isLive'])
        self.assertFalse(presentation(data, now+91, verified=True)['activeMatches'][0]['isLive'])
        self.assertFalse(presentation(data, now, verified=False)['activeMatches'][0]['isLive'])
        old = deepcopy(active)
        old['homeScore'] = 99
        merge_fixtures(data, [old], now-300)
        self.assertEqual(data['fixtures'][-1]['homeScore'], 0)
        active['kickoffUtc'] = now-86400
        self.assertFalse(presentation(data, now, verified=True)['hasLiveView'])

    def test_provider_failure_keeps_original(self):
        class Offline:
            def get(self, url):
                raise ProviderError('offline')
        data = sample()
        before = deepcopy(data)
        with self.assertRaises(ProviderError):
            refresh_snapshot(Offline(), data, time.time(), full=True)
        self.assertEqual(before, data)
        raw = json.loads((FIXTURES / 'sport-fotmob-sample.json').read_text())
        raw['details']['selectedSeason'] = '2024/2025'
        with self.assertRaises(ValueError):
            parse_fotmob_league(raw, '2026/2027')
        raw = deepcopy(data)
        raw['fixtures'][0]['awayScore'] = -1
        with self.assertRaises(ValueError):
            validate_snapshot(raw)

    def test_goals_var_revocation_reconnect_and_restart(self):
        now = time.time()
        data = sample(now)
        match = data['fixtures'][0]
        match.update(status='live', kickoffUtc=now-1800, homeScore=0, awayScore=0, events=[], pendingVAR=False)
        with tempfile.TemporaryDirectory() as directory:
            tracker = GoalTracker(Path(directory) / 'goals.json')
            def update():
                return tracker.update(presentation(data, now, verified=True), now, True)
            self.assertFalse(update())  # Boot baseline.
            match.update(homeScore=1, pendingVAR=True, events=[{'id':'g1', 'type':'goal', 'side':'home', 'player':'Player', 'minute':'23', 'score':[1,0], 'confirmed':False}])
            self.assertFalse(update())
            match['pendingVAR'] = False
            match['events'][0]['confirmed'] = True
            self.assertEqual(len(update()), 1)
            self.assertEqual(len(update()), 1)  # Same ID, no second event.
            match.update(homeScore=0, events=[])
            self.assertFalse(update())  # VAR revoked.
            tracker.disconnect()
            match.update(homeScore=1, events=[{'id':'g2','type':'goal','player':'Player','score':[1,0],'confirmed':True}])
            self.assertFalse(update())  # Reconnect baseline.
            tracker = GoalTracker(Path(directory) / 'goals.json')
            self.assertFalse(update())  # Separate instance baseline.

    def test_rate_limit_cooldown_and_corrupt_goal_store(self):
        import urllib.error
        client = HTTPClient()
        failure = urllib.error.HTTPError('https://example.invalid', 429, 'rate', {'Retry-After':'120'}, None)
        with patch('sport_core.urllib.request.urlopen', side_effect=failure) as request:
            for _ in range(2):
                with self.assertRaises(ProviderError) as caught:
                    client.get('https://example.invalid')
                self.assertGreater(caught.exception.retry_after, 100)
            self.assertEqual(request.call_count, 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'goals.json'
            path.write_text('{"version":1,"notices":[]}')
            self.assertEqual(GoalTracker(path).notices, {})

    def test_timezone_and_season_boundaries(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now = datetime(2026,7,1,0,1,tzinfo=ZoneInfo('Europe/Rome')).timestamp()
        self.assertEqual(season_for(now), '2026/2027')
        self.assertEqual(season_for(now-120), '2025/2026')


if __name__ == '__main__':
    unittest.main()
