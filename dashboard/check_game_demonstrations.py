"""Protected replay, timeout masks, source binding and exact learner resume."""
from pathlib import Path
import tempfile,unittest
import numpy as np
import torch
from gymnasium import spaces
from game_lab.demonstrations import DemonstrationReplay,FIELDS,VERSION,load as load_bank
from game_lab.artifacts import atomic_report,digest
from game_lab.provenance import source_hashes
from game_lab.models import Actor
from game_lab.actuators import configure
from game_lab.skills import initialize,SkillEnv
from game_lab.checkpoint import save,load
from game_residual import key


def bank_for(base):
    rng=np.random.default_rng(87);width=92 if base.get('readoutMode') and not base.get('criticFeatureContext') else 348
    return dict(observations=rng.normal(size=(20,width)).astype(np.float32),
        actions=rng.uniform(-1,1,size=(20,2)).astype(np.float32),
        next_observations=rng.normal(size=(20,width)).astype(np.float32),
        dones=np.zeros((20,1),dtype=np.float32),rewards=np.ones((20,1),dtype=np.float32))


def publish(path,base,bank):
    path.mkdir();np.savez_compressed(path/'transitions.npz',**bank)
    report=dict(version=VERSION,baseHash=key(base),sources=source_hashes(),transitions=len(bank['actions']),
        transitionHash=digest(path/'transitions.npz'),seed=81913)
    atomic_report(path/'manifest.json',report)


class DemonstrationChecks(unittest.TestCase):
    def test_online_overwrite_preserves_bank_and_timeout_bootstrapping(self):
        base=configure(Actor('gru-maneuver',128).export(),'plastic');bank=bank_for(base)
        bank['observations'][:]=2;bank['dones'][:]=1
        replay=DemonstrationReplay(4,spaces.Box(-5,5,(92,),dtype=np.float32),spaces.Box(-1,1,(2,),dtype=np.float32),device='cpu')
        replay.attach(bank,fraction=.25)
        for _ in range(12):replay.add(np.zeros((1,92)),np.ones((1,92)),np.zeros((1,2)),np.zeros(1),np.ones(1),[{'TimeLimit.truncated':True}])
        sample=replay.sample(8)
        self.assertEqual(sample.observations.shape,(8,92))
        np.testing.assert_array_equal(sample.dones[:6].numpy(),np.zeros((6,1)))
        np.testing.assert_array_equal(sample.dones[6:].numpy(),np.ones((2,1)))
        np.testing.assert_array_equal(replay.demonstrations['observations'],bank['observations'])
        self.assertFalse(replay.demonstrations['actions'].flags.writeable)
        self.assertFalse(replay.observations.any());self.assertEqual(replay.size(),4)

    def test_bank_rejects_different_base_sources_and_corruption(self):
        base=configure(Actor('gru-maneuver',128).export(),'plastic')
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'bank';publish(path,base,bank_for(base));load_bank(path,base)
            changed=__import__('copy').deepcopy(base);changed['weights']['head.bias'][0]+=.001
            with self.assertRaisesRegex(ValueError,'contract'):load_bank(path,changed)
            report=__import__('json').loads((path/'manifest.json').read_text());report['sources']['game_simulation.py']='changed'
            atomic_report(path/'manifest.json',report)
            with self.assertRaisesRegex(ValueError,'contract'):load_bank(path,base)
            report['sources']=source_hashes();atomic_report(path/'manifest.json',report)
            with (path/'transitions.npz').open('ab') as stream:stream.write(b'changed')
            with self.assertRaisesRegex(ValueError,'damaged'):load_bank(path,base)

    def test_mixed_replay_and_optimizer_resume_exactly_for_both_methods(self):
        torch.set_num_threads(1);torch.manual_seed(31)
        base=configure(Actor('gru-maneuver',128,maneuver_hidden=32,maneuver_scale=.7).export(),'plastic')
        for method in ('sac','td3'):
            with self.subTest(method=method),tempfile.TemporaryDirectory() as root:
                path=Path(root)/'bank';publish(path,base,bank_for(base))
                model,env=initialize(base,method,seed=24,family='solo',duration=2.,demonstrations=path,pedal_retention=1.)
                model._skill['warmup']=0;model.learn(32)
                save(model,Path(root)/'checkpoint',method=method,contract={'expertReplay':1})
                model.learn(32,reset_num_timesteps=False)
                expected={k:v.detach().clone() for k,v in model.policy.state_dict().items()}
                state=env.episode.world.state.copy()
                resumed,_=load(Path(root)/'checkpoint',SkillEnv(base,family='solo',duration=2.),contract={'expertReplay':1})
                resumed.learn(32,reset_num_timesteps=False)
                for k,v in resumed.policy.state_dict().items():np.testing.assert_array_equal(v.detach().numpy(),expected[k].numpy(),err_msg=method+' '+k)
                np.testing.assert_array_equal(resumed.get_env().envs[0].unwrapped.episode.world.state,state)
                np.testing.assert_array_equal(resumed.replay_buffer.demonstrations['actions'],model.replay_buffer.demonstrations['actions'])
                self.assertFalse(resumed.replay_buffer.demonstrations['actions'].flags.writeable)
                self.assertEqual(resumed._skill['expertReplay'],model._skill['expertReplay'])


if __name__=='__main__':unittest.main()
