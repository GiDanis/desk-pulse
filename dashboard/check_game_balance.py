"""Behavioral gates for versioned driving rewards and execution backends."""
from copy import deepcopy
import json
import time
import unittest
import numpy as np
from game_academy import Episode,academy_profile
from game_academy_trainer import AcademyTrainer
from game_profiles import preset
from game_rewards import specification,migrate,TERMS
from game_control import pursuit_actions
from game_native import available,SparsePopulation
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION,ACADEMY_OBSERVATION_VERSION,TRACKS


class BalanceChecks(unittest.TestCase):
    def test_backend_selection_is_limited_to_the_measured_board_and_workload(self):
        from game_parallel import recommended_collectors
        p=academy_profile(preset(7,'ppo'))
        expected=4 if available() else 0
        self.assertEqual(recommended_collectors(p,'oval-1','impara_sorpasso','xunlong,orangepi-4-pro'),expected)
        self.assertEqual(recommended_collectors(p,'oval-1','impara_infinito','xunlong,orangepi-4-pro'),0)
        self.assertEqual(recommended_collectors(p,'technical-1','impara_sorpasso','xunlong,orangepi-4-pro'),0)
        self.assertEqual(recommended_collectors(p,'oval-1','impara_sorpasso','other-board'),0)
        self.assertEqual(recommended_collectors({**p,'population':64},'oval-1','impara_sorpasso','xunlong,orangepi-4-pro'),0)

    def test_start_migration_preserves_each_pilots_weights_and_original_checkpoint(self):
        for method in ('evolution','neat','ppo','ppo_smooth','imitation'):
            p=academy_profile(preset(7,method));old=AcademyTrainer(p,'oval-1')
            saved=old.checkpoint(12.);saved['curriculum']['phase']='control'
            original=deepcopy(saved);new=migrate(saved,p,'impara')
            self.assertEqual(saved,original)
            self.assertEqual(new['steps'],saved['steps']);self.assertEqual(new['seconds'],12.)
            self.assertEqual(new['learner']['rng'] if method!='neat' else new['learner']['random'],
                             saved['learner']['rng'] if method!='neat' else saved['learner']['random'])
            keys={'evolution':('population','best'),'ppo':('actor','logStd'),
                  'ppo_smooth':('actor','logStd'),'imitation':('weights','examples'),'neat':('candidate',)}[method]
            for key in keys:self.assertEqual(new['learner'].get(key),saved['learner'].get(key))
            if method=='neat':
                for a,b in zip(new['learner']['population'],saved['learner']['population']):
                    self.assertEqual(a['nodes'],b['nodes']);self.assertEqual(a['connections'],b['connections'])
            self.assertIsNone(new['episodes']);self.assertEqual(new['curriculum']['phase'],'launch')
            resumed=AcademyTrainer(p,'oval-1',new,balanced=True)
            self.assertEqual(resumed.phase,'launch');self.assertTrue(resumed.learner.driving_balance)
            if method.startswith('ppo'):self.assertEqual(resumed.learner.tuning['gaeLambda'],.99)

    def test_native_sensors_match_numpy_geometry_including_outside_and_boundaries(self):
        if not available():self.skipTest('Prebuilt native kernel absent; NumPy fallback is available')
        rng=np.random.default_rng(844)
        for entry in TRACKS:
            w=World(16,seed=8,track_id=entry['id'],physics=RACE_PHYSICS_VERSION)
            for _ in range(8):
                for i in range(16):
                    w.state[i,:3]=w.track.pose(float(rng.uniform(0,w.track.length)),float(rng.uniform(-9,9)))
                    w.state[i,2]+=rng.uniform(-3.14,3.14)
                if not w.track.oval:w._segments=w.track.project(w.state[:,:2])[3]
                w.native_sensors=False;a=w.observations(version=ACADEMY_OBSERVATION_VERSION)
                w.native_sensors=True;b=w.observations(version=ACADEMY_OBSERVATION_VERSION)
                np.testing.assert_allclose(a,b,rtol=0,atol=1e-10)
                self.assertTrue(np.isfinite(b).all())

    def test_native_neat_keeps_sparse_topologies_and_ordered_activation(self):
        if not available():self.skipTest('Native kernel absent')
        from game_neat import NEAT
        n=NEAT(academy_profile(preset(9,'neat')));rng=np.random.default_rng(82)
        for _ in range(5):
            x=rng.uniform(-1,1,(32,68));expected=np.array([net.activate(row) for net,row in zip(n.networks,x)])
            compiled=SparsePopulation(n.networks,68)
            np.testing.assert_array_equal(expected,compiled.act(x))
            n.update(rng.normal(size=32))

    def test_continuous_clean_laps_are_rewarded_once_without_ending_the_world(self):
        e=Episode('oval-1','control',2000901,protocol='driving-memory-1',objective='impara_infinito',reward_spec=specification())
        while not e.reason:e.step(pursuit_actions(e.world,[0],speed_factor=1.4)[0])
        clean=sum(r['clean'] for r in e.world.lap_times[0])
        self.assertGreaterEqual(clean,2);self.assertEqual(e.reason,'window');self.assertFalse(e.terminated)
        self.assertAlmostEqual(e.term_totals['finish'],3*clean)
        self.assertAlmostEqual(sum(e.term_totals.values()),e.return_total)
        time_before=e.world.time;e.next_window()
        self.assertEqual(e.term_totals['finish'],0.)
        e.step(pursuit_actions(e.world,[0])[0]);self.assertGreater(e.world.time,time_before)
        self.assertEqual(e.term_totals['finish'],0.)

    def test_full_gas_trajectory_receives_early_slip_feedback_without_overriding_action(self):
        e=Episode('oval-1','control',2000901,protocol='driving-memory-1',objective='impara_infinito',reward_spec=specification())
        while not e.reason:
            action=pursuit_actions(e.world,[0])[0];action[1]=1.
            e.step(action)
        self.assertEqual(e.reason,'contact');self.assertGreater(e.understeer_seconds,0.)
        self.assertLess(e.term_totals['understeer'],0.)
        self.assertEqual(e.pedal_counts['brake'],0)
        self.assertEqual(e.term_totals['retirement'],-3.)
        self.assertEqual(e.term_totals['contact'],0.)
        self.assertAlmostEqual(sum(e.term_totals.values()),e.return_total)

    def test_curve_exercises_cover_release_and_braking_scenarios(self):
        braking=[];moving=[]
        for seed in range(8):
            e=Episode('oval-1','bend',seed,protocol='driving-memory-1',reward_spec=specification())
            moving.append(e.world.state[0,3])
            action=e.teacher_actions();braking.append(action[1]<-.05)
        self.assertTrue(any(braking));self.assertTrue(not all(braking))
        self.assertGreater(min(moving),0);self.assertGreater(max(moving)-min(moving),3.)

    def test_generation_exploration_changes_weights_not_runtime_pedals(self):
        from game_learning import Evolution
        p=academy_profile(preset(4));n=Evolution(p);n.driving_balance=True
        n.update(np.arange(32,dtype=float))
        self.assertAlmostEqual(n.population[-2,-1]-n.population[-3,-1],-1.)
        obs=np.zeros((32,68));self.assertEqual(n.act(obs).shape,(32,2))

    def test_batched_integrator_matches_independent_physics_rewards_and_sensors(self):
        from game_batch import BatchPhysics
        for track in ('oval-1','technical-1','varano-short-1','mallory-oval-1'):
            a=[Episode(track,'control',12+i,protocol='driving-memory-1',objective='impara_infinito',reward_spec=specification()) for i in range(4)]
            b=[Episode(track,'control',e.seed,saved=json.loads(json.dumps(e.snapshot()))) for e in a]
            batch=BatchPhysics()
            for _ in range(80):
                actions=np.array([pursuit_actions(e.world,[0])[0] for e in a])
                prepared=batch.prepare(b,actions)
                self.assertTrue(all(r is not None for r in prepared))
                for i,(x,y) in enumerate(zip(a,b)):
                    expected=x.step(actions[i]);actual=y.step(actions[i],physics=prepared[i])
                    self.assertEqual(x.world.snapshot(),y.world.snapshot())
                    np.testing.assert_array_equal(expected[0],actual[0])
                    self.assertEqual(x.return_total,y.return_total)

    def test_batched_pause_preserves_unapplied_physics_and_critic_bootstrap(self):
        p=academy_profile(preset(23,'ppo'))
        a=AcademyTrainer(p,'oval-1',objective='impara_infinito',balanced=True,batched=True)
        while a.steps<3:a.tick()
        saved=json.loads(json.dumps(a.checkpoint(0),allow_nan=False))
        self.assertIsNotNone(saved['physicsResults'])
        b=AcademyTrainer(p,'oval-1',saved,objective='impara_infinito',balanced=True,batched=True)
        while a.steps<32:a.tick()
        while b.steps<32:b.tick()
        self.assertEqual(json.loads(json.dumps(a.checkpoint(0))),json.loads(json.dumps(b.checkpoint(0))))

    def test_clone_numeric_braking_replay_wraps_and_resumes_deterministically(self):
        from game_learning import Imitation
        p=academy_profile(preset(21,'imitation'));a=Imitation(p);a.driving_balance=True
        rng=np.random.default_rng(424)
        for _ in range(70):a.learn_step(rng.normal(size=(32,68)),rng.uniform(-1,1,(32,2)))
        saved=json.loads(json.dumps(a.checkpoint()));self.assertEqual(len(saved['examples']),2240)
        b=Imitation(p,saved);b.driving_balance=True
        for _ in range(8):
            x=rng.normal(size=(32,68));y=rng.uniform(-1,1,(32,2))
            a.learn_step(x,y);b.learn_step(x,y)
        self.assertEqual(a.checkpoint(),b.checkpoint())

    def test_persistent_envs_match_serial_rewards_models_and_pending_resume(self):
        for batched,method in ((b,m) for b in (False,True) for m in ('evolution','neat','ppo','ppo_smooth','imitation')):
            p=academy_profile(preset(13,method))
            a=AcademyTrainer(p,'oval-1',objective='impara_infinito',balanced=True,batched=batched)
            b=AcademyTrainer(p,'oval-1',json.loads(json.dumps(a.checkpoint(0))),objective='impara_infinito',balanced=True,batched=batched)
            b.enable_collectors(2,persistent=True)
            try:
                goal=32*8
                while a.steps<goal:a.tick()
                deadline=time.monotonic()+20
                while b.steps<goal:
                    b.tick();time.sleep(.0001)
                    self.assertLess(time.monotonic(),deadline)
                def comparable(t):
                    c=t.checkpoint(0);c['curriculum'].pop('execution',None);return json.loads(json.dumps(c))
                self.assertEqual(comparable(a),comparable(b))
                # Finish a collection in flight at pause, then consume once on
                # a serial restore. This checks the compact packet JSON boundary.
                while b.inflight is None:b.tick()
                saved=json.loads(json.dumps(b.checkpoint(0),allow_nan=False))
                c=AcademyTrainer(p,'oval-1',saved,objective='impara_infinito',balanced=True,batched=batched)
                target=b.steps+32
                while b.steps<target:b.tick()
                while c.steps<target:c.tick()
                self.assertEqual(comparable(b),comparable(c))
            finally:b.close()


if __name__=='__main__':unittest.main()
