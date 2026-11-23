"""Promotion, migration, paired worlds and durable evaluation boundaries."""
import json
import tempfile
import unittest
import numpy as np
from game_curriculum import Evaluation, initial_state, consider, summary, pace_weight
from game_learning import Evolution
from game_store import GameStore,default_profile
from game_simulation import World,reference_actions


def result(valid=10,time=40):
    return summary([{'status':'arrivato' if i<valid else 'ritirato','time':time+i*.01 if i<valid else None,
                     'progress':300,'seed':i} for i in range(10)])


class CurriculumChecks(unittest.TestCase):
    def test_faster_failures_do_not_replace_champion(self):
        state=initial_state();policy=Evolution(default_profile()).policy()
        promoted,changed,_=consider(state,policy,result(),None,list(range(10)),'scope')
        self.assertTrue(promoted);self.assertFalse(changed)
        original=json.loads(json.dumps(state['champion']))
        promoted,changed,_=consider(state,policy,result(8,20),result(),list(range(10,20)),'scope')
        self.assertFalse(promoted);self.assertFalse(changed);self.assertEqual(state['champion'],original)
        promoted,_,_=consider(state,policy,result(10,39.99),result(10,40),list(range(20,30)),'scope')
        self.assertFalse(promoted)
        promoted,_,proof=consider(state,policy,result(10,35),result(10,40),list(range(30,40)),'scope')
        self.assertTrue(promoted);self.assertEqual(proof['champion']['median']-proof['candidate']['median'],5)

    def test_phase_requires_independent_reliable_windows(self):
        state=initial_state();policy=Evolution(default_profile()).policy()
        consider(state,policy,result(9),None,list(range(10)),'scope')
        self.assertEqual(state['phase'],'control')
        state['round']+=1
        _,changed,_=consider(state,policy,result(9),result(9),list(range(10,20)),'scope')
        self.assertTrue(changed);self.assertEqual(state['phase'],'pace')
        self.assertEqual(pace_weight(state),0)
        state['phaseUpdates']=4;self.assertEqual(pace_weight(state),.5)

    def test_paired_evaluation_resume_and_training_rng_isolation(self):
        policy=Evolution(default_profile()).policy()
        a=Evaluation(policy,policy,3)
        for _ in range(70):a.step()
        saved=json.loads(json.dumps(a.snapshot()));b=Evaluation(policy,policy,3,saved=saved)
        for _ in range(50):a.step();b.step()
        self.assertEqual(a.snapshot(),b.snapshot())
        for first,second in zip(a.worlds,b.worlds):np.testing.assert_array_equal(first.state,second.state)
        self.assertEqual(a.worlds[0].snapshot(),a.worlds[1].snapshot())
        self.assertNotEqual(a.scenarios,Evaluation(policy,round_number=4).scenarios)
        for traffic in (False,True):
            ev=Evaluation(policy,policy,traffic=traffic)
            self.assertEqual(len(ev.results()[0]['results']),10)
            for _ in range(3):ev.step()
            restored=Evaluation(policy,policy,traffic=traffic,saved=json.loads(json.dumps(ev.snapshot())))
            self.assertEqual(restored.snapshot(),ev.snapshot())

    def test_migration_and_atomic_proof_keep_legacy_policy(self):
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);driver=store.drivers()[0];policy=Evolution(driver['profile']).policy()
            legacy=store.save_training(driver['id'],{},policy,10,1)
            state=initial_state()
            candidate={**policy,'weights':[-w for w in policy['weights']]}
            store.save_training(driver['id'],{'curriculum':state},candidate,20,2,curriculum=state)
            row=store.driver(driver['id']);self.assertEqual(row['policy'],legacy)
            self.assertNotEqual(row['candidate'],legacy);self.assertIsNone(row['curriculum']['champion'])
            consider(state,candidate,result(),None,list(range(10)),'scope')
            store.save_training(driver['id'],{'curriculum':state},candidate,30,3,curriculum=state)
            row=GameStore(root).driver(driver['id']);self.assertEqual(store.load(row['policy']),candidate)
            self.assertTrue(row['curriculum']['champion']);self.assertEqual(len([e for e in store.history(driver['id']) if e['kind']=='evaluation']),1)
            store.set_profile(driver['id'],{**driver['profile'],'seed':42},allow_reconfigure=True)
            row=store.driver(driver['id']);self.assertIsNone(row['checkpoint']);self.assertIsNone(row['curriculum'])
            self.assertEqual(store.load(row['policy']),candidate)

    def test_pace_reward_does_not_change_physics(self):
        a,b=World(),World()
        totals=np.zeros(2)
        for _ in range(250):
            action=reference_actions(a)
            totals[0]+=a.step(action)[1][0];totals[1]+=b.step(action,pace=1)[1][0]
        np.testing.assert_array_equal(a.state,b.state)
        self.assertEqual(a.snapshot(),b.snapshot());self.assertGreater(totals[0],totals[1])


if __name__=='__main__':unittest.main()
