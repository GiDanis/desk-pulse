"""Explicit, immutable training demonstrations and protected online replay.

These are real transitions in the current physics, encoded by the learner's
own frozen causal memory. Teacher intent/labels never enter observations.
The expert bank is training data, not a controller or a release certificate.
"""
from pathlib import Path
import json
import numpy as np
import torch
from stable_baselines3.common.buffers import ReplayBuffer
from stable_baselines3.common.type_aliases import ReplayBufferSamples
from game_lab.artifacts import atomic_report,digest
from game_lab.provenance import source_hashes
from game_residual import key

VERSION='causal-expert-transitions-1'
FIELDS=('observations','actions','next_observations','dones','rewards')
FAMILIES=('solo','traffic','attack','complete','corner','defend','recover')


def collect(base,output,*,seed,seconds=90.,capacity=16384):
    from game_lab.skills import SkillEnv
    from game_lab.teacher import Teacher
    from game_catalog import configuration
    if base['architecture']!='gru-maneuver':raise ValueError('Prepared maneuver policy required')
    if type(seed) is not int or seed<1 or 980000<=seed<=990000 or 1980000<=seed<=1990000:raise ValueError('Training seed required')
    if seconds<30 or capacity<21:raise ValueError('Demonstration collection budget')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    rng=np.random.default_rng(seed);parts=[];rows=[];teacher_calls=0
    for bots in (1,2,3):
        for family in FAMILIES:
            episode_seed=int(rng.integers(1,2**31-1))
            while 980000<=episode_seed<=990000 or 1980000<=episode_seed<=1990000:episode_seed=int(rng.integers(1,2**31-1))
            env=SkillEnv(base,family=family,bots=bots,duration=seconds)
            observation,_=env.reset(seed=episode_seed);teacher=Teacher();transitions=[]
            while True:
                action=np.clip(teacher.label(env.episode.world),-1.,1.).astype(np.float32)
                next_observation,reward,terminated,truncated,info=env.step(action)
                transitions.append((observation.copy(),action.copy(),next_observation.copy(),float(terminated),float(reward)))
                observation=next_observation
                if terminated or truncated:break
            result=env.episode.result();teacher_calls+=teacher.calls
            accepted=bool(not result['contacts'] and result['trackLimits']<=(1 if family=='recover' else 0)
                and not result.get('racecraft',{}).get('violations',0) and not terminated and env.episode.age>=seconds-.1)
            rows.append(dict(seed=episode_seed,family=family,bots=env.episode.world.count-1,requestedBots=bots,
                decisions=len(transitions),accepted=accepted,result=result))
            if accepted:
                # Equal episode capacity prevents long straights from erasing
                # short approach/defense scenarios. Selection is reproducible.
                count=min(len(transitions),capacity//21)
                indices=np.sort(rng.choice(len(transitions),count,replace=False))
                parts.extend(transitions[i] for i in indices)
            env.close()
            print('demonstration',family,bots,episode_seed,accepted,len(transitions),flush=True)
    report=dict(version=VERSION,split='train',baseHash=key(base),features=base['features'],sources=source_hashes(),
        configuration=configuration('oval-1','race-68-v3'),seed=seed,seconds=seconds,capacity=capacity,
        teacherCallsDuringCollection=teacher_calls,teacherIntentInObservations=False,rows=rows,qualified=False)
    if (len(parts)==0 or {r['family'] for r in rows if r['accepted']}!=set(FAMILIES)
        or {r['bots'] for r in rows if r['accepted'] and r['family']=='traffic'}!={1,2,3}):
        atomic_report(output/'rejected.json',report)
        raise ValueError('Incomplete clean demonstration coverage')
    arrays={name:np.asarray([row[i] for row in parts],dtype=np.float32) for i,name in enumerate(FIELDS)}
    arrays['dones']=arrays['dones'].reshape(-1,1);arrays['rewards']=arrays['rewards'].reshape(-1,1)
    with (output/'transitions.npz').open('wb') as stream:np.savez_compressed(stream,**arrays)
    report.update(transitions=len(parts),transitionHash=digest(output/'transitions.npz'))
    atomic_report(output/'manifest.json',report)
    return report


def load(path,base):
    path=Path(path);report=json.loads((path/'manifest.json').read_text())
    if report['version']!=VERSION or report['baseHash']!=key(base) or report['sources']!=source_hashes():raise ValueError('Demonstration contract changed')
    if digest(path/'transitions.npz')!=report['transitionHash']:raise ValueError('Demonstration bank damaged')
    with np.load(path/'transitions.npz',allow_pickle=False) as data:bank={k:data[k].copy() for k in FIELDS}
    from game_lab.actuators import MODE,CRITIC_CONTEXT
    count=report['transitions'];width=92 if base.get('readoutMode')==MODE and base.get('criticFeatureContext')!=CRITIC_CONTEXT else 348
    expected=dict(observations=(count,width),actions=(count,2),next_observations=(count,width),dones=(count,1),rewards=(count,1))
    if any(bank[k].shape!=shape or not np.isfinite(bank[k]).all() for k,shape in expected.items()):raise ValueError('Demonstration shapes')
    if (np.abs(bank['actions'])>1).any() or not np.isin(bank['dones'],[0,1]).all():raise ValueError('Demonstration controls/terminal mask')
    return bank,report


class DemonstrationReplay(ReplayBuffer):
    """Online capacity is unchanged; a separate bank cannot be overwritten.

    SB3's own sampler handles online timeouts. Expert ``dones`` represent
    physical termination only, so a collection time limit still bootstraps.
    Sampling uses NumPy's checkpointed RNG, including after exact resume.
    """
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.demonstrations=None;self.demonstration_fraction=0.

    def attach(self,bank,*,fraction=.25):
        if not 0<fraction<=.5:raise ValueError('Demonstration replay fraction')
        if bank['observations'].shape[1:]!=self.obs_shape or len(bank['actions'])==0:raise ValueError('Demonstration replay contract')
        self.demonstrations={k:np.array(v,copy=True) for k,v in bank.items()}
        for value in self.demonstrations.values():value.flags.writeable=False
        self.demonstration_fraction=float(fraction)

    def __setstate__(self,state):
        self.__dict__.update(state)
        if self.demonstrations is not None:
            for value in self.demonstrations.values():value.flags.writeable=False

    def sample(self,batch_size,env=None):
        if self.demonstrations is None:return super().sample(batch_size,env)
        count=max(1,int(round(batch_size*self.demonstration_fraction)))
        online=super().sample(batch_size-count,env)
        indices=np.random.randint(len(self.demonstrations['actions']),size=count)
        values=[]
        for field,value in zip(ReplayBufferSamples._fields,online):
            if value is None:values.append(None);continue
            demo=self.demonstrations[field][indices]
            if field in ('observations','next_observations'):demo=self._normalize_obs(demo,env)
            elif field=='rewards':demo=self._normalize_reward(demo,env)
            values.append(torch.cat((value,self.to_torch(demo)),dim=0))
        return ReplayBufferSamples(*values)
