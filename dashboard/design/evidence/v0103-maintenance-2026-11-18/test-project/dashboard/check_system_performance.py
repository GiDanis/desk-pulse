"""v0.9.3 correctness gates for cached projections and read-only metadata."""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
_private=tempfile.TemporaryDirectory(prefix='smartpc-performance-')
for _key in ('XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_CACHE_HOME','XDG_STATE_HOME'):
    os.environ[_key]=str(Path(_private.name)/_key)
    Path(os.environ[_key]).mkdir()
os.environ['STATE_DIRECTORY']=os.environ['XDG_STATE_HOME']
os.environ['SMARTPC_FOOTBALL_CONFIG']=str(Path(_private.name)/'unconfigured-football.json')
from PySide6.QtCore import QCoreApplication
from sport import SportService
from sport_core import presentation
from event_core import EventEngine, _payload
from game import GameService

ROOT=Path(__file__).parent
app=QCoreApplication.instance() or QCoreApplication([])


class ProjectionChecks(unittest.TestCase):
    def test_sport_exact_time_boundaries_and_revision(self):
        source=json.loads((ROOT/'fixtures/sport-normalized-sample.json').read_text())
        now=time.time()
        source['fetchedAt']=now
        for match in source['fixtures']:
            match['fetchedAt']=now
        match=source['fixtures'][0]
        match.update(status='live',kickoffUtc=now-10)
        original=deepcopy(source)
        service=SportService(auto_refresh=False,initial=source,verified=True,
                             cache_path=Path(_private.name)/'sport.json',state_path=Path(_private.name)/'goals.json')
        try:
            with patch('sport.presentation',wraps=presentation) as render:
                first=service._data_view(now)
                self.assertIs(first,service._data_view(now+1))
                self.assertEqual(render.call_count,1)
                points=(now-1,now,now+90,math.nextafter(now+90,math.inf),now+10800,
                        math.nextafter(now+10800,math.inf),now+21590,
                        math.nextafter(now+21590,math.inf),now-1000,now+2)
                for point in points:
                    self.assertEqual(service._data_view(point),presentation(source,point,verified=True))
                service._favourite='inter'
                self.assertEqual(service._data_view(now),presentation(source,now,verified=True,favourite='inter'))
                service._from_cache=True
                self.assertEqual(service._data_view(now),presentation(source,now,verified=True,favourite='inter',from_cache=True))
                service._snapshot=deepcopy(source)
                service._snapshot['fixtures'][0]['homeScore']=9
                self.assertEqual(service._data_view(now),presentation(service._snapshot,now,verified=True,favourite='inter',from_cache=True))
            self.assertEqual(source,original)
        finally:service.close()

    def test_sport_transient_error_does_not_poison_cache(self):
        source=json.loads((ROOT/'fixtures/sport-normalized-sample.json').read_text())
        now=time.time()
        source['fetchedAt']=now
        source['fixtures'][0].update(status='live',kickoffUtc=now-10,fetchedAt=now)
        service=SportService(auto_refresh=False,initial=source,verified=True,
                             cache_path=Path(_private.name)/'sport.json',state_path=Path(_private.name)/'goals.json')
        try:
            with patch('sport.time.time',return_value=now):
                good=service.moduleState
                service._error='offline'
                self.assertFalse(any(m['isLive'] for m in service.moduleState['data']['fixtures']))
                service._error=''
                self.assertEqual(good,service.moduleState)
                self.assertNotIn('detailLoading',service._view)
        finally:service.close()

    def test_sport_qml_projection_retains_selected_detail_and_backend_facts(self):
        from theme_api import normalize_dto
        source=json.loads((ROOT/'fixtures/sport-normalized-sample.json').read_text())
        service=SportService(auto_refresh=False,initial=source,
                             cache_path=Path(_private.name)/'sport.json',state_path=Path(_private.name)/'goals.json')
        try:
            full=service.moduleState
            match=next(row for row in full['data']['fixtures'] if row.get('events'))
            identity=match['canonicalMatchId']
            projected=service.view_state(identity)
            selected=next(row for row in projected['data']['fixtures'] if row['canonicalMatchId']==identity)
            self.assertEqual(normalize_dto('MatchData',selected),normalize_dto('MatchData',match))
            self.assertEqual(projected['status'],full['status'])
            self.assertEqual(projected['updatedAt'],full['updatedAt'])
            self.assertEqual([m['canonicalMatchId'] for m in full['data']['fixtures']],
                             [m['canonicalMatchId'] for m in projected['data']['fixtures']])
            self.assertTrue(all(not m.get('events') and not m.get('stats') and not m.get('lineups')
                                for m in service.view_state()['data']['fixtures']))
            self.assertEqual(full,service.moduleState)
        finally:service.close()

    def test_event_decode_reuse_and_public_ownership(self):
        engine=EventEngine(':memory:')
        event=dict(version=1,id='test:1',source='test',category='test',priority=2,
                   title='Test',detail='Test',issuedAt=100,startsAt=100,expiresAt=200,
                   showOnHome=True,nested={'value':[1]})
        try:
            engine.replace_source('test',[event])
            _payload.cache_clear()
            first=engine.snapshot(now=101)
            loads=_payload.cache_info().misses
            engine.next_deadline(101)
            self.assertEqual(first,engine.snapshot(now=101))
            self.assertEqual(_payload.cache_info().misses,loads)
            first['inbox'][0]['nested']['value'].append(2)
            self.assertEqual(engine.lookup('test:1',101)['nested']['value'],[1])
            engine.mark_notified('test:1')
            self.assertTrue(engine.lookup('test:1',101)['presented'])
            self.assertFalse(engine.snapshot(now=200)['inbox'])
        finally:engine.close()

    def test_metadata_process_matches_sync_and_observes_commit(self):
        from game_store import GameStore
        with tempfile.TemporaryDirectory() as root:
            reference=GameService(root)
            expected=reference.snapshot
            reference.close()
            service=GameService(root,async_metadata=True)
            try:
                def wait_ready():
                    until=time.monotonic()+15
                    while time.monotonic()<until:
                        app.processEvents()
                        reader=service._metadata_reader
                        if service._drivers and reader.inflight is None and reader.pending is None:return
                        time.sleep(.005)
                    self.fail('metadata process timeout')
                wait_ready()
                actual=service.snapshot
                for key in ('drivers','selectedDriverId','profile','progress','leaderboard','dossier','settings'):
                    self.assertEqual(actual[key],expected[key],key)
                self.assertIsNone(service._process)
                identity=service._drivers[2]['id']
                # Coalescing: only the last route request can reach publication.
                service._selected=identity
                service._refresh()
                self.assertFalse(service._dossier)  # Never label the previous dossier with a new pilot.
                service._selected=service._drivers[-1]['id']
                service._refresh()
                wait_ready()
                self.assertEqual(service._selected,service._drivers[-1]['id'])
                with GameStore(root).connect() as db:
                    db.execute('UPDATE drivers SET name=? WHERE id=?',('Commit osservato',service._selected))
                service._refresh()
                wait_ready()
                self.assertEqual(service.snapshot['selectedDriverName'],'Commit osservato')
                # A reader never creates a running training or race session.
                with service._store.connect() as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0],0)
            finally:service.close()

    def test_event_cache_external_commit_and_clock_reversal(self):
        with tempfile.TemporaryDirectory() as root:
            engine=EventEngine(Path(root)/'events.sqlite')
            writer=EventEngine(Path(root)/'events.sqlite')
            event=dict(version=1,id='test:future',source='test',category='test',priority=2,
                       title='Test',detail='Test',issuedAt=100,startsAt=120,expiresAt=200,
                       showOnHome=True,bannerUntil=180)
            try:
                writer.replace_source('test',[event])
                self.assertFalse(engine.snapshot(now=110)['banner'])
                self.assertEqual(engine.next_deadline(110),120)
                self.assertTrue(engine.snapshot(now=120)['banner'])
                self.assertEqual(engine.next_deadline(120),180)
                writer.mark_seen('test:future')
                self.assertTrue(engine.snapshot(now=120)['inbox'][0]['seen'])
                self.assertFalse(engine.snapshot(now=200)['inbox'])
                self.assertTrue(engine.snapshot(now=150)['inbox'])
                self.assertEqual(engine.next_deadline(110),120)
                writer.replace_source('test',[])
                self.assertFalse(engine.snapshot(now=150)['inbox'])
            finally:
                writer.close()
                engine.close()

    def test_match_context_needs_only_selected_facts_and_source_envelope(self):
        from theme_api import normalize_legacy
        match=json.loads((ROOT/'fixtures/sport-normalized-sample.json').read_text())['fixtures'][0]
        for status in ('active','updating','stale','offline','error','unavailable'):
            for data in ({},{'fixtures':[match]}):
                envelope=dict(status=status,source='Fixture',updatedAt=100,checkedAt=110,error='',data=data)
                full=dict(model={'sport':envelope},sportMatch=match)
                compact=dict(full,model={'sport':dict(envelope,data={'available':True} if data else {})})
                self.assertEqual(normalize_legacy('sport.match.detail',full),
                                 normalize_legacy('sport.match.detail',compact))


if __name__=='__main__':unittest.main()
