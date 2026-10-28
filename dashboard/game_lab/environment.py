"""Gymnasium adapter over the SAME Episode/World used by the kiosk worker."""
from copy import deepcopy
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from game_academy import Episode
from game_direct import features,controls,FEATURES
from game_direct_bootstrap import direct_profile
from game_rewards import specification

VERSION='smartpc-direct-env-1'
TICKS=6


def make_episode(seed,*,family='traffic',bots=1,duration=60.,track='oval-1',profile=None,single_lap=False):
    profile=profile or direct_profile(seed,'residual_td3')
    if family in ('mixed','racecraft'):
        import numpy as np
        rng=np.random.default_rng(seed)
        choices=('traffic','attack','complete','corner','defend') if family=='racecraft' else ('solo','traffic','attack','complete','corner','defend','recover')
        family=choices[int(rng.integers(len(choices)))]
        bots=int(rng.integers(1,4))
    if family in ('attack','complete','corner','defend','recover'):
        from game_overtaking import scenario
        e=scenario(track,family,seed,profile)
        # Bounded drills are useful for collecting approach states. They must
        # not silently end at the first pass in the sustained evaluation bank.
        e.attack_training=False
    else:
        e=Episode(track,'pace' if family=='solo' else 'overtake',seed,
            protocol='driving-memory-1',objective='impara_infinito' if family=='solo' else 'impara_sorpasso',
            bots=bots,reward_spec=specification(profile))
    e.spec.update(distance=e.world.track.length if single_lap else None,continuous=not single_lap,limitSeconds=float(duration))
    e.world.continuous=not single_lap
    return e


class RacingEnv(gym.Env):
    metadata={'render_modes':[]}

    def __init__(self,*,family='traffic',bots=1,duration=60.,track='oval-1',history=1,profile=None,feature_version=FEATURES,single_lap=False):
        super().__init__()
        if type(history) is not int or not 1<=history<=16:raise ValueError('History length')
        self.options=dict(family=family,bots=bots,duration=duration,track=track)
        if single_lap:self.options['single_lap']=True
        self.profile=deepcopy(profile);self.history=history;self.feature_version=feature_version
        self.action_space=spaces.Box(-1.,1.,shape=(2,),dtype=np.float32)
        self.observation_space=spaces.Box(-10.,10.,shape=(90*history,),dtype=np.float32)
        self.episode=None;self.frames=[];self.physics_steps=0;self.decisions=0
        self.total_physics_steps=0;self.total_decisions=0
        self.finished=True

    def observe(self):
        return np.concatenate(self.frames).astype(np.float32)

    def reset(self,*,seed=None,options=None):
        super().reset(seed=seed)
        opts={**self.options,**(options or {})}
        episode_seed=int(seed) if seed is not None else int(self.np_random.integers(0,2**31-1))
        self.episode=make_episode(episode_seed,profile=self.profile,**opts)
        x=features(self.episode.world,version=self.feature_version)
        self.frames=[x.copy() for _ in range(self.history)]
        self.physics_steps=self.decisions=0;self.finished=False
        return self.observe(),self.info()

    def info(self):
        e=self.episode
        return dict(protocol=VERSION,physicsSteps=self.physics_steps,decisions=self.decisions,
            simulatedSeconds=e.age,reason=e.reason,passes=e.passes,contacts=e.contact_count,
            trackLimits=int(e.world.track_limits[0]),teacherAtInference=False,
            result=e.result() if e.reason else None)

    def step(self,action):
        if self.finished:raise RuntimeError('reset required after terminal/truncated transition')
        action=np.asarray(action,dtype=float)
        if action.shape!=(2,) or not np.isfinite(action).all():raise ValueError('Invalid direct action')
        total=0.;e=self.episode
        for _ in range(TICKS):
            applied=controls(e.world,action,[0])[0]
            _,reward,done,_=e.step(applied,return_observation=False)
            total+=reward;self.physics_steps+=1
            self.total_physics_steps+=1
            if done:break
        self.decisions+=1
        self.total_decisions+=1
        self.frames=(self.frames+[features(e.world,version=self.feature_version)])[-self.history:]
        self.finished=bool(e.terminated or e.truncated)
        return self.observe(),float(total),bool(e.terminated),bool(e.truncated),self.info()

    def snapshot(self):
        return dict(version=VERSION,featureVersion=self.feature_version,options=self.options,history=self.history,profile=self.profile,
            episode=self.episode.snapshot(),frames=[f.tolist() for f in self.frames],
            physicsSteps=self.physics_steps,decisions=self.decisions,
            totalPhysicsSteps=self.total_physics_steps,totalDecisions=self.total_decisions,
            rng=deepcopy(self.np_random.bit_generator.state),finished=self.finished)

    def restore(self,data):
        if data['version']!=VERSION or data['history']!=self.history or data['options']!=self.options or data['profile']!=self.profile:
            raise ValueError('Environment checkpoint contract')
        if data.get('featureVersion',FEATURES)!=self.feature_version:raise ValueError('Sensor checkpoint contract')
        saved=data['episode']
        self.episode=Episode(saved['track_id'],saved['phase'],saved['seed'],saved=saved)
        self.frames=[np.asarray(f,dtype=float) for f in data['frames']]
        self.physics_steps=data['physicsSteps'];self.decisions=data['decisions']
        self.total_physics_steps=data.get('totalPhysicsSteps',self.physics_steps);self.total_decisions=data.get('totalDecisions',self.decisions)
        self.np_random.bit_generator.state=deepcopy(data['rng']);self.finished=data['finished']

    def close(self):self.episode=None;self.finished=True
