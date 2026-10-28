"""A real update after reload must match an uninterrupted reference learner."""
from pathlib import Path
import tempfile,unittest
import numpy as np
import torch
from game_lab.environment import RacingEnv
from game_lab.reference_learning import CalibratedPPO,CalibratedSAC,CalibratedTD3,install_training_prior
from game_lab.checkpoint import save,load


class ReferenceCheckpointChecks(unittest.TestCase):
    def test_ppo_sac_td3_resume_next_updates_exactly(self):
        torch.set_num_threads(1)
        for method,cls in [('ppo',CalibratedPPO),('sac',CalibratedSAC),('td3',CalibratedTD3)]:
            with self.subTest(method=method),tempfile.TemporaryDirectory() as root:
                env=RacingEnv(family='mixed',history=4,duration=2.)
                options=dict(n_steps=8,batch_size=8,n_epochs=1) if method=='ppo' else dict(buffer_size=128,batch_size=8,learning_starts=0)
                model=cls('MlpPolicy',env,seed=42,device='cpu',policy_kwargs=dict(net_arch=[64],activation_fn=torch.nn.Tanh),**options)
                install_training_prior(model,method,warmup=0)
                model.learn(16);saved=save(model,Path(root)/'snapshot',method=method,contract={'physics':'same','dataset':'fixed'})
                model.learn(16,reset_num_timesteps=False)
                expected={k:v.detach().clone() for k,v in model.policy.state_dict().items()}
                physical=env.episode.world.state.copy();obs=model._last_obs.copy()
                restored_env=RacingEnv(family='mixed',history=4,duration=2.)
                restored,receipt=load(Path(root)/'snapshot',restored_env,contract={'physics':'same','dataset':'fixed'})
                self.assertEqual(saved,receipt);restored.learn(16,reset_num_timesteps=False)
                for k,v in restored.policy.state_dict().items():
                    np.testing.assert_array_equal(v.detach().numpy(),expected[k].numpy(),err_msg=method+' '+k)
                np.testing.assert_array_equal(restored_env.episode.world.state,physical)
                np.testing.assert_array_equal(restored._last_obs,obs)
                with self.assertRaises(ValueError):load(Path(root)/'snapshot',restored_env,contract={'dataset':'other'})
                (Path(root)/'snapshot/state.pkl').write_bytes(b'broken')
                with self.assertRaises(ValueError):load(Path(root)/'snapshot',restored_env,contract={'physics':'same','dataset':'fixed'})


if __name__=='__main__':unittest.main()
