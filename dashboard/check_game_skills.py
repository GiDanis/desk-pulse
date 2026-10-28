"""Exact prepared actions and persistent updates on causal recurrent skills."""
from pathlib import Path
import tempfile,unittest
import numpy as np
import torch
from game_lab.models import Actor
from game_lab.skills import SkillEnv,initialize,export
from game_lab.checkpoint import save,load
from game_temporal import TemporalPolicy


class SkillChecks(unittest.TestCase):
    def test_encoding_skips_unused_controls_with_exact_features_and_memory(self):
        from game_lab.actuators import configure
        from game_direct import features
        from unittest.mock import patch
        torch.manual_seed(186)
        for arch,mode in [('gru-skip',None),('gru-adapter',None),('gru-intent',None),('gru-intent-deep',None),('gru-maneuver',None),('gru-maneuver','plastic'),('gru-maneuver','plastic-context')]:
          with self.subTest(architecture=arch,mode=mode):
            base=Actor(arch,128,maneuver_hidden=32,maneuver_scale=.7).export()
            if mode:base=configure(base,mode)
            env=SkillEnv(base,family='solo',duration=3.);observation,_=env.reset(seed=39)
            reference=TemporalPolicy(base);state=None
            for _ in range(12):
                # RacingEnv.observe publishes float32 to both encoder paths.
                # Compare identical inputs, including the boundary cast.
                raw=features(env.episode.world).astype(np.float32);_,state=reference.forward(raw,state)
                expected=reference.readout_features(raw,state)
                if mode=='plastic':expected=expected[-92:]
                np.testing.assert_array_equal(observation,expected.astype(np.float32))
                self.assertEqual(env.skill_state,state)
                with patch.object(env.encoder,'readout_features',wraps=env.encoder.readout_features) as readout:
                    observation,*_=env.step(np.array([0.,.1],dtype=np.float32))
                    self.assertEqual(readout.call_count,0 if mode=='plastic' else 1)

    def test_periodic_candidate_capture_keeps_the_training_trajectory(self):
        from game_lab.actuators import configure
        torch.set_num_threads(1);torch.manual_seed(85)
        base=configure(Actor('gru-maneuver',128,maneuver_hidden=32,maneuver_scale=.7).export(),'plastic-context')
        for method in ('ppo','sac','td3'):
          with self.subTest(method=method):
            whole,_=initialize(base,method,seed=29,family='solo',duration=2.,pedal_retention=1.);whole._skill['warmup']=0
            whole.learn(256);expected={k:v.detach().clone() for k,v in whole.policy.state_dict().items()}
            split,_=initialize(base,method,seed=29,family='solo',duration=2.,pedal_retention=1.);split._skill['warmup']=0
            split.learn(128);export(split);split.learn(128,reset_num_timesteps=False)
            for k,v in split.policy.state_dict().items():np.testing.assert_array_equal(v.detach().numpy(),expected[k].numpy(),err_msg=method+' '+k)

    def test_frozen_critic_context_matches_controls_and_exact_resume(self):
        from game_lab.actuators import configure
        from game_direct import features
        torch.set_num_threads(1);torch.manual_seed(84)
        base=configure(Actor('gru-maneuver',128,maneuver_hidden=32,maneuver_scale=.7).export(),'plastic-context')
        for method in ('ppo','sac','td3'):
          with self.subTest(method=method),tempfile.TemporaryDirectory() as root:
            model,env=initialize(base,method,seed=14,family='solo',duration=2.,pedal_retention=1.)
            self.assertEqual(env.observation_space.shape,(348,))
            obs,_=env.reset(seed=192);expected,_=TemporalPolicy(base).forward(features(env.episode.world))
            np.testing.assert_allclose(model.predict(obs,deterministic=True)[0],expected,atol=2e-6)
            frozen=obs.copy();model._skill['warmup']=0;model.learn(128)
            # Environment encodings still use the original frozen controls;
            # training current controls cannot change old replay semantics.
            original=SkillEnv(base,family='solo',duration=2.);again,_=original.reset(seed=192)
            np.testing.assert_array_equal(again,frozen)
            save(model,Path(root)/'saved',method=method,contract={'context':1})
            model.learn(128,reset_num_timesteps=False)
            expected={k:v.detach().clone() for k,v in model.policy.state_dict().items()}
            resumed,_=load(Path(root)/'saved',SkillEnv(base,family='solo',duration=2.),contract={'context':1})
            resumed.learn(128,reset_num_timesteps=False)
            for k,v in resumed.policy.state_dict().items():np.testing.assert_array_equal(v.detach().numpy(),expected[k].numpy(),err_msg=method+' '+k)
            candidate=export(resumed);self.assertEqual(candidate['criticFeatureContext'],base['criticFeatureContext'])
            inherited,_=initialize(candidate,method,family='solo',duration=2.)
            self.assertEqual(inherited.observation_space.shape,(348,))

    def test_plastic_actuators_match_and_resume_without_changing_causal_memory(self):
        from game_lab.actuators import configure
        from game_lab.skills import readout
        from game_policy_digest import ReadoutDigest,mutable_weights
        from game_lab.runtime_worker import preview_readout,restore_preview_policy
        from game_residual import key
        torch.set_num_threads(1);torch.manual_seed(183)
        base=configure(Actor('gru-maneuver',128,maneuver_hidden=32,maneuver_scale=.7).export(),'plastic')
        for method in ('ppo','sac','td3'):
          with self.subTest(method=method),tempfile.TemporaryDirectory() as root:
            model,env=initialize(base,method,seed=41,family='solo',duration=2.,pedal_retention=1.)
            self.assertEqual(env.observation_space.shape,(92,))
            obs,_=env.reset(seed=92);portable=TemporalPolicy(export(model));state=None
            from game_direct import features
            for _ in range(5):
                expected,state=portable.forward(features(env.episode.world),state)
                actual=model.predict(obs,deterministic=True)[0]
                np.testing.assert_allclose(actual,expected,atol=2e-6)
                obs,*_=env.step(actual)
            initial=export(model);digester=ReadoutDigest(initial);encoder=TemporalPolicy(initial).encoder_key
            model._skill['warmup']=0;model.learn(128)
            save(model,Path(root)/'saved',method=method,contract={'plastic':1})
            self.assertTrue((Path(root)/'saved/skill.pkl').is_file())
            self.assertNotIn('skillPolicy',env.snapshot())
            from zipfile import ZipFile
            with ZipFile(Path(root)/'saved/model.zip') as archive:
                self.assertNotIn('_skill',__import__('json').loads(archive.read('data')))
                self.assertLess(archive.getinfo('data').file_size,1000000)
            model.learn(128,reset_num_timesteps=False)
            expected={k:v.detach().clone() for k,v in model.policy.state_dict().items()}
            second_env=SkillEnv(base,family='solo',duration=2.)
            second,_=load(Path(root)/'saved',second_env,contract={'plastic':1})
            second.learn(128,reset_num_timesteps=False)
            for k,v in second.policy.state_dict().items():np.testing.assert_array_equal(v.detach().numpy(),expected[k].numpy(),err_msg=method+' '+k)
            candidate=export(second)
            for name in ('steer_controller.0.weight','pedal_controller.2.weight'):
                self.assertNotEqual(candidate['weights'][name],base['weights'][name])
            for name,value in base['weights'].items():
                if name not in mutable_weights(base):self.assertEqual(candidate['weights'][name],value)
            updated=TemporalPolicy(candidate);self.assertEqual(updated.encoder_key,encoder)
            self.assertEqual(digester.digest({p:candidate[p[0]][p[1]] for p in digester.paths}),key(candidate))
            self.assertEqual(restore_preview_policy(candidate,preview_readout(updated)),candidate)
            inherited,_=initialize(candidate,method,seed=41,family='solo',duration=2.)
            self.assertEqual(inherited.get_env().observation_space.shape,(92,))
            self.assertEqual(inherited._skill['pedalRetention'],1.)
            self.assertTrue(candidate['origin']['controlEncodersTrainable'])
            # Updating feedforward controls must not reset per-car recurrence
            # or force a second decision during an existing 100 ms interval.
            world=env.episode.world;world.temporal_cache={};portable.act(world,0)
            before=__import__('copy').deepcopy(world.temporal_cache[0]);updated.act(world,0)
            self.assertEqual(world.temporal_cache[0],before)

    def test_cached_policy_hash_and_adapter_transfer_match_complete_export(self):
        from game_policy_digest import ReadoutDigest
        from game_residual import key
        from game_lab.skills import readout
        torch.set_num_threads(1);torch.manual_seed(81)
        for architecture,opts in [(a,{}) for a in ('gru-adapter','gru-intent','gru-intent-deep','gru-maneuver')]+[('gru-maneuver',dict(maneuver_hidden=32,maneuver_scale=.7))]:
          actor=Actor(architecture,128,**opts)
          if architecture=='gru-adapter':
            with torch.no_grad():actor.adapter_head.weight.normal_(std=.03)
          base=actor.export()
          for method in ('ppo','sac','td3'):
            model,env=initialize(base,method,seed=53,family='solo',duration=2.)
            data=export(model);digester=ReadoutDigest(data);obs,_=env.reset(seed=14)
            expected,_=TemporalPolicy(data).forward(__import__('game_direct').features(env.episode.world))
            np.testing.assert_allclose(model.predict(obs,deterministic=True)[0],expected,atol=2e-6)
            for count in (1,128,729):
                with torch.no_grad():readout(model,method).weight.add_(.0001)
                model.num_timesteps=count;updated=export(model)
                values={path:updated[path[0]][path[1]] for path in digester.paths}
                self.assertEqual(digester.digest(values),key(updated))

    def test_reference_actions_match_prepared_network_and_export(self):
        torch.set_num_threads(1);torch.manual_seed(12)
        base=Actor('gru-skip').export()
        for method in ('ppo','sac','td3'):
            with self.subTest(method=method):
                model,env=initialize(base,method,seed=42,family='solo',duration=2.)
                obs,_=env.reset(seed=942);portable=TemporalPolicy(export(model));state=None
                for _ in range(10):
                    from game_direct import features
                    expected,state=portable.forward(features(env.episode.world),state)
                    actual=model.predict(obs,deterministic=True)[0]
                    np.testing.assert_allclose(actual,expected,atol=2e-6)
                    obs,*_=env.step(actual)

    def test_all_learners_resume_real_updates_with_frozen_encoder(self):
        torch.set_num_threads(1);torch.manual_seed(13)
        cases=[(a,m,2,'gaussian') for a in ('gru-skip','gru-maneuver') for m in ('ppo','sac','td3')]+[('gru-maneuver','td3',32,'gaussian'),('gru-maneuver','ppo',32,'sde')]
        for architecture,method,memory,exploration in cases:
            base=Actor(architecture,128,maneuver_hidden=memory,maneuver_scale=.7 if memory==32 else 1.).export()
            with self.subTest(architecture=architecture,method=method,memory=memory),tempfile.TemporaryDirectory() as root:
                model,env=initialize(base,method,seed=44,family='solo',duration=2.,
                    steering_retention=1000. if memory==32 else 25.,actor_rate=.00003 if memory==32 else .000003,exploration=exploration)
                model._skill['warmup']=0;model.learn(128)
                original_encoder=base['weights']['core.weight_hh_l0']
                save(model,Path(root)/'snapshot',method=method,contract={'skill':'fixed'})
                model.learn(128,reset_num_timesteps=False)
                expected={k:v.detach().clone() for k,v in model.policy.state_dict().items()}
                physical=env.episode.world.state.copy();hidden=env.skill_state
                second_env=SkillEnv(base,family='solo',duration=2.)
                second,_=load(Path(root)/'snapshot',second_env,contract={'skill':'fixed'})
                second.learn(128,reset_num_timesteps=False)
                for k,v in second.policy.state_dict().items():
                    np.testing.assert_array_equal(v.detach().numpy(),expected[k].numpy(),err_msg=method+' '+k)
                np.testing.assert_array_equal(second_env.episode.world.state,physical)
                self.assertEqual(second_env.skill_state,hidden)
                candidate=export(second)
                if memory==32:
                    inherited,_=initialize(candidate,method,seed=44,family='solo',duration=2.)
                    self.assertEqual(inherited._skill['steeringRetention'],1000.)
                    self.assertEqual(inherited._skill['actorLearningRate'],.00003)
                    self.assertEqual(inherited._skill['explorationStyle'],exploration)
                self.assertEqual(candidate['weights']['core.weight_hh_l0'],original_encoder)
                self.assertNotEqual(candidate['weights']['head.weight'],base['weights']['head.weight'])


if __name__=='__main__':unittest.main()
