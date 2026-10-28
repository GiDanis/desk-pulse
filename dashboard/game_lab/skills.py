"""Reference learners refine direct actuators over frozen recurrent skills.

The recurrent encoder is neural, causal and frozen during RL. Therefore old
replay features retain their meaning. Every steering/pedal coefficient of the
readout remains trainable. No teacher, target speed or path follower is used.
"""
from copy import deepcopy
import numpy as np
import torch
from gymnasium import spaces
from stable_baselines3 import PPO,SAC,TD3
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.distributions import DiagGaussianDistribution,StateDependentNoiseDistribution
from stable_baselines3.common.noise import NormalActionNoise
from game_lab.environment import RacingEnv
from game_temporal import TemporalPolicy
from game_residual import key
from game_lab.actuators import MODE,CRITIC_CONTEXT,NeuralActuators,NeuralSACPolicy,NeuralTD3Policy,configure,specification


class SkillEnv(RacingEnv):
    def __init__(self,policy,**kwargs):
        if policy.get('architecture') not in ('gru','gru-skip','gru-adapter','gru-intent','gru-intent-deep','gru-maneuver'):raise ValueError('Recurrent direct skill required')
        self.skill_policy=deepcopy(policy);self.skill_hash=key(policy);self.encoder=TemporalPolicy(policy);self.skill_state=None
        super().__init__(feature_version=policy['features'],**kwargs)
        if self.history!=1:raise ValueError('Skill state already owns causal history')
        self.compact_controls=policy.get('readoutMode')==MODE and policy.get('criticFeatureContext')!=CRITIC_CONTEXT
        self.observation_space=spaces.Box(-200.,200.,shape=(92 if self.compact_controls else 348 if self.encoder.arch in ('gru-intent-deep','gru-maneuver') else 220 if self.encoder.arch=='gru-intent' else self.encoder.hidden+90+(128 if self.encoder.arch=='gru-adapter' else 0),),dtype=np.float32)

    def encode(self,raw):
        _,self.skill_state=self.encoder.forward(raw,self.skill_state,encode_only=True)
        value=self.encoder.maneuver_inputs(raw,self.skill_state) if self.compact_controls else self.encoder.readout_features(raw,self.skill_state)
        return value.astype(np.float32)

    def reset(self,**kwargs):
        self.skill_state=None
        raw,info=super().reset(**kwargs)
        return self.encode(raw),info

    def step(self,action):
        raw,r,terminated,truncated,info=super().step(action)
        return self.encode(raw),r,terminated,truncated,info

    def snapshot(self):
        return {**super().snapshot(),'skillPolicyHash':self.skill_hash,'skillState':deepcopy(self.skill_state)}

    def restore(self,state):
        if state.get('skillPolicyHash',key(state['skillPolicy']) if 'skillPolicy' in state else None)!=self.skill_hash:raise ValueError('Frozen skill checkpoint mismatch')
        super().restore(state);self.skill_state=deepcopy(state['skillState'])


class BoundedMeanPolicy(ActorCriticPolicy):
    """Ordinary PPO Gaussian; its learned mean is the exact bounded BC actor."""
    def __init__(self,*args,neural_base=None,**kwargs):
        self.neural_base=neural_base
        super().__init__(*args,**kwargs)

    def _build(self,lr_schedule):
        super()._build(lr_schedule)
        if self.neural_base is not None:self.action_net=NeuralActuators(self.neural_base).to(self.device)
        actor=list(self.action_net.parameters())+[self.log_std];ids={id(p) for p in actor}
        critic=[p for p in self.parameters() if id(p) not in ids]
        self.optimizer=self.optimizer_class([dict(params=actor,role='actor'),dict(params=critic,role='critic')],
            lr=lr_schedule(1),**self.optimizer_kwargs)

    def _get_action_dist_from_latent(self,latent_pi):
        if isinstance(self.action_dist,StateDependentNoiseDistribution):
            # gSDE explores coherently across successive decisions. Unit
            # noise features preserve the declared per-actuator deviation;
            # the neural action mean itself is unchanged.
            noise_features=torch.nn.functional.normalize(latent_pi,dim=-1,eps=1e-8)
            return self.action_dist.proba_distribution(torch.tanh(self.action_net(latent_pi)),self.log_std,noise_features)
        if not isinstance(self.action_dist,DiagGaussianDistribution):raise ValueError('Continuous PPO skill policy')
        return self.action_dist.proba_distribution(torch.tanh(self.action_net(latent_pi)),self.log_std)


def readout(model,method):
    if method=='ppo':return model.policy.action_net
    if method=='sac':return model.actor.mu
    if method=='td3':return model.actor.mu[0]
    raise ValueError('Skill method')


def initialize(base,method='ppo',*,seed=1,family='mixed',bots=1,duration=180.,budget=32768,track='oval-1',single_lap=False,role='driving',update_every=1,steering_retention=None,pedal_retention=None,actor_rate=None,exploration=None,actuator_mode=None,demonstrations=None,demonstration_fraction=.25):
    base=configure(base,actuator_mode);plastic=base.get('readoutMode')==MODE
    if role not in ('driving','tactic'):raise ValueError('Skill role')
    if role=='tactic' and method!='td3':raise ValueError('Tactical specialization requires TD3')
    if type(update_every) is not int or update_every not in (1,2,4):raise ValueError('Gradient collection interval')
    origin=base.get('origin') or {}
    if origin.get('expertReplay') and demonstrations is None:raise ValueError('Refinement requires its explicit demonstration bank')
    bank=bank_report=None
    if demonstrations is not None:
        if method=='ppo':raise ValueError('Expert replay requires off-policy learning')
        from game_lab.demonstrations import load,DemonstrationReplay
        bank,bank_report=load(demonstrations,base)
        if not 0<demonstration_fraction<=.5:raise ValueError('Demonstration replay fraction')
    steering_retention=origin.get('steeringRetention',25.) if steering_retention is None else steering_retention
    pedal_retention=origin.get('pedalRetention',.01) if pedal_retention is None else pedal_retention
    actor_rate=origin.get('actorLearningRate',.000003) if actor_rate is None else actor_rate
    exploration=origin.get('explorationStyle','gaussian') if exploration is None else exploration
    if exploration not in ('gaussian','sde') or (exploration=='sde' and method!='ppo'):raise ValueError('Exploration recipe')
    if not np.isfinite(steering_retention) or not 1<=steering_retention<=10000:raise ValueError('Steering retention coefficient')
    if not np.isfinite(pedal_retention) or not 0<=pedal_retention<=10000:raise ValueError('Pedal retention coefficient')
    if not np.isfinite(actor_rate) or not 1e-7<=actor_rate<=.001:raise ValueError('Actor learning rate')
    env=SkillEnv(base,family=family,bots=bots,duration=duration,track=track,single_lap=single_lap)
    common=dict(seed=seed,device='cpu',gamma=float(np.exp(-.1/40)),learning_rate=.0003,verbose=0)
    policy_kwargs=dict(net_arch=dict(pi=[],vf=[128,128]) if method=='ppo' else dict(pi=[],qf=[128,128]),activation_fn=torch.nn.Tanh)
    if plastic:policy_kwargs['neural_base']=specification(base)
    if method=='ppo':
        model=PPO(BoundedMeanPolicy,env,n_steps=128,batch_size=64,n_epochs=4,gae_lambda=.99,
            clip_range=.1,target_kl=.01,use_sde=exploration=='sde',sde_sample_freq=64 if exploration=='sde' else -1,
            policy_kwargs=policy_kwargs,**common)
    else:
        opts=dict(policy_kwargs=policy_kwargs,
            buffer_size=32768,batch_size=128,learning_starts=0,train_freq=update_every,gradient_steps=1)
        if bank is not None:opts['replay_buffer_class']=DemonstrationReplay
        if method=='sac':model=SAC(NeuralSACPolicy if plastic else 'MlpPolicy',env,ent_coef='auto_0.001',target_entropy=-7.,**opts,**common)
        elif method=='td3':model=TD3(NeuralTD3Policy if plastic else 'MlpPolicy',env,action_noise=NormalActionNoise(np.zeros(2),np.array([.003,.04])),
            target_policy_noise=.02,target_noise_clip=.05,**opts,**common)
        else:raise ValueError('Skill method')
    layer=readout(model,method);h=base['hidden'];w=base['weights']
    weight=readout_weights(base)
    with torch.no_grad():
        if not plastic:
            layer.weight.copy_(torch.as_tensor(weight,dtype=torch.float32));layer.bias.copy_(torch.as_tensor(w['head.bias'],dtype=torch.float32))
        if method=='ppo':model.policy.log_std.copy_(torch.tensor([-5.8,-3.]))
        if method=='sac':model.actor.log_std.weight.zero_();model.actor.log_std.bias.copy_(torch.tensor([-5.8,-3.]))
    if method=='td3':model.actor_target.load_state_dict(model.actor.state_dict())
    if bank is not None:model.replay_buffer.attach(bank,fraction=demonstration_fraction)
    model._skill=dict(version='causal-skill-readout-1',base=deepcopy(base),baseHash=key(base),method=method,seed=seed,budget=budget,role=role,
        critic='same frozen causal features as actor',warmup=1024,updateEvery=128 if method=='ppo' else update_every,
        steeringRetention=float(steering_retention),pedalRetention=float(pedal_retention),actorLearningRate=float(actor_rate),explorationStyle=exploration)
    if bank_report:model._skill['expertReplay']=dict(version=bank_report['version'],transitionHash=bank_report['transitionHash'],
        transitions=bank_report['transitions'],fraction=demonstration_fraction,collectionSeed=bank_report['seed'])
    install_prior(model)
    return model,env


def install_prior(model):
    """Soft steering retention while the critic learns, with free pedals.

    Optimizer groups are unchanged, so SB3 save/load retains Adam moments.
    The prior is the original neural readout; the teacher is never invoked.
    """
    spec=model._skill;method=spec['method'];layer=readout(model,method)
    base=spec['base'];w=base['weights']
    if base.get('readoutMode')==MODE:
        fixed=NeuralActuators(specification(base)).eval()
        for p in fixed.parameters():p.requires_grad_(False)
    else:
        fixed_w=torch.tensor(readout_weights(base),dtype=torch.float32)
        fixed_b=torch.tensor(w['head.bias'],dtype=torch.float32)
        fixed=lambda x:torch.nn.functional.linear(x,fixed_w,fixed_b)
    optimizer=model.policy.optimizer if method=='ppo' else model.actor.optimizer
    original=optimizer.step;batch={}
    layer.register_forward_pre_hook(lambda _,args:batch.update(x=args[0].detach()))
    def step(*args,**kwargs):
        if model.num_timesteps<spec['warmup']:
            if method!='ppo':return None
            for p in layer.parameters():p.grad=None
            model.policy.log_std.grad=None
        elif batch.get('x') is not None:
            with torch.enable_grad():
                x=batch['x'];prediction=torch.tanh(layer(x));target=torch.tanh(fixed(x))
                # Penalty is in actual actuator space, and never constrains an
                # action at inference or overwrites the learner's command.
                strength=max(.05,1.-model.num_timesteps/max(1,spec['budget']))
                penalty=((prediction-target)**2*torch.tensor([spec.get('steeringRetention',25.),spec.get('pedalRetention',.01)])).mean()*strength
                gradients=torch.autograd.grad(penalty,tuple(layer.parameters()))
                for p,g in zip(layer.parameters(),gradients):p.grad=g.detach() if p.grad is None else p.grad+g.detach()
        for group in optimizer.param_groups:
            if method!='ppo' or group.get('role')=='actor':group['lr']=spec.get('actorLearningRate',.000003)
        return original(*args,**kwargs)
    optimizer.step=step


def export(model):
    spec=model._skill;data=deepcopy(spec['base']);method=spec['method'];layer=readout(model,method);h=data['hidden']
    data['architecture']=data['architecture'] if data['architecture'] in ('gru-adapter','gru-intent','gru-intent-deep','gru-maneuver') else 'gru-skip';data['algorithm']='residual_tactic' if spec.get('role')=='tactic' else 'residual_'+method
    h,s=head_sizes(data)
    if data.get('readoutMode')==MODE:
        data['weights'].update({k:v.detach().cpu().numpy().astype(float).tolist() for k,v in layer.state_dict().items()})
    else:
        data['weights']['head.weight']=layer.weight[:,:h].detach().cpu().numpy().astype(float).tolist()
        data['weights']['skip.weight']=layer.weight[:,h:h+s].detach().cpu().numpy().astype(float).tolist()
        if data['architecture']=='gru-adapter':data['weights']['adapter_head.weight']=layer.weight[:,h+90:].detach().cpu().numpy().astype(float).tolist()
        data['weights']['head.bias']=layer.bias.detach().cpu().numpy().astype(float).tolist()
    data['origin']={**(data.get('origin') or {}),'stage':'reference-skill-refinement','method':method,
        'seed':spec['seed'],'baseHash':spec['baseHash'] if 'baseHash' in spec else key(spec['base']),'decisions':model.num_timesteps,
        'updateEvery':spec.get('updateEvery',128 if method=='ppo' else 1),
        'steeringRetention':spec.get('steeringRetention',25.),'pedalRetention':spec.get('pedalRetention',.01),'actorLearningRate':spec.get('actorLearningRate',.000003),
        'explorationStyle':spec.get('explorationStyle','gaussian'),
        'backend':'sb3-skill-1','role':spec.get('role','driving'),'teacherCallsDuringRL':0,'encoderTrainable':False,'actuatorsTrainable':True,
        'controlEncodersTrainable':data.get('readoutMode')==MODE}
    if data.get('criticFeatureContext'):data['origin']['criticFeatureContext']=data['criticFeatureContext']
    if spec.get('expertReplay'):data['origin']['expertReplay']=deepcopy(spec['expertReplay'])
    TemporalPolicy(data)
    return data


def readout_weights(base):
    w=base['weights'];parts=[np.asarray(w['head.weight']),np.asarray(w.get('skip.weight',np.zeros((2,90))))]
    if base['architecture']=='gru-adapter':parts.append(np.asarray(w['adapter_head.weight']))
    return np.concatenate(parts,axis=1)


def head_sizes(base):return (256,92) if base['architecture'] in ('gru-intent-deep','gru-maneuver') else (128,92) if base['architecture']=='gru-intent' else (base['hidden'],90)
