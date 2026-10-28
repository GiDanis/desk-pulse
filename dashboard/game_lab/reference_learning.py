"""Standard SB3 algorithms on a common SmartPC observation/action contract.

No imported reference weights or action corrections. Each experiment retains
its own imitation-only actor, learner, replay, seeds and deterministic export.
"""
from pathlib import Path
import json,math,time
import numpy as np
import torch
from torch import nn
from stable_baselines3 import PPO,SAC,TD3
from game_lab.environment import RacingEnv


class CalibratedActorRate:
    def _update_learning_rate(self,optimizers):
        super()._update_learning_rate(optimizers)
        actor=getattr(self,'actor',None)
        if actor is not None:
            for group in actor.optimizer.param_groups:group['lr']=.00003
        elif hasattr(self,'policy'):
            for group in self.policy.optimizer.param_groups:
                if group.get('role')=='actor':group['lr']=.00003


class CalibratedPPO(CalibratedActorRate,PPO):
    def _setup_model(self):
        super()._setup_model()
        actor=list(self.policy.mlp_extractor.policy_net[0].parameters())+list(self.policy.action_net.parameters())+[self.policy.log_std]
        ids={id(p) for p in actor};critic=[p for p in self.policy.parameters() if id(p) not in ids]
        self.policy.optimizer=self.policy.optimizer_class([dict(params=actor,role='actor'),dict(params=critic,role='critic')],
            lr=self.lr_schedule(1),**self.policy.optimizer_kwargs)

class CalibratedSAC(CalibratedActorRate,SAC):pass
class CalibratedTD3(CalibratedActorRate,TD3):pass


def layers(model,method):
    if method=='ppo':return model.policy.mlp_extractor.policy_net[0],model.policy.action_net
    if method=='sac':return model.policy.actor.latent_pi[0],model.policy.actor.mu
    return model.policy.actor.mu[0],model.policy.actor.mu[2]


def action_tensor(model,method,x):
    first,last=layers(model,method)
    extractor=model.policy.features_extractor if method=='ppo' else model.actor.features_extractor
    raw=last(torch.tanh(first(extractor(x))))
    return torch.clamp(raw,-1,1) if method=='ppo' else torch.tanh(raw)


def export(model,method,history,origin):
    from game_direct import ACTION,FEATURES
    first,last=layers(model,method)
    extractor=model.policy.features_extractor if method=='ppo' else model.actor.features_extractor
    mean=getattr(extractor,'mean',torch.zeros(90))[:90];scale=getattr(extractor,'scale',torch.ones(90))[:90]
    def array(x):return x.detach().cpu().numpy().astype(float).tolist()
    return dict(schema=1,kind='temporal-direct',algorithm='residual_'+method,observation='race-68-v3',inputs=68,
        action=ACTION,features=FEATURES,featureInputs=90,decisionHz=10,physicsHz=60,teacherAtInference=False,
        architecture='history' if history>1 else 'dense',hidden=first.out_features,history=history,
        normalization=dict(mean=array(mean),scale=array(scale)),outputActivation='clip' if method=='ppo' else 'tanh',
        weights={'core.weight':array(first.weight),'core.bias':array(first.bias),'head.weight':array(last.weight),'head.bias':array(last.bias)},origin=origin)


def causal_history(x,history):
    padded=np.concatenate((np.repeat(x[:1],history-1,axis=0),x),axis=0)
    return np.stack([padded[i:i+history].ravel() for i in range(len(x))])


def install_training_prior(model,method,*,warmup=4096):
    """Training-only soft prior and critic warmup. Inference remains free.

    No teacher is called. The prior is the independently prepared neural actor;
    pedal anchoring is weak, steering anchoring decays with collected data.
    """
    first,last=layers(model,method)
    parameters=list(first.parameters())+list(last.parameters())
    previous=getattr(model,'_smartpc_prior',None)
    if previous and previous['method']!=method:raise ValueError('Reference prior method mismatch')
    fixed=previous['fixed'] if previous else [p.detach().clone() for p in parameters]
    model._smartpc_prior=dict(method=method,fixed=fixed,warmup=warmup)
    if method=='ppo':
        parameters+=[model.policy.log_std]
        optimizer=model.policy.optimizer
    else:optimizer=model.actor.optimizer
    batch={}
    def observe(_module,inputs):batch['x']=inputs[0].detach()
    first.register_forward_pre_hook(observe)
    original_step=optimizer.step
    def step(*args,**kwargs):
        if model.num_timesteps<warmup:
            if method!='ppo':return None
            for p in parameters:p.grad=None
        elif batch.get('x') is not None:
            with torch.enable_grad():
                x=batch['x'];raw_prediction=last(torch.tanh(first(x)))
                prediction=torch.clamp(raw_prediction,-1,1) if method=='ppo' else torch.tanh(raw_prediction)
                raw=torch.nn.functional.linear(torch.tanh(torch.nn.functional.linear(x,fixed[0],fixed[1])),fixed[2],fixed[3])
                target=torch.clamp(raw,-1,1) if method=='ppo' else torch.tanh(raw)
                strength=max(.025,.25*(1-model.num_timesteps/32768))
                loss=((prediction-target)**2*torch.tensor([25.,.05])).mean()*strength
                gradients=torch.autograd.grad(loss,parameters,allow_unused=True)
                for p,g in zip(parameters,gradients):
                    if g is not None:p.grad=g.detach() if p.grad is None else p.grad+g.detach()
        return original_step(*args,**kwargs)
    optimizer.step=step


def seed_replay(model,dataset,history,rng):
    added=0
    for path in sorted(Path(dataset).glob('train-*.npz')):
        with np.load(path,allow_pickle=False) as data:
            if any(k not in data for k in ('u','next_x','terminated','truncated')):continue
            x=data['x'];history_x=causal_history(x,history)
            for i in np.sort(rng.choice(len(x),min(128,len(x)),replace=False)):
                nxt=np.r_[history_x[i,90:],data['next_x'][i]] if history>1 else data['next_x'][i]
                terminated=bool(data['terminated'][i]);truncated=bool(data['truncated'][i])
                model.replay_buffer.add(history_x[i][None,:],nxt[None,:],data['u'][i][None,:],
                    np.array([data['rewards'][i]]),np.array([terminated or truncated]),
                    [dict(TimeLimit_truncated=truncated and not terminated,**{'TimeLimit.truncated':truncated and not terminated})])
                added+=1
    return added


def train(output,dataset,*,method='td3',seed=1,history=4,decisions=32768,bc_updates=2000,recipe='standard'):
    from game_lab.dataset import load_sequences
    from game_temporal import TemporalPolicy
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(1);torch.manual_seed(seed);rng=np.random.default_rng(seed)
    from game_lab.artifacts import freeze_dataset
    dataset_manifest=freeze_dataset(dataset,output/'dataset');dataset=output/'dataset'
    sequences=load_sequences(dataset)
    normalized=recipe=='normalized-anchored-2'
    env=RacingEnv(history=history,**(dict(family='mixed',duration=180.) if normalized else {}))
    policy_kwargs=dict(net_arch=[128 if normalized else 64],activation_fn=nn.Tanh)
    if normalized:
        from game_lab.normalization import PhysicalFeatures
        all_x=np.concatenate([s['x'] for s in sequences])
        policy_kwargs.update(features_extractor_class=PhysicalFeatures,features_extractor_kwargs=dict(
            mean=np.mean(all_x,axis=0).tolist(),scale=np.maximum(.05,np.std(all_x,axis=0)).tolist()))
    common=dict(policy_kwargs=policy_kwargs,seed=seed,device='cpu',verbose=0,
        gamma=math.exp(-.1/40.),learning_rate=.0003)
    calibrated=recipe in ('teacher-anchored-1','normalized-anchored-2')
    if recipe not in ('standard','teacher-anchored-1','normalized-anchored-2'):raise ValueError('Reference recipe')
    if method=='ppo':model=(CalibratedPPO if calibrated else PPO)('MlpPolicy',env,n_steps=512,batch_size=128,n_epochs=4,gae_lambda=.99,**({'target_kl':.01,'clip_range':.1} if calibrated else {}),**common)
    elif method=='sac':model=(CalibratedSAC if calibrated else SAC)('MlpPolicy',env,buffer_size=32768,learning_starts=256,batch_size=128,train_freq=1,gradient_steps=1,**({'ent_coef':'auto_0.01','target_entropy':-5.} if calibrated else {}),**common)
    elif method=='td3':
        from stable_baselines3.common.noise import NormalActionNoise
        model=(CalibratedTD3 if calibrated else TD3)('MlpPolicy',env,buffer_size=32768,learning_starts=256,batch_size=128,train_freq=1,gradient_steps=1,
            action_noise=NormalActionNoise(np.zeros(2),np.array([.025,.1] if calibrated else [.08,.12])),
            **({'target_policy_noise':.05,'target_noise_clip':.1} if calibrated else {}),**common)
    else:raise ValueError('Reference method')
    x=np.concatenate([causal_history(s['x'],history) for s in sequences]);y=np.concatenate([s['y'] for s in sequences])
    first,last=layers(model,method);optimizer=torch.optim.Adam(list(first.parameters())+list(last.parameters()),lr=.001)
    losses=[];started=time.monotonic()
    for update in range(bc_updates):
        indices=rng.integers(0,len(x),128)
        predicted=action_tensor(model,method,torch.as_tensor(x[indices],dtype=torch.float32))
        loss=((predicted-torch.as_tensor(y[indices],dtype=torch.float32))**2*torch.tensor([25. if normalized else 4.,1.])).mean()
        optimizer.zero_grad();loss.backward();optimizer.step()
        if update%100==0:losses.append(float(loss.detach()))
    # Targets must start from the prepared actor, not from the discarded random
    # initialization. SAC has no target actor, TD3 does.
    if method=='td3':model.policy.actor_target.load_state_dict(model.policy.actor.state_dict())
    if calibrated:
        with torch.no_grad():
            if method=='ppo':model.policy.log_std.copy_(torch.tensor([-3.5,-1.75]))
            elif method=='sac':model.actor.log_std.weight.zero_();model.actor.log_std.bias.copy_(torch.tensor([-3.5,-1.75]))
    origin=dict(kind='sb3-independent-imitation',method=method,seed=seed,examples=len(x),bcUpdates=bc_updates,recipe=recipe,datasetHash=dataset_manifest['hash'])
    base=export(model,method,history,origin)
    # Check export against the actual reference policy's deterministic API.
    observations=x[rng.integers(0,len(x),16)].astype(np.float32)
    expected=model.predict(observations,deterministic=True)[0]
    first,last=layers(model,method)
    with torch.no_grad():actual=action_tensor(model,method,torch.as_tensor(observations)).numpy()
    np.testing.assert_allclose(actual,expected,atol=2e-6,rtol=2e-5)
    (output/'base.json').write_text(json.dumps(base,separators=(',',':'))+'\n')
    model.save(output/'imitation-model')
    offline=0;warmup_updates=0
    if calibrated:
        install_training_prior(model,method)
        if method!='ppo':
            from stable_baselines3.common.logger import configure
            model.set_logger(configure(format_strings=[]))
            offline=seed_replay(model,dataset,history,rng)
            if offline:model.train(gradient_steps=2048,batch_size=128);warmup_updates=2048
    model.learn(total_timesteps=decisions,progress_bar=False)
    candidate=export(model,method,history,{**origin,'kind':'sb3-refinement','decisions':model.num_timesteps})
    TemporalPolicy(candidate)
    (output/'policy.json').write_text(json.dumps(candidate,separators=(',',':'))+'\n')
    model.save(output/'model')
    from game_lab.provenance import contract
    from game_lab.checkpoint import save
    from game_residual import key
    binding=contract(method=method,recipe=recipe,seed=seed,history=history,dataset_hash=dataset_manifest['hash'],
        base_hash=key(base),environment=dict(env.options,history=history))
    save(model,output/('snapshot-'+str(model.num_timesteps)),method=method,contract=binding)
    if method!='ppo':model.save_replay_buffer(output/'replay.pkl')
    report=dict(method=method,seed=seed,history=history,recipe=recipe,critic='same causal inputs as actor; no privileged task features',
        datasetHash=dataset_manifest['hash'],behaviorCloningUpdates=bc_updates,losses=losses,decisions=model.num_timesteps,physicsStepsCollected=env.total_physics_steps,
        learnerUpdates=model._n_updates,
        offlineTransitions=offline,criticWarmupUpdates=warmup_updates,teacherCallsDuringRL=0,
        decisionSeconds=.1,gamma=common['gamma'],wallSeconds=time.monotonic()-started,qualified=False)
    (output/'training.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def continue_training(output,checkpoint,*,decisions):
    """Resume at a complete update boundary, preserving the original BC base."""
    from game_lab.checkpoint import load,save
    from game_lab.provenance import verify
    from game_residual import key
    output=Path(output);checkpoint=Path(checkpoint)
    manifest=json.loads((checkpoint/'manifest.json').read_text());binding=manifest['contract'];verify(binding)
    base_path=checkpoint.parent/'base.json';base=json.loads(base_path.read_text())
    if key(base)!=binding['baseHash']:raise ValueError('Original imitation base changed')
    if output.exists():raise ValueError('Continuation output already exists')
    output.mkdir(parents=True)
    env=RacingEnv(**binding['environment']);model,_=load(checkpoint,env,contract=binding)
    before_steps=env.total_physics_steps;before_decisions=model.num_timesteps;started=time.monotonic()
    model.learn(total_timesteps=decisions,reset_num_timesteps=False)
    origin=dict(base['origin'],kind='sb3-refinement',decisions=model.num_timesteps,resumedFrom=str(checkpoint))
    candidate=export(model,binding['method'],binding['history'],origin)
    (output/'base.json').write_bytes(base_path.read_bytes())
    from game_lab.artifacts import atomic_report
    atomic_report(output/'policy.json',candidate)
    snapshot=output/('snapshot-'+str(model.num_timesteps))
    save(model,snapshot,method=binding['method'],contract=binding)
    report=dict(method=binding['method'],datasetHash=binding['datasetHash'],seed=binding['seed'],recipe=binding['recipe'],
        decisions=model.num_timesteps,decisionsThisStage=model.num_timesteps-before_decisions,
        physicsStepsCollected=env.total_physics_steps-before_steps,learnerUpdates=model._n_updates,
        teacherCallsDuringRL=0,wallSeconds=time.monotonic()-started,qualified=False,snapshot=str(snapshot))
    atomic_report(output/'training.json',report)
    return report
