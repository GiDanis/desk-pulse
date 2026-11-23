"""One autonomous Serie A worker shared by notifications and score views."""
from copy import deepcopy
import os
import json
from pathlib import Path
import time
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot
from football_free import BSDClient, FootballFeed, load_private
from events import default_store_path
from sport_core import make_match, club_id, validate_snapshot


def projected(result, season):
    fixtures = []
    for match in result.get('matches', []):
        status = ('half_time' if match['status'] == 'halftime' else 'live' if match['status'] in
                  {'inprogress','1st_half','2nd_half','extratime','penalties'} else 'finished' if match['status'] in
                  {'finished','aet'} else {'notstarted':'scheduled','delayed':'scheduled','postponed':'postponed','cancelled':'cancelled'}.get(match['status'], 'unknown'))
        value = make_match({'name': match['home_team'], 'id': match['home_team_id']},
                           {'name': match['away_team'], 'id': match['away_team_id']}, provider='bsd',
                           provider_id=match['id'], season=season, kickoff=match['kickoff'], status=status,
                           scores=[match['home_score'], match['away_score']], round_name=str(match.get('round_number') or ''),
                           minute=str(match.get('current_minute') or ''), raw={'source': 'BSD'})
        # Provider IDs remain authoritative; no cross-provider fuzzy event mapping.
        value['canonicalMatchId'] = f"bsd:serie_a:{season}:{match['id']}"
        value.update(fetchedAt=match.get('fetchedAt') or result['checkedAt'],
                     dataChangedAt=match.get('dataChangedAt') or result['checkedAt'],
                     sourceDataAt=match.get('sourceDataAt'))
        fixtures.append(value)
    standings = [{'teamId': club_id(v['team_name']), 'team': v['team_name'], 'position': v['position'],
                  'points': v['pts'], 'played': v['played'], 'won': v['won'], 'draw': v['drawn'],
                  'lost': v['lost'], 'goalsFor': v['gf'], 'goalsAgainst': v['ga'], 'goalDifference': v['gd']}
                 for v in result.get('standings', [])]
    return {'provider': 'bsd', 'competitionId': 'serie_a', 'competitionName': 'Serie A', 'calendarScope': 'season', 'season': season,
            'fetchedAt': result['checkedAt'], 'fixtures': fixtures, 'standings': standings, 'teams': [],
            'coverageMessage': 'Calendario BSD · dettagli estesi non acquisiti', 'liveVerified': False}


class Signals(QObject):
    done = Signal(object, object)


class Worker(QRunnable):
    def __init__(self, feed, detail_id=None):
        super().__init__()
        self.feed = feed
        self.detail_id = detail_id
        self.signals = Signals()

    def run(self):
        try:
            result, error = self.feed.refresh(), None
            validate_snapshot(projected(result, self.feed.season_name))
            if self.detail_id is not None:
                try:
                    self.feed.read_detail(self.detail_id, time.time())
                except Exception:
                    result['detailError'] = 'Dettaglio BSD non aggiornato · dati precedenti conservati'
        except Exception as exc:
            self.feed.disconnect()
            result, error = None, exc
        self.signals.done.emit(result, error)


class FootballService(QObject):
    changed = Signal()
    eventsChanged = Signal(object)
    interruptionsChanged = Signal(bool)

    def __init__(self, parent=None, *, auto_refresh=True, config_path=None, directory=None):
        super().__init__(parent)
        self.directory = Path(directory) if directory else default_store_path().parent
        self.config_path = Path(config_path or os.environ.get('SMARTPC_FOOTBALL_CONFIG', self.directory / 'football-bsd.json'))
        self.feed = None
        self.worker = None
        self.closed = False
        self.enabled = True
        self.status = 'fonte da configurare · BSD gratuito'
        self.result = {}
        self.snapshot = None
        self.failures = 0
        self.pending_detail = None
        self.auto = auto_refresh and os.environ.get('SMARTPC_SPORT_OFFLINE') not in ('1','true','yes')
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda: self.refresh())
        try:
            config = load_private(self.config_path)
            if config:
                self.feed = FootballFeed(BSDClient(config['token'], self.directory), self.directory)
                self.status = 'fonte da verificare · BSD'
                try:
                    if self.feed.path.stat().st_size > 2_000_000:
                        raise ValueError('Cache BSD troppo grande')
                    cached = json.loads(self.feed.path.read_text())
                    # Persisted identity is scoped by the saved season, never
                    # guessed from the current date after an offline reboot.
                    snapshot = projected(cached, cached['seasonName'])
                    validate_snapshot(snapshot)
                    self.snapshot = snapshot
                    self.status = 'cache BSD · da verificare'
                except (OSError, ValueError, KeyError, IndexError, TypeError):
                    pass
        except (OSError, ValueError):
            self.status = 'configurazione BSD da correggere'
        if self.feed and self.auto:
            QTimer.singleShot(0, lambda: self.refresh())

    @Slot(result=bool)
    def refresh(self, detail_id=None):
        if detail_id is not None:
            self.pending_detail = detail_id
        if self.closed or self.worker or not self.feed:
            return False
        self.timer.stop()
        self.worker = Worker(self.feed, self.pending_detail)
        self.pending_detail = None
        self.worker.signals.done.connect(self._finished)
        self.pool.start(self.worker)
        return True

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.interruptionsChanged.emit(enabled)
        self.eventsChanged.emit(deepcopy(self.result.get('notices', [])))
        self.changed.emit()

    @Slot(object, object)
    def _finished(self, result, error):
        self.worker = None
        if self.closed:
            return
        if result:
            self.result = result
            self.snapshot = projected(result, self.feed.season_name)
            for match in self.snapshot['fixtures']:
                match.update(deepcopy(self.feed.details.get(int(match['providerMatchId']), {})))
            if result.get('detailError'):
                self.snapshot['detailError'] = result['detailError']
            self.status = result['status'] if self.enabled else 'solo dati · avvisi Serie A disattivati'
            self.failures = 0
            self.eventsChanged.emit(result['notices'])
            delay = result['nextSeconds']
        else:
            self.failures += 1
            self.status = 'dati precedenti · fonte BSD non aggiornata' if self.snapshot else 'fonte BSD non disponibile'
            delay = max(getattr(error, 'retry_after', 0), min(900, 30 * 2 ** min(self.failures, 5)))
        self.changed.emit()
        if self.pending_detail is not None:
            self.refresh()
            return
        if self.auto:
            self.timer.start(int(min(86400, delay) * 1000))

    def close(self):
        self.closed = True
        self.timer.stop()
        self.pool.waitForDone(15000)
