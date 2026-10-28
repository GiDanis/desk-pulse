"""Regression gates for pilot integrity, old networks and metric circuits."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from game_catalog import LEGACY_OBSERVATION_VERSION, OBSERVATION_VERSION, qualified
from game_control import pursuit_actions
from game_geometry import get_track
from game_learning import Evolution, Imitation, PPO, PPOSmooth, Policy, forward, log_probability
from game_profiles import METHODS, preset, reference_policy
from game_protocol import training_task, race_budget
from game_simulation import World, vertices, overlap
from game_store import GameStore


class RealCircuitChecks(unittest.TestCase):
    def test_existing_archive_startup_does_not_rewrite_sqlite_header(self):
        with tempfile.TemporaryDirectory() as root:
            GameStore(root)
            path=Path(root)/'game.sqlite'
            before=(path.read_bytes(),path.stat().st_mtime_ns)
            GameStore(root)
            self.assertEqual((path.read_bytes(),path.stat().st_mtime_ns),before)

    def test_first_track_access_preserves_each_method_and_fixed_parameters(self):
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root)
            for method in METHODS:
                pilot=store.create_driver(algorithm=method)
                original=store.driver(pilot)
                for track in ('mallory-oval-1','varano-short-1'):
                    new=store.driver(pilot,track)
                    self.assertEqual(new['profile']['algorithm'],method)
                    self.assertEqual(new['profile']['hidden'],original['profile']['hidden'])
                    self.assertEqual(new['profile']['observation'],OBSERVATION_VERSION)
                with self.assertRaises(ValueError):
                    store.set_profile(pilot,{**original['profile'],'traffic':True})
                self.assertEqual(store.driver(pilot),original)

    def test_legacy_network_and_training_provenance_survive(self):
        profile={**preset(),'observation':LEGACY_OBSERVATION_VERSION}
        learner=PPO(profile);frozen=learner.actor.copy()
        policy=learner.policy();world=World(8)
        np.testing.assert_array_equal(world.observations(version=LEGACY_OBSERVATION_VERSION),world.observations()[:,:32])
        np.testing.assert_array_equal(Policy(policy).act(world.observations()),np.tanh(forward(frozen,world.observations()[:,:32],16)))
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);_,payload=store.begin_session('impara',{'profile':profile})
            self.assertEqual(payload['configuration']['observation'],LEGACY_OBSERVATION_VERSION)
        resumed=PPO(profile,json.loads(json.dumps(learner.checkpoint())))
        np.testing.assert_array_equal(resumed.actor,frozen)
        for _ in range(4):
            obs=world.observations(version=LEGACY_OBSERVATION_VERSION)
            actions,raw,logp,value=resumed.sample(obs)
            nxt,reward,done=world.step(actions)
            resumed.remember(obs,raw,logp,value,reward,done,nxt,done)
        self.assertTrue(resumed.buffer)

    def test_smooth_exact_probability_and_ou_migration(self):
        profile=preset(6,'ppo_smooth');learner=PPOSmooth(profile)
        obs=World(32).observations()
        actions,raw,logp,_=learner.sample(obs)
        np.testing.assert_array_equal(actions,np.tanh(raw))
        np.testing.assert_allclose(logp,log_probability(raw,forward(learner.actor,obs,16),learner.log_std),atol=1e-12)
        snapshot=learner.checkpoint();resumed=PPOSmooth(profile,json.loads(json.dumps(snapshot)))
        np.testing.assert_array_equal(learner.sample(obs)[1],resumed.sample(obs)[1])
        old={**snapshot,'buffer':[{'oldOU':True}],'pending':{'oldOU':True}}
        old.pop('explorationVersion')
        migrated=PPOSmooth(profile,old)
        np.testing.assert_array_equal(migrated.actor,snapshot['actor'])
        self.assertEqual(migrated.buffer,[]);self.assertIsNone(migrated.pending)
        a=World(1);b=World(1)
        _,ra,_=a.step(np.array([[1.,.5]]),control_cost=0.)
        _,rb,_=b.step(np.array([[1.,.5]]),control_cost=.03)
        np.testing.assert_array_equal(a.state,b.state);self.assertLess(rb[0],ra[0])

    def test_imitation_aggregates_only_active_states_and_resumes(self):
        profile=preset(5,'imitation');learner=Imitation(profile);world=World(32)
        obs=world.observations();target=pursuit_actions(world);active=np.arange(32)%2==0
        for _ in range(8):learner.learn_step(obs,target,active)
        self.assertEqual(learner.sample_count,128);self.assertEqual(len(learner.samples),128)
        checkpoint=json.loads(json.dumps(learner.checkpoint()));resumed=Imitation(profile,checkpoint)
        learner.learn_step(obs,target,np.zeros(32,bool));self.assertEqual(learner.checkpoint(),checkpoint)
        for _ in range(8):
            learner.learn_step(obs,target,active);resumed.learn_step(obs,target,active)
        self.assertEqual(learner.checkpoint(),resumed.checkpoint())

    def test_adaptive_mutation_is_bounded_and_checkpoint_deterministic(self):
        profile=preset();learner=Evolution(profile)
        for _ in range(25):learner.update(np.zeros(32))
        self.assertEqual(learner.mutation_scale,2.);self.assertGreater(learner.diversity,0)
        resumed=Evolution(profile,json.loads(json.dumps(learner.checkpoint())))
        learner.update(np.arange(32));resumed.update(np.arange(32))
        self.assertEqual(learner.checkpoint(),resumed.checkpoint());self.assertEqual(learner.stagnation,0)

    def test_metric_geometry_grid_and_multilap_reference(self):
        for identity,length in (('mallory-oval-1',1609.344),('varano-short-1',1640.)):
            track=get_track(identity)
            self.assertAlmostEqual(track.length,length,places=6)
            world=World(4,shared=True,laps=3,track_id=identity);body=vertices(world.state)
            self.assertTrue(track.contains(body).all())
            for i in range(4):
                for j in range(i+1,4):self.assertFalse(overlap(body[i],body[j]))
            world=World(1,laps=3,track_id=identity);policy=Policy(reference_policy(identity))
            for _ in range(24000):
                world.step(pursuit_actions(world),return_observations=False)
                if not world.active[0]:break
            self.assertEqual(world.rows()[0]['status'],'arrivato',world.rows())
            self.assertGreater(world.progress[0],length*3)
            self.assertLess(world.time,race_budget(identity,3))
            self.assertGreater(training_task(identity,'pace')['limitSeconds'],world.time)
            with self.assertRaises(ValueError):policy.act(World(1).observations(),world=World(1))

    def test_new_track_qualification_requires_three_laps(self):
        from game_catalog import scope_hash
        proof={'scope':scope_hash('varano-short-1'),'candidateHash':'saved','candidate':{'valid':10,'laps':1}}
        driver={'policy':'saved','profile':preset(),'curriculum':{'champion':{'proof':proof}}}
        self.assertFalse(qualified(driver,'varano-short-1'))
        proof['candidate']['laps']=3;self.assertTrue(qualified(driver,'varano-short-1'))

    def test_reference_requires_a_real_qualifying_time_without_fake_neural_proof(self):
        from game_catalog import race_eligible
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);identity=store.create_driver(algorithm='pure_pursuit')
            store.select_track('varano-short-1');pilot=store.driver(identity)
            self.assertFalse(race_eligible(pilot,'varano-short-1'))
            self.assertFalse(qualified(pilot,'varano-short-1'));self.assertEqual(pilot['steps'],0)
            store.reset_driver(identity)
            self.assertFalse(race_eligible(store.driver(identity),'varano-short-1'))
            pilot['policy']='some-other-model';self.assertFalse(race_eligible(pilot,'varano-short-1'))

    def test_gui_projection_keeps_exact_boundaries_out_of_frame_maps(self):
        from game_catalog import visual_content
        config,drawing=visual_content('varano-short-1')
        self.assertNotIn('centerline',config['track']);self.assertNotIn('outer',drawing)
        self.assertTrue(drawing['outerPath'].startswith('M'))
        self.assertEqual(drawing['length'],get_track('varano-short-1').length)
        # Publishing the GUI content must not load the numerical runtime.
        import subprocess,sys
        result=subprocess.check_output([sys.executable,'-c',
            "import game_catalog,sys;game_catalog.visual_content('varano-short-1');assert 'numpy' not in sys.modules"],
            cwd=__import__('pathlib').Path(__file__).resolve().parent)
        self.assertEqual(result,b'')


if __name__=='__main__':unittest.main()
