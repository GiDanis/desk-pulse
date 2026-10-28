"""Versioned racing base and residual policies. No training occurs on import."""
from copy import deepcopy
import hashlib
import json
import math
import numpy as np

BASE='race-base-1'
RECIPE='race-residual-4'
STUDY_RECIPE='race-residual-3'
FEATURES='race-residual-90-v1'
ACTION='line-pace-residual-v2'
METHODS=('race_master','residual_ppo','residual_sac','residual_td3','residual_tactic')
ROSTER=(('Maestro','race_master'),('Crono','residual_ppo'),('Memoria','residual_sac'),
        ('Linea','residual_td3'),('Tattico','residual_tactic'))
SCALES=np.array([1.,.25])
DECISION_STEPS=6


def is_residual(profile):return profile.get('algorithm') in METHODS


def legacy_recipe(profile):
    return dict(version='race-residual-2',base=BASE,features=FEATURES,action=ACTION,
        lineMap='base-to-full-corridor-v1',algorithm=profile['algorithm'],learner='td3' if profile['algorithm']=='residual_tactic' else profile['algorithm'].removeprefix('residual_'),decisionHz=10,physicsHz=60,scales=SCALES.tolist(),
        hidden=profile['hidden'],learningRate=profile['learningRate'],seed=profile['seed'],
        gamma=math.exp(-.1/40),gaeLambda=math.exp(-.1/1.6),rollout=128,
        replayCapacity=32768,batchSize=64,gradientEvery=4,tau=.005,
        entropy=.0001,policyDelay=2,targetNoise=.05,exploration=[.01,.15] if profile['algorithm']=='residual_ppo' else [.01,.05],
        reward='residual-racing-1',passRule='held-0.5s-band-v1',
        curriculum='solo-8192-then-mixed-v1' if profile['algorithm']=='residual_tactic' else 'solo-or-selected-traffic-v1')
def recipe(profile):
    result=legacy_recipe(profile)
    if profile.get('racingBackup') in (2,3,5):result['backupSteps']=profile['racingBackup']
    # Explicit private study only. Five-seed held-out traffic regressed: no
    # production preset opts in, and existing replay remains on recipe 2.
    if profile.get('rewardExperiment')=='common-units-1':
        result.update(version=STUDY_RECIPE,reward='residual-racing-2',raceRulesVersion='spatial-rules-2',cutoff='collection-boundary-1')
    elif profile['algorithm']!='race_master' and profile.get('rewardExperiment')!='legacy-1':
        result.update(version=RECIPE,reward='residual-racing-3',criticContext='task-context-1',criticInputs=94,
            shaping='bounded-time-speed-potential-1',gaeLambda=math.exp(-.1/4.),
            exploration=[.04,.15] if profile['algorithm']=='residual_ppo' else [.08,.08],
            ppoEntropy=.0002,minStd=[.03,.05],maxStd=[.25,.25])
        if profile['algorithm']=='residual_ppo':
            result.update(gaeLambda=math.exp(-.1/1.6),ppoEntropy=.0001,potentialPrior=True)
    return result


def value_features(episode,observation=None):
    """Privileged task context for the critic; the racing actor stays local."""
    finite=episode.objective=='impara'
    distance=episode.spec.get('distance')
    remaining=max(0.,1-episode.valid_progress/distance) if finite and distance else 0.
    budget=max(0.,1-episode.age/episode.spec['limitSeconds']) if finite else 0.
    from game_driving_memory import PHASES
    return np.r_[features(episode.world) if observation is None else observation,
                 float(finite),remaining,budget,PHASES.index(episode.phase)/(len(PHASES)-1)]


def learning_potential(episode):
    """Bounded frozen potential, evaluated at a learner decision boundary."""
    from game_rewards import reference_time
    remaining=max(0.,1-episode.valid_progress/episode.spec['distance']) if episode.objective=='impara' and episode.spec.get('distance') else 0.
    _,heading,_=episode.world.coordinates()
    angle=float(heading[0]-episode.world.state[0,2])
    reference_speed=episode.world.track.length/reference_time(episode.world,episode.reward_spec)
    forward_speed=max(0.,float(episode.world.state[0,3])*math.cos(angle))
    return -.25*remaining+.05*float(np.clip(forward_speed/reference_speed,0,2))


def potential_from_value_features(observation):
    """Value prior for the catalog's tracks (all longer than 180 m)."""
    x=np.asarray(observation)
    reference=9*np.sqrt(np.maximum(.1,x[...,89])/.95)
    speed=np.maximum(0,x[...,71]*30*np.cos(x[...,10]*math.pi))
    return -.25*x[...,91]+.05*np.clip(speed/reference,0,2)


def profile(seed,method):
    from game_profiles import preset
    p=preset(seed,'ppo')
    p.update(version=2,algorithm=method,observation='race-68-v3',hidden=32,
        population=1,rollout=128,learningRate=.0001,gamma=math.exp(-.1/40),recipeVersion=1)
    return p


def snapshot(profile,weights=None):
    if profile.get('controlMode')=='direct':
        from game_direct_bootstrap import initial_policy
        from game_direct import snapshot as direct_snapshot
        return initial_policy(profile) if weights is None else direct_snapshot(profile,weights)
    return dict(schema=1,kind='racing',algorithm=profile['algorithm'],observation='race-68-v3',
        action=ACTION,inputs=68,featureInputs=90,hidden=profile['hidden'],
        base=BASE,recipe=recipe(profile),weights=None if weights is None else np.asarray(weights).tolist())


def seed_policy(profile):
    if profile.get('controlMode')=='direct':
        from game_direct_bootstrap import initial_policy
        return initial_policy(profile)
    return snapshot(profile,None if profile['algorithm']=='race_master' else initial_weights(profile))


def key(policy):
    return hashlib.sha256(json.dumps(policy,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def features(world,index=0):
    """Causal fixed-role observations; querying does not advance the base state."""
    from game_control import racing_actions
    w=world;i=int(index);obs=w.observations(version='race-68-v3')[i].copy();obs[64:68]=0
    rule=getattr(w,'residual_rules',{}).get(i,{})
    obs[64:66]=[float(rule.get('armed',False)),rule.get('moveDirection',0)]
    lane=w.racing_lane.copy()
    base=racing_actions(w,[i])[0];w.racing_lane[:]=lane
    extra=np.zeros(22);extra[:2]=base
    extra[2]=lane[i]/max(1,w.track.width/2)
    extra[3]=w.state[i,3]/30
    previous=getattr(w,'residual_previous',np.zeros((w.count,2)))
    extra[4:6]=previous[i]
    own=w.state[i];c,s=np.cos(own[2]),np.sin(own[2])
    nearby=[]
    for j in range(w.count):
        if i==j or not w.active[j]:continue
        d=w.progress[j]-w.progress[i]
        if getattr(w,'continuous',False):d=(d+w.track.length/2)%w.track.length-w.track.length/2
        if abs(d)>150:continue
        xy=w.state[j,:2]-own[:2]
        lateral=-s*xy[0]+c*xy[1]
        # Reject physically separate branches and choose roles deterministically.
        if np.linalg.norm(xy)>150:continue
        nearby.append((j,float(d),float(lateral)))
    front=sorted((r for r in nearby if r[1]>w.vehicle.length),key=lambda r:r[1])
    rear=sorted((r for r in nearby if r[1]<-w.vehicle.length),key=lambda r:-r[1])
    side=sorted((r for r in nearby if abs(r[1])<=w.vehicle.length),key=lambda r:abs(r[2]))
    for k,rows in enumerate((front,rear,side)):
        if not rows:continue
        j,d,lat=rows[0];other=w.state[j]
        rel_vx=other[3]*np.cos(other[2]-own[2])-own[3]
        rel_vy=other[3]*np.sin(other[2]-own[2])-own[4]
        extra[6+5*k:11+5*k]=[d/150,lat/20,rel_vx/30,rel_vy/15,1]
    extra[-1]=w.surface.grip*w.condition.grip_factor*w.tire.grip_factor
    result=np.r_[obs,extra]
    if not np.isfinite(result).all():raise ValueError('Sensori residuali non finiti')
    return np.clip(result,-10,10)


def controls(world,actions,indices=None):
    from game_control import racing_actions
    rows=np.arange(world.count) if indices is None else np.atleast_1d(indices)
    actions=np.atleast_2d(actions)
    if actions.shape!=(len(rows),2) or not np.isfinite(actions).all():
        raise ValueError('Correzione del pilota non valida')
    actions=np.clip(actions,-1,1)
    if not hasattr(world,'residual_previous'):world.residual_previous=np.zeros((world.count,2))
    world.residual_previous[rows]=actions
    if not hasattr(world,'residual_rules'):world.residual_rules={}
    for i,action in zip(rows,actions):
        state=world.residual_rules.setdefault(int(i),dict(armed=False,moveDirection=0,anchor=0.,weaves=0))
        gaps=world.progress-world.progress[i]
        if getattr(world,'continuous',False):gaps=(gaps+world.track.length/2)%world.track.length-world.track.length/2
        threatened=bool(np.any((gaps<-world.vehicle.length)&(gaps>-45)&(world.state[:,3]>world.state[i,3]+.1)&world.active))
        margin=max(0.,world.track.width/2-world.vehicle.width/2-.9)
        base=float(getattr(world,'racing_base_lane',world.racing_lane)[i]);fraction=float(action[0])
        target=base+fraction*(margin-base if fraction>=0 else margin+base)
        state['requestedLine']=target
        if not threatened:state.update(armed=False,moveDirection=0,anchor=target)
        elif not state['armed']:state.update(armed=True,moveDirection=0,anchor=target)
        elif abs(target-state['anchor'])>.8:
            direction=1 if target>state['anchor'] else -1
            if state['moveDirection'] and direction!=state['moveDirection']:state['weaves']+=1
            state.update(moveDirection=direction,anchor=target)
    return racing_actions(world,rows,line_fraction=actions[:,0],pace_delta=actions[:,1]*SCALES[1])


class RacingPolicy:
    def __init__(self,data):
        from game_learning import parameters
        if data.get('base')!=BASE or data.get('action')!=ACTION or data.get('recipe',{}).get('features')!=FEATURES:
            raise ValueError('Contratto del pilota residuale incompatibile')
        if data['algorithm'] not in METHODS or data['recipe'].get('scales')!=SCALES.tolist() or data['recipe'].get('decisionHz')!=10 or data['recipe'].get('lineMap')!='base-to-full-corridor-v1':raise ValueError('Ricetta del pilota incompatibile')
        if data['algorithm']=='race_master' and data['weights'] is not None:raise ValueError('Il Maestro non usa pesi neurali')
        self.data=deepcopy(data);self.key=key(data);self.hidden=data['hidden']
        self.weights=None if data['weights'] is None else np.asarray(data['weights'],dtype=float)
        if self.weights is not None and (self.weights.shape!=(parameters(90,self.hidden),) or not np.isfinite(self.weights).all()):
            raise ValueError('Pesi residuali non validi')
        if self.weights is None and data['algorithm']!='race_master':raise ValueError('Rete del pilota assente')

    def commands(self,world,index=None):
        from game_learning import forward
        rows=np.arange(world.count) if index is None else np.atleast_1d(index)
        cache=getattr(world,'residual_cache',{})
        commands=[]
        tick=int(round(world.time*60))
        for i in rows:
            old=cache.get(int(i))
            if old is None or old['key']!=self.key or tick<old['tick'] or tick-old['tick']>=DECISION_STEPS:
                action=np.zeros(2) if self.weights is None else np.tanh(forward(self.weights,features(world,i),self.hidden))
                old=dict(key=self.key,tick=tick,action=action.tolist());cache[int(i)]=old
            commands.append(old['action'])
        world.residual_cache=cache
        return np.asarray(commands),rows

    def act(self,world,index=None):
        commands,rows=self.commands(world,index)
        out=controls(world,commands,rows)
        return out[0] if index is not None else out


def initial_weights(profile):
    if profile.get('controlMode')=='direct':
        from game_direct_bootstrap import initial_weights as prepared
        return prepared(profile)
    from game_learning import random_weights
    weights=random_weights(np.random.default_rng(profile['seed']),profile['hidden'],inputs=90)
    weights[(90+1)*profile['hidden']:]=0
    return weights
