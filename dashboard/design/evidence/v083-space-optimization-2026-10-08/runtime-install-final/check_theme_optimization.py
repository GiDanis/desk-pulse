"""Regression for standings identity, narrow models and verified latest retention."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from theme_api import normalize_dto, normalize_legacy
from theme_bundle import BundleManager
from theme_core import ThemeError
from theme_lifecycle import LifecycleManager, BASE, selection_key


class OptimizationTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'teamId':'club-'+str(i),'team':'Club '+str(i),'position':i+1,'points':0 if i==0 else i,'played':2} for i in range(20)]
        self.data={'standings':deepcopy(self.rows),'fixtures':[{'canonicalMatchId':'match-'+str(i),'round':'1','homeTeam':'Club A','awayTeam':'Club B'} for i in range(380)]}

    def test_real_provider_identity_and_zero_points(self):
        output=normalize_dto('SportData',self.data)['standings']
        self.assertEqual([x['id'] for x in output],[x['teamId'] for x in self.rows])
        self.assertEqual([x['name'] for x in output],[x['team'] for x in self.rows])
        self.assertEqual(output[0]['entityId'],'club-0')
        self.assertTrue(output[0]['points']['available'])
        self.assertEqual(output[0]['points']['value'],0)
        canonical=normalize_dto('Standing',{'id':'driver','name':'Pilot','team':'Team','entityId':'driver'})
        self.assertEqual(canonical['name'],'Pilot')

    def test_selection_does_not_rebuild_the_season(self):
        cache={}
        payload={'model':{'sport':{'data':self.data,'status':'offline'}}}
        with patch('theme_api.normalize_dto',wraps=normalize_dto) as calls:
            first=normalize_legacy('sport.standings',payload,cache,validate=False)
            self.assertFalse(any(call.args[0]=='MatchData' for call in calls.call_args_list))
            calls.reset_mock()
            second=normalize_legacy('sport.standings',{**payload,'selection':{'index':10},'epoch':10},cache,validate=False)
            self.assertFalse(any(call.args[0]=='Standing' for call in calls.call_args_list))
            self.assertIs(first['standings'],second['standings'])
            changed=deepcopy(payload)
            changed['model']['sport']['data']['standings'].reverse()
            changed['model']['sport']['status']='active'
            third=normalize_legacy('sport.standings',changed,cache,validate=False)
            self.assertEqual(third['standings'][0]['id'],'club-19')
            self.assertEqual(third['source']['status'],'active')

    def test_fixtures_publish_only_the_keyboard_route(self):
        payload={'model':{'sport':{'data':self.data,'status':'offline'}},'rows':self.data['fixtures'][5:8]}
        output=normalize_legacy('sport.fixtures',payload,{},validate=False)
        self.assertEqual([row['id'] for row in output['matches']],['match-5','match-6','match-7'])

    def test_latest_requires_commit_and_keeps_live_leases(self):
        with tempfile.TemporaryDirectory(prefix='smartpc-latest-test-') as private:
            base=Path(private);manager=BundleManager(base/'data')
            project=base/'project';shutil.copytree(Path(__file__).parent/'examples/bundles/studio-ambient',project)
            old=manager.import_bundle(project,preflight=lambda *_:{'status':'passed','testOnly':True},require_preflight=True)
            lifecycle=LifecycleManager(base/'data')
            activation=lifecycle.begin(old);lifecycle.mark_ready(activation['ticket'])
            lifecycle.commit(activation['ticket'],{'coherent':True,'presented':True,'key':selection_key(activation['candidate'])})
            lease=lifecycle.acquire(old)
            p=project/'bundle.json';manifest=json.loads(p.read_text());manifest['version']='9.0.0';manifest['retention']='latest';p.write_text(json.dumps(manifest))
            theme_path=project/'theme.json';theme=json.loads(theme_path.read_text());theme['version']='9.0.0';theme_path.write_text(json.dumps(theme))
            current=manager.import_bundle(project,preflight=lambda *_:{'status':'passed','testOnly':True},require_preflight=True)
            activation=lifecycle.begin(current)
            with self.assertRaises(ThemeError):lifecycle.finalize_latest(current)
            lifecycle.mark_ready(activation['ticket'])
            lifecycle.commit(activation['ticket'],{'coherent':True,'presented':True,'key':selection_key(activation['candidate'])})
            self.assertEqual(len(lifecycle.finalize_latest(current)['retained']),1)
            self.assertEqual(lifecycle.read()['previous'],BASE)
            lifecycle.release(lease)
            self.assertEqual(len(lifecycle.finalize_latest(current)['removed']),1)
            self.assertEqual([row['version'] for row in manager.list_revisions()],['9.0.0'])


if __name__=='__main__':unittest.main()
