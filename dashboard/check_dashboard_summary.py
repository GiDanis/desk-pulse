"""Qualification of dashboard priorities, missing values and mixed freshness."""
import unittest
from dashboard_summary import build_summary, environment_devices


class DashboardSummaryTests(unittest.TestCase):
    def project(self, view, data, status='active', **extra):
        envelope = {'status': status, 'source': 'fixture', 'updatedAt': 1000, 'data': data}
        payload = {**extra}
        model = {}
        if view.startswith('sport-'):
            payload['dashboardSport' if view in ('sport-sport', 'sport-team') else 'dashboardRacing'] = envelope
        elif view.startswith('casa-'):
            model['casa'] = envelope
        elif view.startswith('rete-'):
            payload['networkState'] = envelope
        else:
            model['weather'] = envelope
        return build_summary(view, payload, model, 1000)

    def test_racing_session_after_event_start_is_not_lost(self):
        data = {'events': [{'id': 'gp', 'name': 'GP', 'start': 900, 'sessions': [
            {'id': 'p', 'name': 'Prove', 'start': 900}, {'id': 'q', 'name': 'Qualifiche', 'start': 1200},
            {'id': 'race', 'name': 'Gara', 'start': 1800}]}]}
        result = self.project('sport-f1', data)
        self.assertEqual(result['eventId'], 'gp')
        self.assertEqual(result['sessionId'], 'q')
        self.assertEqual(result['cards'][0]['title'], 'Qualifiche')

    def test_racing_clock_never_proves_live(self):
        data = {'events': [{'id': 'gp', 'sessions': [{'id': 'race', 'start': 990}]}],
                'live': {'active': True, 'isLive': True, 'rows': [{'name':'Driver'}], 'eventId': 'gp', 'sessionId': 'race'}}
        for status, verified in [('active', False), ('offline', True), ('stale', True)]:
            data['liveVerified'] = verified
            result = self.project('sport-f1', data, status)
            self.assertFalse(any(c['value'] == 'In diretta' for c in result['cards']))

    def test_verified_racing_live_precedes_future(self):
        data = {'liveVerified': True, 'events': [{'id': 'gp', 'sessions': [
            {'id': 'live', 'name': 'Gara', 'start': 990}, {'id': 'next', 'start': 1200}]}],
                'live': {'active': True, 'isLive': True, 'rows': [{'name':'Driver'}], 'eventId': 'gp', 'sessionId': 'live'}}
        self.assertEqual(self.project('sport-f1', data)['cards'][0]['value'], 'In diretta')

    def test_missing_score_and_real_zero_are_distinct(self):
        data = {'lastFinished': [{'canonicalMatchId': 'a', 'status': 'finished', 'homeScore': 0, 'awayScore': None}]}
        self.assertEqual(self.project('sport-sport', data)['cards'][0]['value'], '0 – —')

    def test_cancelled_match_not_next(self):
        data = {'fixtures': [{'canonicalMatchId': 'a', 'kickoffUtc': 1200, 'status': 'cancelled'},
                             {'canonicalMatchId': 'b', 'kickoffUtc': 1300, 'status': 'scheduled'}]}
        self.assertEqual(self.project('sport-sport', data)['cards'][0]['id'], 'b')

    def test_league_priority_is_independent_of_favourite(self):
        rows = [{'canonicalMatchId': 'first', 'status': 'scheduled', 'kickoffUtc': 1100, 'homeTeamId': 'other'},
                {'canonicalMatchId': 'favourite', 'status': 'scheduled', 'kickoffUtc': 1300, 'homeTeamId': 'inter'}]
        data = {'fixtures': rows, 'favouriteTeamId': 'inter'}
        self.assertEqual(self.project('sport-sport', data)['eventId'], 'first')
        self.assertEqual(self.project('sport-team', data)['eventId'], 'favourite')
        data['favouriteTeamId'] = 'other'
        self.assertEqual(self.project('sport-sport', data)['eventId'], 'first')

    def test_team_dashboard_never_shows_another_club_match(self):
        data = {'favouriteTeamId': 'inter', 'fixtures': [
            {'canonicalMatchId': 'other', 'status': 'scheduled', 'kickoffUtc': 1100, 'homeTeamId': 'milan'}]}
        result = self.project('sport-team', data)
        self.assertNotIn('eventId', result)
        self.assertFalse(any(c['id'] == 'other' for c in result['cards']))

    def test_league_leader_and_favourite_standing_are_separate(self):
        data = {'favouriteTeamId': 'inter', 'standings': [
            {'teamId': 'napoli', 'team': 'Napoli', 'position': 1, 'points': 20},
            {'teamId': 'inter', 'team': 'Inter', 'position': 4, 'points': 12}]}
        self.assertEqual(self.project('sport-sport', data)['cards'][0]['title'], 'Napoli')
        self.assertEqual(self.project('sport-team', data)['cards'][0]['title'], 'Inter')

    def test_no_favourite_has_explicit_team_prompt(self):
        result = self.project('sport-team', {})
        self.assertEqual(result['title'], 'La mia squadra')
        self.assertEqual(result['cards'][0]['id'], 'choose-team')

    def test_environment_uses_verified_codes_not_names(self):
        data = {'devices': [{'id': 'fake', 'name': 'Temperatura salotto', 'metrics': []},
                            {'id': 'raw', 'metrics': [{'code': 'va_temperature', 'quality': 'unverified'}]},
                            {'id': 'real', 'name': 'Sensore', 'metrics': [{'code': 'va_temperature', 'quality': 'reported',
                             'value': 0, 'displayText': '0 °C', 'previous': True}]}]}
        self.assertEqual([r['id'] for r in environment_devices(data)], ['real'])
        summary = self.project('casa-ambiente', data)
        self.assertEqual(summary['cards'][0]['value'], '0 °C')
        self.assertTrue(summary['cards'][0]['previous'])

    def test_saved_online_not_counted_current(self):
        data = {'devices': [{'id': 'a', 'online': True, 'availabilityPrevious': True},
                            {'id': 'b', 'online': False, 'availabilityPrevious': False}]}
        self.assertEqual(self.project('casa-dispositivi', data)['cards'][1]['value'], '0')
        data['devices'][1]['availabilityPrevious'] = True
        self.assertEqual(self.project('casa-dispositivi', data)['cards'][1]['value'], '—')

    def test_unknown_cloud_availability_is_not_zero(self):
        data={'devices':[{'id':'a','online':None,'availabilityPrevious':False}]}
        self.assertEqual(self.project('casa-dispositivi',data)['cards'][1]['value'],'—')

    def test_two_favourites_use_full_height(self):
        data={'favourites':[{'id':'a','name':'A'},{'id':'b','name':'B'}]}
        result=self.project('casa-preferiti',data)
        self.assertEqual([c['rect']['height'] for c in result['cards']],[504,504])

    def test_soccer_fresh_in_progress_precedes_future_without_false_live(self):
        data={'activeMatches':[{'canonicalMatchId':'a','status':'live','isLive':False,'fresh':True,'kickoffUtc':990,'homeScore':0,'awayScore':1,'minute':'12'}],
              'fixtures':[{'canonicalMatchId':'b','status':'scheduled','kickoffUtc':1200}]}
        self.assertEqual(self.project('sport-sport',data)['eventId'],'a')
        self.assertEqual(self.project('sport-sport',data)['cards'][0]['title'],'In corso')
        self.assertEqual(self.project('sport-sport',data)['cards'][0]['value'],'0 – 1')
        self.assertEqual(self.project('sport-sport',data,'updating')['eventId'],'a')
        self.assertEqual(self.project('sport-sport',data,'offline')['eventId'],'b')
        data['activeMatches'][0]['fresh']=False
        self.assertEqual(self.project('sport-sport',data)['eventId'],'b')

    def test_completed_qualifying_precedes_next_race(self):
        data={'events':[{'id':'gp','sessions':[{'id':'q','start':900,'name':'Qualifiche','state':'finished','results':[{'name':'Driver','value':'1:20'}]},
                                             {'id':'race','start':1200,'name':'Gara'}]}]}
        result=self.project('sport-f1',data)
        self.assertEqual(result['sessionId'],'q')
        self.assertEqual(result['mode'],'results')
        self.assertEqual(result['cards'][0]['value'],'Terminata')
        self.assertEqual(result['cards'][2]['title'],'Prossima sessione')

    def test_finished_timing_is_visible_without_live_label(self):
        data={'events':[{'id':'gp','sessions':[{'id':'q','start':900,'name':'Qualifiche'}, {'id':'race','start':1200}]}],
              'live':{'active':False,'isLive':False,'status':'Finished','eventId':'gp','sessionId':'q','rows':[{'name':'Driver','value':'1:20'}]}}
        result=self.project('sport-f1',data)
        self.assertEqual(result['sessionId'],'q')
        self.assertEqual(result['mode'],'timing')
        self.assertEqual(result['cards'][0]['value'],'Terminata')
        self.assertTrue(result['cards'][1]['previous'])

    def test_racing_waiting_for_results_does_not_invent_live(self):
        data={'events':[{'id':'gp','sessions':[{'id':'q','start':-7000,'name':'Qualifiche'}, {'id':'race','start':1200}]}]}
        result=self.project('sport-f1',data)
        self.assertEqual(result['sessionId'],'q')
        self.assertEqual(result['mode'],'pending')
        self.assertEqual(result['cards'][0]['value'],'In attesa')

    def test_reachability_is_not_total_inventory(self):
        data = {'hasInventory': True, 'devices': [{'id': 'a', 'name': 'A', 'statusText': 'Raggiungibile secondo box', 'previous': True},
                                                {'id': 'b', 'name': 'B', 'statusText': 'Non raggiungibile secondo box', 'previous': False}]}
        result = self.project('rete-dispositivi', data)
        self.assertEqual(result['cards'][0]['value'], '2')
        self.assertEqual(result['cards'][1]['value'], '0')

    def test_wan_freshness_is_local(self):
        router = {'summary': 'FTTH · up', 'rows': [{'id': 'wan:down', 'value': '0 Mbit/s', 'previous': False},
                                                  {'id': 'wan:up', 'value': '2 Mbit/s', 'previous': True}]}
        result = self.project('rete-traffico', {}, dashboardRouter=router)
        self.assertEqual(result['cards'][0]['value'], '0')
        self.assertEqual(result['cards'][0]['unit'], 'Mbit/s')
        self.assertFalse(result['cards'][0]['previous'])
        self.assertTrue(result['cards'][1]['previous'])

    def test_account_details_keep_previous_source_and_real_zero(self):
        from theme_api import normalize_legacy
        model={'account':{'status':'offline','source':'Account fixture','updatedAt':900,'data':{
            'windows':[{'label':'5 ore','usedPercent':0,'windowDurationMins':300}],
            'credits':{'unlimited':False,'balance':0}}}}
        result=normalize_legacy('overlay.summary',{'familyId':'account','model':model})
        self.assertEqual(result['rows'][0]['value'],'0%')
        self.assertEqual(next(r for r in result['rows'] if r['id']=='credits')['value'],'0')
        self.assertTrue(all('Dato precedente' in r['detail'] and 'Account fixture' in r['detail'] for r in result['rows']))

    def test_layout_has_no_unused_lower_quadrant(self):
        data = {'events': [{'id': 'gp', 'name': 'GP', 'circuit': 'Circuito', 'sessions': [
            {'id': 'q', 'name': 'Qualifiche', 'start': 1200}, {'id': 'race', 'name': 'Gara', 'start': 1800}]}],
                'standings': [{'name': 'Pilota', 'points': 10}]}
        result = self.project('sport-f1', data)
        self.assertEqual(len(result['cards']), 4)
        self.assertEqual(sum(c['rect']['width'] * c['rect']['height'] for c in result['cards']), 400*504 + 496*244 + 2*240*244)
        for c in result['cards']:
            r = c['rect']
            self.assertLessEqual(r['x'] + r['width'], 912)
            self.assertLessEqual(r['y'] + r['height'], 504)


if __name__ == '__main__':
    unittest.main()
