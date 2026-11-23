"""Promotion rejects real partial/development runs, mismatched identities and safety loss."""
from copy import deepcopy
import unittest
from game_lab.qualification import qualify,package


class PromotionChecks(unittest.TestCase):
    def test_attack_latency_uses_offered_approaches_and_counts_unanswered(self):
        def campaign(unanswered=False):
            runs=[]
            for seed in range(5):
                rows=[]
                for family,bots in [('solo',1),('attack',1),('complete',1),('corner',1),('defend',1),('recover',1),('traffic',1),('traffic',2),('traffic',3)]:
                    opportunities=[dict(kind='already-alongside',latency=None)] if family=='complete' else [dict(kind='approach',latency=None if unanswered else 1.)] if family=='attack' else []
                    rows.append(dict(seed=seed,family=family,bots=bots,duration=180.,cleanPass=True,clean=True,windowComplete=True,cleanLaps=5,flyingMedian=20.,firstPass=4.,
                        result=dict(contacts=0,trackLimits=0,attack=dict(opportunityEvents=opportunities,queueSeconds=0.,idleAlongsideSeconds=0.))))
                base=deepcopy(rows)
                for row in base:row['firstPass']=5.
                bank=dict(split='final',hash='synthetic-test-only',cases=[{k:r[k] for k in ('seed','family','bots','duration')} for r in rows])
                runs.append(dict(preparationSeed=seed,datasetHash=str(seed),baseHash='base',candidateHash='candidate',referenceSoloMedian=20.,
                    baseEvaluation=dict(bank=bank,policyHash='base',rows=base),candidateEvaluation=dict(bank=bank,policyHash='candidate',rows=rows),
                    races=[dict(cars=n,complete=True,laps=3,allCarsVisible=True) for n in (2,5)]))
            return runs
        self.assertTrue(qualify(campaign())['qualified'])
        self.assertTrue(any('Attack latency' in f for f in qualify(campaign(True))['failures']))
        for family in ('solo','defend','recover'):
            broken=campaign()
            for run in broken:
                row=next(r for r in run['candidateEvaluation']['rows'] if r['family']==family);row['windowComplete']=False
            self.assertFalse(qualify(broken)['qualified'])
            self.assertTrue(any(family.capitalize()+' competence' in f or family+' competence' in f for f in qualify(broken)['failures']))

    def test_development_cannot_hide_defense_or_slow_solo_and_grid_gets_time(self):
        from game_protocol import finish_window
        self.assertAlmostEqual(finish_window([23.5,35.7],3),72.3)
        self.assertGreaterEqual(3*23.5+finish_window([23.5,35.7],3),4*35.7)
        self.assertEqual(finish_window([],3),30.)
        with self.assertRaises(ValueError):finish_window([float('nan')],3)
        from game_lab.readiness import base_readiness
        runs=[]
        for seed in range(5):
            cases=[dict(seed=i,family=f,bots=n,duration=180.,clean=True,windowComplete=True,cleanPass=True,cleanLaps=5,flyingMedian=20.,result=dict(contacts=0,trackLimits=0),firstPass=4.)
                for i,(f,n) in enumerate([('solo',1),('attack',1),('complete',1),('corner',1),('defend',1),('recover',1),('traffic',1),('traffic',2),('traffic',3)])]
            runs.append(dict(preparationSeed=seed,datasetHash=str(seed),referenceSoloMedian=20.,evaluation=dict(bank=dict(split='development',hash='synthetic-only',cases=cases),rows=deepcopy(cases))))
        self.assertTrue(base_readiness(runs)['readyForFinal'])
        next(c for c in runs[0]['evaluation']['rows'] if c['family']=='defend')['clean']=False
        self.assertFalse(base_readiness(runs)['readyForFinal'])
        self.assertIn('defend competence',base_readiness(runs)['rows'][0]['issues'])
        next(c for c in runs[1]['evaluation']['rows'] if c['family']=='solo')['flyingMedian']=21.
        self.assertIn('Common solo reference',base_readiness(runs)['rows'][1]['issues'])

    def test_an_empty_or_development_campaign_cannot_promote(self):
        self.assertFalse(qualify([])['qualified'])
        report=qualify([dict(preparationSeed=i,datasetHash=str(i),baseEvaluation={'bank':{'split':'development'}},candidateEvaluation={'bank':{'split':'development'}}) for i in range(5)])
        self.assertFalse(report['qualified']);self.assertTrue(any('Final bank' in f for f in report['failures']))
        with self.assertRaises(ValueError):package({},report,context={},selected_seed=0)

    def test_five_continuations_of_one_preparation_are_rejected(self):
        report=qualify([dict(preparationSeed=1,datasetHash='same') for _ in range(5)])
        self.assertFalse(report['qualified'])
        self.assertTrue(any('distinct preparation datasets' in f for f in report['failures']))


if __name__=='__main__':unittest.main()
