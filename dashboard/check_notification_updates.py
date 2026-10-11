"""Offline regressions for delivery deadlines, Serie A deltas and recovery."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer
from account_sync import merge_limits
from event_core import EventEngine
from events import EventService
from football_free import FootballFeed, BSDClient, fixture, load_private
from racing_events import RacingEvents
from racing_timing import F1Timing
from sport_core import ProviderError
from fantacalcio import FantacalcioService

APP = QCoreApplication.instance() or QCoreApplication([])
NOW = 1791626400.0


def notice(identity='test:1', **values):
    return dict(version=1, id=identity, source='test', category='test', priority=2,
                title='Avviso', detail='Dettaglio', issuedAt=NOW, startsAt=NOW,
                expiresAt=NOW+3600, bannerUntil=NOW+180, **values)


def match(identity=1, **values):
    result = dict(id=identity, home_team='Inter', away_team='Roma', home_team_id=7, away_team_id=8,
                  event_date='2026-10-10T10:00:00Z', kickoff=NOW, status='inprogress', home_score=0, away_score=0)
    result.update(values)
    return result


class Updates(unittest.TestCase):
    def test_full_feed_keeps_source_age_and_avoids_unchanged_cache_writes(self):
        from football_free import atomic_json
        class Client:
            requests = bytes = 0
            def get(self, path, **query):
                self.requests += 1
                row = dict(match(), league_id=4, season_id=1375,
                           last_updated='2026-10-01T10:00:00Z')
                if path == 'leagues/':
                    return {'count':1,'results':[dict(id=4,name='Serie A',country='Italy',
                        is_women=False,is_active=True,current_season=dict(id=1375,name='Serie A 26/27',year=2026,is_current=True))]}
                if path.endswith('/standings/'):
                    return dict(league_id=4,season=dict(id=1375),grouped=False,
                                standings=[{} for _ in range(20)])
                if path.endswith('/incidents/'):
                    return dict(event_id=1,incidents=[])
                if path == 'events/live/':
                    return {'count':1,'events':[row]}
                return {'count':1,'results':[row]}
        with tempfile.TemporaryDirectory() as d, patch('football_free.atomic_json', wraps=atomic_json) as save:
            feed=FootballFeed(Client(),d)
            first=feed.refresh(NOW)
            second=feed.refresh(NOW+30)
            self.assertEqual(save.call_count,1)
            self.assertLess(second['matches'][0]['sourceDataAt'],NOW-86400)
            self.assertEqual(first['matches'][0]['dataChangedAt'],second['matches'][0]['dataChangedAt'])
            self.assertEqual(second['matches'][0]['fetchedAt'],NOW+30)
            self.assertFalse(second['notices'])
            feed.refresh(NOW+300)
            self.assertEqual(save.call_count,2)

    def test_bulletin_revision_replays_only_meaningful_changes(self):
        e=EventEngine(':memory:')
        event=notice(noticeRevision='orange:wind:day', revision='bulletin-1')
        e.replace_source('test',[event]);e.mark_notified(event['id']);e.mark_seen(event['id'])
        e.replace_source('test',[dict(event,revision='bulletin-2')])
        self.assertFalse(e.snapshot(now=NOW)['banner'])
        self.assertEqual(e.snapshot(now=NOW)['unreadCount'],0)
        e.replace_source('test',[dict(event,noticeRevision='orange:wind,rain:day',revision='bulletin-3')])
        self.assertEqual(e.snapshot(now=NOW)['banner']['id'],event['id'])
        self.assertEqual(e.snapshot(now=NOW)['unreadCount'],1)
        e.close()

    def test_football_timer_discards_slot_return_value(self):
        from football import FootballService
        with tempfile.TemporaryDirectory() as d:
            service=FootballService(directory=d,auto_refresh=False)
            loop=QEventLoop()
            service.timer.start(1)
            QTimer.singleShot(20,loop.quit)
            loop.exec()
            self.assertFalse(service.timer.isActive())
            self.assertIsNone(service.worker)
            service.close()

    def test_history_and_unread_are_independent_of_view_limit(self):
        e = EventEngine(':memory:')
        values = [notice(f'test:{i}') for i in range(150)]
        e.replace_source('test', values)
        self.assertEqual(e.snapshot(now=NOW)['unreadCount'],150)
        self.assertEqual(len(e.snapshot(now=NOW)['inbox']),100)
        e.mark_notified('test:1')
        self.assertEqual(e.snapshot(now=NOW)['unreadCount'],150)
        e.replace_source('test', [])
        self.assertFalse(e.snapshot(now=NOW)['inbox'])
        self.assertTrue(e.snapshot(now=NOW, history=True)['inbox'][0]['cancelled'])
        self.assertEqual(e.snapshot(now=NOW+8*86400, history=True)['inbox'],[])
        e.close()

    def test_quiet_recovery_does_not_replay_stale_sport_banners(self):
        e=EventEngine(':memory:');e.replace_source('test',[notice()])
        self.assertEqual(e.snapshot(now=NOW, quiet=True)['banner'],{})
        self.assertEqual(e.snapshot(now=NOW+181)['banner'],{})
        self.assertEqual(len(e.snapshot(now=NOW+181)['inbox']),1)
        self.assertEqual(e.next_deadline(NOW),NOW+180)
        e.close()

    def test_pending_banner_is_not_lost_beyond_the_inbox_limit(self):
        with patch('events.time.time',return_value=NOW):
            s=EventService(path=':memory:',auto_refresh=False);s.set_quiet(False,0,1)
            s.setPresentationAcknowledgement(True);s.setBannerAvailable(True)
            values=[notice(f'test:{i}',notificationRank=3 if i>0 else 2) for i in range(150)]
            s.publish_snapshot('test',values)
            self.assertTrue(s.eventState['visibleBanner'])
            self.assertFalse(s._banner_timer.isActive())
            v=s.eventState['visibleBanner'];self.assertTrue(s.markBannerPresented(v['id']))
            s.toggleHistory();self.assertEqual(s.eventState['visibleBanner']['id'],v['id'])
            s.close()

    def test_account_warning_and_critical_have_separate_delivery(self):
        with patch('events.time.time',return_value=NOW):
            s=EventService(path=':memory:',auto_refresh=False);s.set_quiet(False,0,1)
            state={'status':'active','updatedAt':NOW,'data':{'windows':[{'usedPercent':81,'resetsAt':NOW+3600,'windowDurationMins':300}]}}
            s.ingest_account(state,80,95);v=s.eventState['banner'];self.assertEqual(v['notificationRank'],2)
            s._engine.mark_notified(v['id']);state['data']['windows'][0]['usedPercent']=96
            s.ingest_account(state,80,95);self.assertEqual(s.eventState['banner']['notificationRank'],3)
            s.close()

    def test_all_matches_and_score_corrections_without_false_confirmation(self):
        with tempfile.TemporaryDirectory() as d:
            f=FootballFeed(None,d)
            for i in (1,2,3):
                old=match(i);new=match(i,home_score=1)
                f.compare(old,new,[{'type':'goal','home_score':1,'away_score':0,'confirmed':True}],NOW)
            self.assertEqual(len(f.notices),3)
            self.assertTrue(all('segnalato' in v['title'] for v in f.notices.values()))
            f.compare(match(2,home_score=1),match(2),[],NOW+10)
            self.assertEqual(sum(v['type']=='score' for v in f.notices.values()),2)
            self.assertTrue(any(v['type']=='correction' for v in f.notices.values()))
            size=len(f.notices);f.compare(match(4),match(4,home_score=2),[],NOW+20,silent=True)
            self.assertEqual(len(f.notices),size)
            f.compare(match(5),match(5,home_score=2),[],NOW+20)
            self.assertIn('Risultato aggiornato',list(f.notices.values())[-1]['title'])
            f.compare(match(6),match(6,status='finished'),[],NOW+30)
            self.assertEqual(list(f.notices.values())[-1]['type'],'end')

    def test_quota_survives_restart_and_respects_remaining(self):
        with tempfile.TemporaryDirectory() as d, patch('football_free.time.time',return_value=NOW):
            transport=lambda url: ({'ok':True},{'RateLimit':'"football";r=499;t=100'})
            c=BSDClient('private',d,transport);c.get('events/live/')
            self.assertEqual(c.requests,1)
            restarted=BSDClient('private',d,transport)
            with self.assertRaises(ProviderError): restarted.get('events/live/')
            self.assertEqual(restarted.requests,0)

    def test_wrong_identity_null_score_and_private_configuration(self):
        raw=match(league_id=4,season_id=12,home_score=None,away_score=None)
        self.assertIsNone(fixture(raw,4,12)['home_score'])
        with self.assertRaises(ValueError):fixture(raw,5,12)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'token.json';p.write_text('{"token":"abcdefgh1234"}');p.chmod(0o644)
            with self.assertRaises(ValueError):load_private(p)
            p.chmod(0o600);self.assertTrue(load_private(p))

    def test_racing_baseline_session_changes_and_specific_flags(self):
        t=RacingEvents('f1');v=dict(eventId='gp',sessionId='race',active=True,status='Started',fetchedAt=NOW,name='Gara')
        red={'1':{'Scope':'Track','Flag':'RED','Message':'RED FLAG'}}
        self.assertEqual(t.update(v,NOW,red),[])
        notices=t.update(dict(v,fetchedAt=NOW+1),NOW+1,{**red,'2':{'Scope':'Track','Flag':'RED','Message':'RED FLAG'}})
        self.assertEqual(len(notices),1)
        self.assertEqual(t.update(dict(v,sessionId='qualifying',fetchedAt=NOW+2),NOW+2,red),notices)
        t.update(dict(v,sessionId='qualifying',active=False,status='Finished',fetchedAt=NOW+3),NOW+3,red)
        self.assertEqual(len(t.notices),2)

    def test_partial_account_delta_preserves_other_buckets(self):
        old={'rateLimitsByLimitId':{'a':{'limitId':'a','primary':{'usedPercent':20},'secondary':{'usedPercent':10}},'b':{'limitId':'b'}}}
        new=merge_limits(old,{'params':{'rateLimits':{'limitId':'a','primary':{'usedPercent':30}}}})
        self.assertEqual(new['rateLimitsByLimitId']['a']['secondary'],old['rateLimitsByLimitId']['a']['secondary'])
        self.assertIn('b',new['rateLimitsByLimitId']);self.assertNotEqual(old,new)

    def test_f1_delta_publishes_a_consolidated_signal_but_heartbeat_does_not(self):
        f=F1Timing();f._ping.stop()
        f._message('{"type":1,"arguments":["Heartbeat",{}]}\u001e')
        self.assertFalse(f._publish.isActive())
        f._message('{"type":1,"arguments":["SessionStatus",{"Status":"Started"}]}\u001e')
        self.assertTrue(f._publish.isActive());f.close()

    def test_fantasy_never_rearms_on_success_failure_or_leave(self):
        with tempfile.TemporaryDirectory() as d:
            f=FantacalcioService(d,auto_refresh=True)
            f.key='2026-27/5';f.match={'canonicalMatchId':'one'};f.requested_match='one'
            class W: key='2026-27/5';cache_error=''
            f.worker=W();f._finished(None,ProviderError('offline'))
            self.assertFalse(f.timer.isActive())
            f.worker=W();f.clear();f._finished(None,ProviderError('offline'))
            self.assertFalse(f.timer.isActive());self.assertFalse(f.key);f.close()


if __name__=='__main__': unittest.main()
