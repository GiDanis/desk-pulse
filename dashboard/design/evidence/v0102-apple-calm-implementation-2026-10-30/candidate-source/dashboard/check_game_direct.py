"""Authority, causality and persistence gates for private direct driving."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from game_direct import features, controls, snapshot, DirectPolicy
from game_direct_trainer import DirectTrainer
from game_learning import Policy,random_weights,parameters
from game_residual import profile
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION


class DirectTests(unittest.TestCase):
    def world(self):
        w=World(1,7,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True)
        w.reset(varied=False);return w

    def base(self,method='residual_ppo'):
        from game_direct_bootstrap import direct_profile
        p=direct_profile(31,method)
        # Real teacher-imitation asset from private preparation, never a teacher
        # inside the inference graph. Tests can fall back to finite dummy weights
        # for structural checks without pretending they are a qualified driver.
        weights=random_weights(np.random.default_rng(31),p['hidden'],inputs=90)
        return p,snapshot(p,weights)

    def test_inference_never_calls_teacher_or_line_controller(self):
        p,data=self.base();w=self.world();before=w.racing_lane.copy()
        with (patch('game_control.pursuit_actions',side_effect=AssertionError('teacher')),
              patch('game_control.racing_actions',side_effect=AssertionError('teacher'))):
            # Both sensor extraction and the production Policy adapter are checked.
            for _ in range(20):
                a=Policy(data).act(None,world=w,index=0)
                w.step(a[None,:],return_observations=False)
        np.testing.assert_array_equal(before,w.racing_lane)

    def test_full_authority_and_no_45kmh_ceiling(self):
        w=self.world();p,data=self.base();weights=np.zeros(parameters(90,p['hidden']))
        weights[-2:]=[3.,4.];data=snapshot(p,weights)
        a=Policy(data).act(None,world=w,index=0)
        self.assertGreater(a[0],.99);self.assertGreater(a[1],.999)
        np.testing.assert_array_equal(controls(w,[[1.,-1.]]),[[1.,-1.]])
        np.testing.assert_array_equal(controls(w,[[0.,1.]]),[[0.,1.]])
        # A full pedal remains full above the old target speed.
        w.state[0,3]=20.
        np.testing.assert_array_equal(controls(w,[[0.,1.]]),[[0.,1.]])
        w.step([[0.,1.]],return_observations=False)
        self.assertGreater(w.state[0,3],20.)

    def test_features_are_causal_not_teacher_or_task_targets(self):
        w=self.world();x=features(w);self.assertEqual(x.shape,(90,))
        w.racing_lane[:]=3.;w.training_context[:]=.9
        np.testing.assert_array_equal(x,features(w))
        w.state[0,6]+=.1;self.assertNotEqual(x[8],features(w)[8])
        w.state[0,3]+=1.;self.assertNotEqual(x[72],features(w)[72])
        self.assertTrue(np.isfinite(features(w)).all())

    def test_policy_world_resume_inside_a_held_action(self):
        p,data=self.base();a=self.world();policy=Policy(data)
        for _ in range(17):a.step(policy.act(None,world=a),return_observations=False)
        b=self.world();b.restore(json.loads(json.dumps(a.snapshot())))
        for _ in range(20):
            ua=policy.act(None,world=a);ub=Policy(data).act(None,world=b)
            np.testing.assert_array_equal(ua,ub)
            a.step(ua,return_observations=False);b.step(ub,return_observations=False)
        np.testing.assert_array_equal(a.state,b.state)
        a.reset();self.assertEqual(a.direct_cache,{})
        np.testing.assert_array_equal(a.direct_previous,np.zeros((1,2)))

    def test_direct_opponent_does_not_change_ego_rule_contract(self):
        w=World(2,7,shared=True,track_id='oval-1',physics=RACE_PHYSICS_VERSION)
        controls(w,[[0.,1.]],[1])
        self.assertFalse(w.direct_control)
        controls(w,[[0.,1.]],[0])
        self.assertTrue(w.direct_control)

    def test_requires_explicit_new_base_and_rejects_residual_checkpoint(self):
        p,data=self.base()
        from game_direct_bootstrap import initial_policy
        t=DirectTrainer(p,'oval-1')
        np.testing.assert_array_equal(t.learner.actor,initial_policy(p)['weights'])
        with self.assertRaises(ValueError):DirectTrainer(p,'oval-1',dict(protocol='race-residual-1',initialPolicy=data))
        from game_residual import snapshot as old_snapshot,initial_weights
        legacy={k:v for k,v in p.items() if k!='controlMode'}
        with self.assertRaises(ValueError):DirectPolicy(old_snapshot(legacy,initial_weights(legacy)))

    def test_prepared_base_rejects_tampering_and_reset_keeps_no_old_actor(self):
        import tempfile
        import game_direct_bootstrap as bootstrap
        from game_store import GameStore
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);driver=store.drivers()[1]
            self.assertEqual(driver['profile']['controlMode'],'direct')
            policy=store.load(driver['policy']);self.assertEqual(policy['kind'],'direct')
            self.assertEqual(policy['origin']['policyHash'],bootstrap.base_asset()['policyHash'])
            tactical=store.drivers()[4];tactical_policy=store.load(tactical['policy'])
            self.assertEqual(tactical_policy['origin']['role'],'traffic')
            np.testing.assert_array_equal(tactical_policy['weights'],bootstrap.base_asset('traffic')['policy']['weights'])
            self.assertNotEqual(tactical_policy['weights'],policy['weights'])
            trainer=DirectTrainer(driver['profile'],'oval-1')
            trainer.learner.actor[-1]+=1.
            store.save_training(driver['id'],trainer.checkpoint(0),trainer.learner.policy(),0,0,{},trainer.state)
            store.reset_residual(driver['id']);fresh=store.driver(driver['id'])
            self.assertIsNone(fresh['checkpoint']);self.assertEqual(fresh['steps'],0)
            np.testing.assert_array_equal(store.load(fresh['policy'])['weights'],policy['weights'])
            corrupt=json.loads(bootstrap.ASSET.read_text());corrupt['policy']['weights'][0]+=1.
            path=Path(root)/'corrupt.json';path.write_text(json.dumps(corrupt))
            bootstrap.base_asset.cache_clear()
            with patch('game_direct_bootstrap.ASSET',path):
                with self.assertRaises(ValueError):bootstrap.base_asset()
            bootstrap.base_asset.cache_clear()

    def test_worker_positional_opponents_dispatches_to_direct_trainer(self):
        from game_residual_trainer import ResidualTrainer
        p,data=self.base();opponents=[Policy(data)]
        t=ResidualTrainer(p,'oval-1',dict(initialPolicy=data),opponents)
        self.assertIsInstance(t,DirectTrainer);self.assertEqual(len(t.opponents),1)
        for _ in range(8):t.tick()
        self.assertEqual(t.steps,8)

    def test_offpolicy_prepares_critic_before_changing_actor(self):
        from game_direct_trainer import DirectOffPolicy
        p,data=self.base('residual_td3');learner=DirectOffPolicy(p)
        learner.actor=np.asarray(data['weights']);learner.target_actor=learner.actor.copy();learner.anchor_actor=learner.actor.copy()
        before=learner.actor.copy();q=learner.q1.copy();rng=np.random.default_rng(9)
        for _ in range(200):
            obs=rng.normal(size=94);obs[73]=.95
            action=learner.sample(obs)[0];learner.remember(obs,action,.01,obs*.99,False);learner.update()
        np.testing.assert_array_equal(before,learner.actor)
        self.assertGreater(np.linalg.norm(q-learner.q1),0.)
        self.assertFalse(learner.actor_update_ready())
        learner.transitions=learner.spec['anchorSteps']
        gradient=rng.normal(size=len(before));obs=rng.normal(size=(5,90))
        np.testing.assert_array_equal(gradient,learner.actor_gradient(gradient,obs))

    def test_all_methods_update_and_resume_with_direct_actions(self):
        for method in ('residual_ppo','residual_sac','residual_td3','residual_tactic'):
            p,data=self.base(method);t=DirectTrainer(p,'oval-1',dict(initialPolicy=data))
            initial=t.learner.actor.copy()
            for _ in range(3800):t.tick()
            a=DirectTrainer(p,'oval-1',json.loads(json.dumps(t.checkpoint(0))))
            for _ in range(300):t.tick();a.tick()
            self.assertGreater(t.learner.update_index,0)
            self.assertGreater(np.linalg.norm(t.learner.actor-initial),0)
            np.testing.assert_array_equal(t.learner.actor,a.learner.actor)
            np.testing.assert_array_equal(t.episode.world.state,a.episode.world.state)
            self.assertEqual(t.learner.policy()['kind'],'direct')
            self.assertFalse(t.state['execution']['teacherAtInference'])
            # Expose actual actuator uncertainty, not fake target-line centimetres.
            _,_,frame=t.frame('Test',1,0)
            self.assertNotIn('explorationMeters',frame['residual'])
            self.assertEqual(frame['residual']['control'],'network-actuators')


if __name__=='__main__':unittest.main()
