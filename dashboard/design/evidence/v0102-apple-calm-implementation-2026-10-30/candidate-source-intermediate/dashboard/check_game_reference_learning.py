"""Critic warmup and a training-only prior do not alter inference actuators."""
import unittest
import numpy as np
import torch
from game_lab.environment import RacingEnv
from game_lab.reference_learning import CalibratedTD3,CalibratedPPO,layers,install_training_prior,action_tensor,export
from game_temporal import TemporalPolicy


class ReferenceLearningChecks(unittest.TestCase):
    def test_td3_warmup_keeps_actor_then_allows_updates(self):
        torch.set_num_threads(1)
        model=CalibratedTD3('MlpPolicy',RacingEnv(),policy_kwargs=dict(net_arch=[64],activation_fn=torch.nn.Tanh),device='cpu',seed=3)
        first,last=layers(model,'td3');parameters=list(first.parameters())+list(last.parameters())
        before=[p.detach().clone() for p in parameters];install_training_prior(model,'td3')
        x=torch.randn(8,90);action_tensor(model,'td3',x).sum().backward();model.actor.optimizer.step()
        for a,b in zip(before,parameters):self.assertTrue(torch.equal(a,b))
        model.num_timesteps=5000;model.actor.optimizer.zero_grad();action_tensor(model,'td3',x).sum().backward();model.actor.optimizer.step()
        self.assertTrue(any(not torch.equal(a,b) for a,b in zip(before,parameters)))
        policy=TemporalPolicy(export(model,'td3',1,{}))
        value,_=policy.forward(x[0].numpy())
        with torch.no_grad():expected=action_tensor(model,'td3',x)[0].numpy()
        np.testing.assert_allclose(value,expected,atol=2e-6)

    def test_normalized_history_export_matches_reference_prediction(self):
        from game_lab.normalization import PhysicalFeatures
        history=4;mean=np.linspace(-.2,.3,90);scale=np.linspace(.1,1.5,90)
        env=RacingEnv(history=history)
        model=CalibratedTD3('MlpPolicy',env,policy_kwargs=dict(net_arch=[128],activation_fn=torch.nn.Tanh,
            features_extractor_class=PhysicalFeatures,features_extractor_kwargs=dict(mean=mean,scale=scale)),device='cpu',seed=5)
        policy=TemporalPolicy(export(model,'td3',history,{}));state=None
        rng=np.random.default_rng(15);xs=rng.uniform(-.5,.5,(7,90)).astype(np.float32)
        for i,x in enumerate(xs):
            action,state=policy.forward(x,state)
            frames=[xs[max(0,j)] for j in range(i-history+1,i+1)]
            expected=model.predict(np.concatenate(frames),deterministic=True)[0]
            np.testing.assert_allclose(action,expected,atol=2e-6)
        install_training_prior(model,'td3');model.num_timesteps=5000
        data=torch.tensor(np.concatenate(frames)[None,:]);prediction=action_tensor(model,'td3',data)
        before=model.actor.mu[0].weight.detach().clone()
        prediction.sum().backward();model.actor.optimizer.step()
        self.assertFalse(torch.equal(before,model.actor.mu[0].weight))

    def test_ppo_actor_can_wait_while_critic_learns(self):
        model=CalibratedPPO('MlpPolicy',RacingEnv(),n_steps=8,batch_size=8,
            policy_kwargs=dict(net_arch=[64],activation_fn=torch.nn.Tanh),device='cpu',seed=4)
        install_training_prior(model,'ppo')
        first,_=layers(model,'ppo');actor=first.weight.detach().clone()
        critic=model.policy.value_net.weight.detach().clone()
        for p in model.policy.parameters():p.grad=torch.ones_like(p)
        model.policy.optimizer.step()
        self.assertTrue(torch.equal(first.weight,actor));self.assertFalse(torch.equal(model.policy.value_net.weight,critic))


if __name__=='__main__':unittest.main()
