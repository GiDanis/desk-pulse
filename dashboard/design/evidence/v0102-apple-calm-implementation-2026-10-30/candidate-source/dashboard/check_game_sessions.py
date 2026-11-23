"""Session contracts, actual lap qualification, objective resume and reset identity."""
import tempfile
import unittest
import json
from copy import deepcopy
import numpy as np
from game_modes import MODES,qualified_snapshot,grid_order
from game_academy import Episode,academy_profile
from game_academy_trainer import AcademyTrainer
from game_profiles import preset,reference_policy
from game_learning import Policy
from game_catalog import configuration,scope_hash,race_eligible,RACE_PHYSICS_VERSION
from game_control import racing_actions
from game_simulation import World,DT
from game_store import GameStore
from game_results import exercise

class SessionChecks(unittest.TestCase):
    def test_five_modes_and_no_legacy_race_bypass(self):
        self.assertEqual(len(MODES),5)
        for algorithm in ('evolution','pure_pursuit'):
            self.assertFalse(race_eligible(dict(profile=preset(1,algorithm),policy='old'), 'oval-1'))

    def test_neat_attempts_keep_population_through_verification_and_reset_short_distance(self):
        t=AcademyTrainer(academy_profile(preset(3,'neat')),'oval-1',view='attempts')
        before=t.checkpoint(0);rows,_,meta=t.frame('Neat',2,0)
        self.assertEqual((len(rows),meta['presentation']),(32,'population'))
        t.episodes[0].reset();next_rows,_,_=t.frame('Neat',2,0)
        self.assertNotEqual(rows[0]['resetKey'],next_rows[0]['resetKey'])
        t.review=type('Review',(),dict(episodes=t.episodes,cursor=0,kind='familiarization'))()
        visible,_,meta=t.frame('Neat',2,0)
        self.assertEqual(len(visible),32)
        self.assertEqual(meta['presentation'],'population')
        self.assertEqual(t.steps,before['steps'])

    def test_watched_neat_never_changes_fitness_or_population_rng(self):
        t=AcademyTrainer(academy_profile(preset(3,'neat')),'oval-1')
        before=t.checkpoint(0)
        for _ in range(4):
            t.last_preview-=DT;t.advance_preview();rows,_,meta=t.frame('Neat',2,0)
        self.assertEqual(meta['presentation'],'preview');self.assertEqual(len(rows),1)
        self.assertGreater(t.preview.world.time,0)
        self.assertEqual(t.checkpoint(0),before)

    def test_infinite_crosses_four_laps_without_finish_and_has_bounded_history(self):
        e=Episode('oval-1','control',4,objective='impara_infinito')
        for _ in range(12000):
            e.step(racing_actions(e.world,[0])[0])
            if e.world.checkpoint[0]>=16:break
            if e.reason=='window':e.next_window()
            self.assertFalse(e.reason,e.result())
        self.assertGreaterEqual(e.world.checkpoint[0],16)
        self.assertTrue(e.world.active[0]);self.assertFalse(np.isfinite(e.world.finish[0]))
        self.assertEqual(len(e.world.lap_times[0]),4)
        saved=json.loads(json.dumps(e.snapshot(),allow_nan=False))
        restored=Episode('oval-1','control',4,saved=saved)
        self.assertEqual(restored.snapshot(),saved)
        self.assertTrue(restored.world.continuous)

    def test_external_window_bootstraps_and_does_not_teleport_ppo_world(self):
        e=Episode('oval-1','control',4,objective='impara_infinito')
        e.spec['limitSeconds']=DT
        _,_,done,terminal=e.step([0,1])
        self.assertTrue(done);self.assertFalse(terminal);self.assertEqual(e.reason,'window')
        pose=e.world.state.copy();time=e.world.time;revision=e.revision
        observation=e.observations().copy();age=e.age
        e.next_window()
        self.assertEqual(e.age,age)
        np.testing.assert_array_equal(e.observations(),observation)
        np.testing.assert_array_equal(e.world.state,pose)
        self.assertEqual((e.world.time,e.revision),(time,revision))
        self.assertFalse(e.reason)

    def test_continuous_demo_declares_policy_switch_at_window_without_resetting_pose(self):
        from unittest.mock import patch
        t=AcademyTrainer(academy_profile(preset(3,'ppo')),'oval-1',objective='impara_infinito')
        t.prepare_preview();e=t.preview;e.reason='window';e.truncated=True
        pose=e.world.state.copy();revision=e.revision;old=deepcopy(t.preview_policy.snapshot)
        t.learner.actor[-1]+=.5;t.preview_remaining=0.
        with patch('game_academy_trainer.time.monotonic',return_value=t.last_preview):t.advance_preview()
        self.assertNotEqual(t.preview_policy.snapshot,old)
        self.assertEqual(t.preview_switch['reason'],'new-controller-at-window')
        np.testing.assert_array_equal(e.world.state,pose);self.assertEqual(e.revision,revision)

    def test_continuous_bot_teacher_observes_lapped_traffic_physically(self):
        w=World(2,1,shared=True,track_id='oval-1',physics=RACE_PHYSICS_VERSION)
        w.continuous=True
        w.state[0,:3]=w.track.pose(0,0);w.state[1,:3]=w.track.pose(12,0)
        w.state[:,3]=[15,4];w.progress[:]=[0,12];lane=w.racing_lane.copy()
        expected=racing_actions(w,[0]);w.progress[0]+=w.track.length;w.racing_lane=lane.copy()
        np.testing.assert_array_equal(racing_actions(w,[0]),expected)

    def test_objective_checkpoint_preserves_main_path_and_resumes_exactly(self):
        with tempfile.TemporaryDirectory() as root:
            s=GameStore(root);identity=s.drivers()[0]['id'];s.activate_academy(identity);s.prepare_driving(identity)
            original=deepcopy(s.driver(identity))
            t=AcademyTrainer(original['profile'],'oval-1',objective='impara_sorpasso',bots=2)
            for _ in range(34):t.tick()
            s.select_objective('impara_sorpasso')
            s.save_training(identity,t.checkpoint(5),t.learner.policy(),t.steps,5,t.metric,t.state)
            restored=AcademyTrainer(original['profile'],'oval-1',s.objective_checkpoint(identity,'impara_sorpasso'),objective='impara_sorpasso',bots=2)
            self.assertEqual(restored.checkpoint(5),t.checkpoint(5))
            s.select_objective('impara');self.assertEqual(s.driver(identity),original)
            s.reset_all(identity);self.assertIsNone(s.objective_checkpoint(identity,'impara_sorpasso'))

    def test_real_flying_lap_certifies_snapshot_survives_new_training_and_grid_inverts(self):
        with tempfile.TemporaryDirectory() as root:
            s=GameStore(root);drivers=[s.drivers()[0],s.drivers()[1]]
            profile=academy_profile(preset(1,'pure_pursuit'));artifact=reference_policy('oval-1',True);policy=s.artifact(artifact)
            w=World(1,1,laps=3,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True);w.reset(varied=False)
            for _ in range(12000):
                w.step(racing_actions(w),return_observations=False)
                if not w.active.any():break
            self.assertEqual(len(w.lap_times[0]),3)
            for i,d in enumerate(drivers):
                session,payload=s.begin_session('qualifica',dict(participants=[dict(id=d['id'],policy=policy,profile=profile)],profile=profile))
                with self.assertRaises(ValueError):s.record_qualification(d['id'],policy,profile,w.lap_times[0][0],session)
                for lap in w.lap_times[0][1:]:s.record_qualification(d['id'],policy,profile,lap,session)
                self.assertTrue(race_eligible(s.driver(d['id'])))
            fastest=grid_order([s.driver(d['id']) for d in drivers],'oval-1','fastest_first')
            slowest=grid_order([s.driver(d['id']) for d in drivers],'oval-1','slowest_first')
            self.assertEqual(len(fastest),2)
            # Identical measured times use a stable number tie-break in both orders.
            self.assertEqual(fastest[0][0]['id'],drivers[0]['id'])
            old=qualified_snapshot(s.driver(drivers[0]['id']),'oval-1')
            self.assertEqual(old['policy'],policy)
            self.assertIsNone(qualified_snapshot(s.driver(drivers[0]['id']),'technical-1'))
            s.reset_all(drivers[0]['id']);self.assertFalse(race_eligible(s.driver(drivers[0]['id'])))

    def test_technical_summary_exposes_failed_retention_and_untested(self):
        p=dict(phase='recovery',candidate=dict(valid=20,total=20,tested=20,median=4.91,retained=False,results=[dict(goalMeters=40,reason='success')],skills=dict(control=dict(valid=0,total=20,tested=3))))
        r=exercise(p)
        self.assertIn('40 m',r['title']);self.assertIn('tipico 4.91',r['value'])
        self.assertIn('non superata',r['description']);self.assertIn('17 non eseguiti',r['detailRows'][0]['description'])

if __name__=='__main__':unittest.main()
