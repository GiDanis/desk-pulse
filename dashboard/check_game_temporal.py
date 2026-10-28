"""PyTorch/NumPy parity and recurrent lifecycle, without training a model."""
import json,unittest
import numpy as np
import torch
from game_lab.models import Actor
from game_temporal import TemporalPolicy
from game_lab.environment import make_episode


class TemporalChecks(unittest.TestCase):
    def test_private_maneuver_memory_has_portable_actions_and_free_actuators(self):
        torch.set_num_threads(1);torch.manual_seed(872)
        actor=Actor('gru-maneuver',128,maneuver_hidden=32,maneuver_scale=.7).eval()
        raw=np.random.default_rng(92).uniform(-1,1,(1,160,90)).astype(np.float32)
        with torch.no_grad():expected,_=actor(torch.as_tensor(raw))
        portable=TemporalPolicy(actor.export());state=None
        for tick,x in enumerate(raw[0]):
            actual,state=portable.forward(x,state);np.testing.assert_allclose(actual,expected[0,tick],rtol=2e-5,atol=2e-6)
        self.assertEqual(len(state['intent']),32)
        with torch.no_grad():actor.steer_head.bias.fill_(10.)
        action,_=TemporalPolicy(actor.export()).forward(raw[0,0])
        self.assertGreater(action[0],.99)  # latent scale is not an actuator cap

    def test_road_migration_preserves_actions_and_measures_current_rivals(self):
        from game_lab.sensors import road_policy
        from game_direct import features,ROAD_FEATURES
        torch.manual_seed(781);actor=Actor('gru-skip').eval()
        with torch.no_grad():
            actor.mean.normal_(std=.1);actor.scale.uniform_(.1,1.)
            actor.skip.weight.normal_(std=.03)
        old=TemporalPolicy(actor.export());new=TemporalPolicy(road_policy(actor.export()))
        e=make_episode(31,family='traffic',bots=3);h=k=None
        for _ in range(70):
            x=features(e.world);z=features(e.world,version=ROAD_FEATURES)
            a,h=old.forward(x,h);b,k=new.forward(z,k)
            np.testing.assert_allclose(a,b,atol=2e-6)
            e.step([0.,.2],return_observation=False)
        self.assertEqual(new.data['features'],ROAD_FEATURES)

    def test_torch_numpy_parity_for_all_architectures(self):
        torch.set_num_threads(1)
        for architecture in ('dense','history','gru','set-gru','gru-skip','gru-adapter','gru-intent','gru-intent-deep','gru-maneuver'):
            with self.subTest(architecture=architecture):
                torch.manual_seed(712);actor=Actor(architecture).eval()
                if architecture in ('gru-skip','gru-adapter'):
                    with torch.no_grad():actor.skip.weight.normal_(std=.03)
                if architecture=='gru-adapter':
                    with torch.no_grad():actor.adapter_head.weight.normal_(std=.03)
                policy=TemporalPolicy(actor.export())
                x=np.random.default_rng(81).uniform(-1,1,(2,48,90)).astype(np.float32)
                with torch.no_grad():expected,_=actor(torch.as_tensor(x))
                for sample in range(2):
                    state=None
                    for tick in range(48):
                        value,state=policy.forward(x[sample,tick],state)
                        np.testing.assert_allclose(value,expected[sample,tick],rtol=2e-5,atol=2e-6)

    def test_history_stepwise_collection_matches_full_sequence(self):
        torch.manual_seed(85);actor=Actor('history').eval()
        x=torch.randn(2,30,90)
        with torch.no_grad():
            full,_=actor(x);state=None;steps=[]
            for j in range(x.shape[1]):
                value,state=actor(x[:,j:j+1],state);steps.append(value)
        torch.testing.assert_close(torch.cat(steps,1),full)

    def test_set_actor_keeps_actions_when_rival_slots_are_permuted(self):
        actor=Actor('set-gru').eval();rng=np.random.default_rng(41)
        x=rng.uniform(-1,1,(1,20,90)).astype(np.float32);x[:,:,17]=1;x[:,:,24]=1;x[:,:,31]=0
        y=x.copy()
        for target,source in enumerate([2,0,1]):
            y[:,:,11+7*target:18+7*target]=x[:,:,11+7*source:18+7*source]
            y[:,:,55+3*target:58+3*target]=x[:,:,55+3*source:58+3*source]
        with torch.no_grad():a,_=actor(torch.as_tensor(x));b,_=actor(torch.as_tensor(y))
        np.testing.assert_allclose(a.numpy(),b.numpy(),atol=2e-6)
        policy=TemporalPolicy(actor.export());h=k=None
        for a,b in zip(x[0],y[0]):
            u,h=policy.forward(a,h);v,k=policy.forward(b,k);np.testing.assert_allclose(u,v,atol=2e-6)

    def test_updating_readout_keeps_memory_and_decision_cadence(self):
        from copy import deepcopy
        torch.manual_seed(97);data=Actor('gru-skip').export();first=TemporalPolicy(data)
        changed=deepcopy(data);changed['weights']['head.bias'][1]+=.03;second=TemporalPolicy(changed)
        e=make_episode(431,bots=1);first.act(e.world,0)
        original=deepcopy(e.world.temporal_cache[0]);e.world.time=1/60
        second.act(e.world,0)
        self.assertEqual(e.world.temporal_cache[0],original)
        e.world.time=6/60
        from game_direct import features
        _,expected=second.forward(features(e.world),original['state'])
        second.act(e.world,0)
        np.testing.assert_array_equal(e.world.temporal_cache[0]['state'],expected)
        self.assertEqual(e.world.temporal_cache[0]['encoderKey'],first.encoder_key)

    def test_hidden_state_is_per_car_persisted_and_not_reset_at_window(self):
        torch.manual_seed(94);policy=TemporalPolicy(Actor().export())
        a=make_episode(431,bots=2);b=make_episode(431,bots=2)
        for _ in range(20):
            a.step(policy.act(a.world,0),return_observation=False)
        saved=json.loads(json.dumps(a.snapshot()));b.restore(saved)
        self.assertTrue(a.world.temporal_cache)
        for _ in range(20):
            u=policy.act(a.world,0);v=policy.act(b.world,0)
            np.testing.assert_array_equal(u,v)
            a.step(u,return_observation=False);b.step(v,return_observation=False)
        old=json.dumps(a.world.temporal_cache)
        a.next_window();self.assertEqual(json.dumps(a.world.temporal_cache),old)
        policy.act(a.world,1);self.assertIn(1,a.world.temporal_cache)
        a.world.reset(return_observations=False);self.assertEqual(a.world.temporal_cache,{})


if __name__=='__main__':unittest.main()
