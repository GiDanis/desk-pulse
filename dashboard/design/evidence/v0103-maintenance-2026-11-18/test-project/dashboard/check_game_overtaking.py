"""Targeted reward migration, batched physical parity and durable writer checks."""
import unittest,json,tempfile,time
from copy import deepcopy
from pathlib import Path
import numpy as np
from game_residual import profile,snapshot,initial_weights
from game_learning import Policy
from game_simulation import World,RAY_ANGLES
from game_catalog import RACE_PHYSICS_VERSION
from game_residual_trainer import ResidualTrainer,ResidualCheck
from game_residual_learning import encode_checkpoint,OffPolicy
from game_rewards import specification
from game_academy import Episode

class BrokenStore:
    def save_training(self,*a,**kw):raise OSError('disk failure')


class OvertakingChecks(unittest.TestCase):
    def test_batched_controls_preserve_nonzero_policies_physics_and_resume(self):
        from game_control import frozen_actions
        for continuous in (False,True):
            a=World(5,47,shared=True,laps=5,physics=RACE_PHYSICS_VERSION,telemetry=True)
            a.reset(varied=False);a.continuous=continuous;a.native_sensors=True
            b=World(5,47,shared=True,laps=5,physics=RACE_PHYSICS_VERSION,telemetry=True);b.restore(a.snapshot());b.native_sensors=True
            pa=[];pb=[]
            for i,m in enumerate(('race_master','residual_ppo','residual_sac','residual_td3','residual_tactic')):
                p=profile(i+1,m);weights=None if m=='race_master' else initial_weights(p)
                if weights is not None:weights[-66:]=np.random.default_rng(i).normal(0,.025,66)
                policy=snapshot(p,weights);pa.append(Policy(policy));pb.append(Policy(policy))
            for tick in range(900):
                ua=np.array([p.act(None,world=a,index=i) for i,p in enumerate(pa)])
                ub=frozen_actions(b,pb)
                np.testing.assert_allclose(ua,ub,atol=2e-13,rtol=0)
                a.step(ua,return_observations=False);b.step(ub,return_observations=False)
            np.testing.assert_allclose(a.state,b.state,atol=1e-10,rtol=0)
            self.assertEqual(a.events,b.events)
            np.testing.assert_equal(a.track_limits,b.track_limits)
            np.testing.assert_equal(a.lap_count,b.lap_count)
            np.testing.assert_equal(a.racing_lane,b.racing_lane)

    def test_skipping_discarded_observations_keeps_rewards_and_physics(self):
        from game_geometry import get_track
        for track in ('oval-1','varano-short-1'):
            for phase in ('pace','corner'):
                spec=specification(profile(21,'residual_tactic'))
                a=Episode(track,phase,95201,protocol='driving-memory-1',reward_spec=spec)
                b=Episode(track,phase,95201,protocol='driving-memory-1',reward_spec=spec)
                p=profile(3,'residual_tactic');weights=initial_weights(p);weights[-66:]=.01
                pa,pb=Policy(snapshot(p,weights)),Policy(snapshot(p,weights))
                for _ in range(400):
                    ra=a.step(pa.act(None,world=a.world,index=0));rb=b.step(pb.act(None,world=b.world,index=0),return_observation=False)
                    self.assertIsNone(rb[0]);self.assertEqual(ra[1:],rb[1:])
                    np.testing.assert_array_equal(a.world.state,b.world.state)

    def test_versioned_default_preserves_checkpoint_and_replay(self):
        from game_residual import recipe
        for method in ('residual_ppo','residual_sac','residual_td3','residual_tactic'):
            p=profile(21,method);a=ResidualTrainer(p,'oval-1')
            self.assertEqual(recipe(p)['version'],'race-residual-4')
            self.assertEqual(a.reward_spec['version'],'residual-racing-3')
            self.assertNotIn('cutoff',recipe(p))
            for _ in range(80):a.tick()
            c=a.checkpoint(12.);b=ResidualTrainer(p,'oval-1',c)
            self.assertNotIn('migration',b.state)
            self.assertNotIn('recipeArchives',b.state)
            self.assertEqual(a.learner.checkpoint(),b.learner.checkpoint())
            for _ in range(40):a.tick();b.tick()
            self.assertEqual(a.learner.checkpoint(),b.learner.checkpoint())
            np.testing.assert_array_equal(a.episode.world.state,b.episode.world.state)

    def test_known_recipe_migration_preserves_actor_counters_rng_and_archive(self):
        for method in ('residual_ppo','residual_sac','residual_td3','residual_tactic'):
            p={**profile(21,method),'rewardExperiment':'common-units-1'};a=ResidualTrainer(p,'oval-1')
            for _ in range(90):a.tick()
            c=a.checkpoint(12.);c['sourceCheckpoint']='a'*64
            r=c['curriculum']['effectiveParameters'];r.update(version='race-residual-2',reward='residual-racing-1');r.pop('cutoff');r.pop('raceRulesVersion')
            old=deepcopy(c);b=ResidualTrainer(p,'oval-1',c)
            self.assertEqual(c,old)
            np.testing.assert_array_equal(a.learner.actor,b.learner.actor)
            np.testing.assert_array_equal(a.learner.log_std,b.learner.log_std)
            self.assertEqual(a.learner.rng.bit_generator.state,b.learner.rng.bit_generator.state)
            self.assertEqual(b.steps,a.steps);self.assertEqual(b.decisions,a.decisions)
            self.assertEqual(b.source_checkpoint,'a'*64)
            self.assertEqual(b.state['champion'],a.state['champion'])
            self.assertEqual(b.learner.update_index,0)
            if hasattr(b.learner,'count'):self.assertEqual(b.learner.count,0)
            else:self.assertEqual(len(b.learner.buffer),0)
            restored=ResidualTrainer(p,'oval-1',json.loads(json.dumps(b.checkpoint(12.))))
            self.assertEqual(restored.state['recipeArchives'],b.state['recipeArchives'])

    def test_reward_units_and_collection_cutoff_match(self):
        spec=specification({**profile(21,'residual_tactic'),'rewardExperiment':'common-units-1'})
        finite=Episode('oval-1','corner',95201,protocol='driving-memory-1',reward_spec=spec)
        continuous=Episode('oval-1','corner',95201,protocol='driving-memory-1',objective='impara_sorpasso',bots=1,reward_spec=spec)
        self.assertEqual(finite.spec['distance'],240)
        self.assertTrue(finite.world.continuous)
        # identical physical start: objective changes neither reward units nor rules
        continuous.world.restore(finite.world.snapshot())
        a,b=Policy(snapshot(profile(1,'race_master'))),Policy(snapshot(profile(1,'race_master')))
        for _ in range(600):
            finite.step(a.act(None,world=finite.world,index=0));continuous.step(b.act(None,world=continuous.world,index=0))
            self.assertAlmostEqual(finite.reward,continuous.reward,places=12)
        while not finite.reason:finite.step(a.act(None,world=finite.world,index=0))
        self.assertTrue(finite.truncated);self.assertFalse(finite.terminated)
        self.assertEqual(finite.reason,'success');self.assertGreaterEqual(finite.passes,1)

    def test_nonretiring_contact_is_reported_before_incomplete_pass(self):
        e=Episode('oval-1','overtake',99159,protocol='driving-memory-1',
            reward_spec=specification(profile(21,'residual_tactic')))
        e.reason='skill_failed';e.contact_count=1
        self.assertFalse(e.world.retired[0]);self.assertFalse(e.skill_valid())
        self.assertEqual(e.result()['terminationCause'],'vehicle_contact')
        self.assertEqual(e.manoeuvre_status(),'Contatto nella prova')

    def test_visual_rays_equal_observation_projection(self):
        w=World(5,8,shared=True,physics=RACE_PHYSICS_VERSION);w.native_sensors=True
        for i in range(5):np.testing.assert_array_equal(w.observations(version='race-68-v3')[i,:5],np.clip(w.sensor_rays(w.state[i:i+1],RAY_ANGLES,150)[0]/150,0,1))

    def test_detached_replay_and_bounded_durable_writer(self):
        from game_checkpoint_writer import CheckpointWriter
        from game_store import GameStore
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);driver=store.drivers()[2];t=ResidualTrainer(driver['profile'],'oval-1')
            for _ in range(80):t.tick()
            c=t.checkpoint(3.,deferred=True);rows=c['learner']['_replaySnapshot'].copy()
            t.learner.replay[:t.learner.count]=9
            np.testing.assert_array_equal(c['learner']['_replaySnapshot'],rows)
            writer=CheckpointWriter(store)
            try:
                self.assertTrue(writer.submit(driver['id'],c,t.learner.policy(),t.steps,3.,t.metric,t.state,None,{}))
                self.assertFalse(writer.submit(None,None,None,None,None,None,None,None,None))
                saved=writer.collect(wait=True);self.assertEqual(saved['steps'],t.steps)
                d=store.driver(driver['id']);loaded=store.load(d['checkpoint'])
                replay=OffPolicy(driver['profile'],loaded['learner'])
                np.testing.assert_array_equal(replay.replay[:replay.count],rows)
            finally:writer.close()

    def test_dossier_does_not_read_a_residual_replay_on_gui_refresh(self):
        from game_store import GameStore
        from game_dossier import dossier
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);d=store.drivers()[2];t=ResidualTrainer(d['profile'],'oval-1')
            store.save_training(d['id'],t.checkpoint(0),t.learner.policy(),0,0,t.metric,t.state)
            checkpoint=store.driver(d['id'])['checkpoint'];load=store.load
            def guarded(digest):
                self.assertNotEqual(digest,checkpoint,'GUI must use compact metadata, not the replay')
                return load(digest)
            store.load=guarded
            self.assertTrue(dossier(store,d['id'])['summary'])

    def test_writer_failure_never_returns_saved(self):
        from game_checkpoint_writer import CheckpointWriter
        writer=CheckpointWriter(BrokenStore())
        try:
            writer.submit('x',{},None,0,0,{},None,None,{})
            with self.assertRaises(OSError):writer.collect(wait=True)
            self.assertFalse(writer.busy)
        finally:writer.close()

    def test_verification_cache_reuses_only_completed_matching_bank(self):
        p=snapshot(profile(21,'residual_ppo'),initial_weights(profile(21,'residual_ppo')))
        cache={};check=ResidualCheck(p,p,'oval-1',cache=cache)
        ticks=0
        while not check.tick():ticks+=1
        original=check.result();self.assertEqual(original['reusedChampionCases'],0)
        again=ResidualCheck(p,p,'oval-1',cache=cache);self.assertEqual(again.reused,3)
        ticks_again=0
        while not again.tick():ticks_again+=1
        actual=again.result();self.assertLess(ticks_again,ticks*.6)
        self.assertEqual(actual['candidate'],original['candidate']);self.assertEqual(actual['champion'],original['champion'])
        changed=deepcopy(p);changed['weights'][-1]=.1
        self.assertEqual(ResidualCheck(p,changed,'oval-1',cache=cache).reused,0)

if __name__=='__main__':unittest.main()
