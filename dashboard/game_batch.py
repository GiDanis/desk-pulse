"""Batch the unchanged float64 integrator for compatible independent worlds.

Worlds are grouped by exact clock, physics/configuration and adaptive substeps.
Traffic worlds retain their own collision domain and use the ordinary path.
Results are applied in episode order; this module never evaluates a policy.
"""
from collections import OrderedDict
from copy import deepcopy
import math
import numpy as np
from game_simulation import World,DT
from game_catalog import ACADEMY_OBSERVATION_VERSION

ARRAYS=('state','active','retired','retirement_cause','finish','progress','previous_phase','checkpoint',
        'episode_time','acceleration','training_context','racing_lane','track_limits',
        'offroad_seconds','was_offroad','progress_credit','credit_age','progress_origin','gate_origin','gate_base','lap_invalid','clean_laps','lap_count','safe_frontier','safe_distance')
TELEMETRY=('lap_started','max_speed','lap_contacted','lap_limits')


class BatchPhysics:
    def __init__(self):self.worlds=OrderedDict()

    def prepare(self,episodes,actions,smooth=False):
        groups={};results=[None]*len(episodes)
        for i,e in enumerate(episodes):
            w=e.world
            if e.reason or w.shared or w.count!=1 or not e.reward_spec:continue
            samples=max(w.substeps,int(np.ceil(float(np.hypot(w.state[:,3],w.state[:,4]).max())*DT/.25)),
                        int(np.ceil(float(abs(w.state[:,5]).max())*DT/.025)))
            pace=0. if e.phase in ('launch','control','bend','straight') else 1.
            contract=(w.track.id,w.physics,w.substeps,w.laps,w.vehicle,w.surface,w.condition,w.tire,
                      w.continuous,w.telemetry,w.native_sensors,samples,pace)
            groups.setdefault((contract,w.time),[]).append(i)
        for (contract,clock),indices in groups.items():
            if len(indices)<2:continue
            first=episodes[indices[0]].world
            key=(contract,len(indices))
            if key not in self.worlds:
                self.worlds[key]=World(len(indices),0,shared=False,laps=first.laps,substeps=first.substeps,
                    vehicle=first.vehicle,surface=first.surface,condition=first.condition,tire=first.tire,
                    track_id=first.track.id,physics=first.physics,telemetry=first.telemetry,lazy_sensors=True)
                while len(self.worlds)>16:self.worlds.popitem(last=False)
            grouped=self.worlds[key];self.worlds.move_to_end(key)
            grouped.native_sensors=first.native_sensors;grouped.continuous=first.continuous
            grouped.time=clock;grouped.events=[];grouped.contact_times={}
            grouped.training_phase=first.training_phase
            for name in ARRAYS+(TELEMETRY if first.telemetry else ()):
                value=getattr(grouped,name,None)
                if value is None:continue
                for row,i in enumerate(indices):value[row]=getattr(episodes[i].world,name)[0]
            if not first.track.oval:
                grouped._segments=np.array([int(e.world._segments[0]) for e in (episodes[i] for i in indices)])
            grouped._observed_cache=None;grouped._coordinate_cache=None
            if first.telemetry:grouped.lap_times=[list(episodes[i].world.lap_times[0]) for i in indices]
            _,reward,_=grouped.step(np.asarray(actions)[indices],pace=contract[-1],return_observations=False,
                                    control_cost=.03 if smooth else 0.)
            observed=grouped.observations(version=ACADEMY_OBSERVATION_VERSION)
            coordinates=grouped.coordinates()
            for row,i in enumerate(indices):
                packet={name:getattr(grouped,name)[row:row+1].copy() for name in ARRAYS+(TELEMETRY if first.telemetry else ()) if hasattr(grouped,name)}
                if not first.track.oval:packet['_segments']=grouped._segments[row:row+1].copy()
                events=[]
                for event in grouped.events:
                    if row in event.get('cars',[]):events.append({**event,'cars':[0]})
                results[i]=dict(world=packet,time=grouped.time,events=events,
                    lapTimes=list(grouped.lap_times[row]) if first.telemetry else None,
                    observations=observed[row].copy(),coordinates=[x[row:row+1].copy() for x in coordinates],
                    reward=float(reward[row]),terms={k:float(v[row]) for k,v in grouped.reward_terms.items()})
        return results


def apply(world,result):
    for name,value in result['world'].items():
        current=getattr(world,name,None)
        new=np.asarray(value,dtype=current.dtype if isinstance(current,np.ndarray) else None)
        if isinstance(current,np.ndarray) and current.shape==new.shape:np.copyto(current,new)
        else:setattr(world,name,new.copy())
    world.time=result['time'];world.events.extend(deepcopy(result['events']))
    if result['lapTimes'] is not None:world.lap_times=[deepcopy(result['lapTimes'])]
    world.reward_terms={k:np.array([v]) for k,v in result['terms'].items()}
    world.reward=np.array([result['reward']])
    key=(world.state[:,:2].tobytes(),getattr(world,'_segments',np.empty(0)).tobytes())
    world._coordinate_cache=(key,tuple(np.asarray(x).copy() for x in result['coordinates']))
    world._observed_cache=None


def durable_results(results):
    if results is None:return None
    from game_numeric import checkpoint_value
    output=[]
    for result in results:
        if result is None:output.append(None);continue
        row=deepcopy(result)
        row['world']['finish']=[float(x) if x is not None and np.isfinite(x) else None for x in row['world']['finish']]
        output.append(checkpoint_value(row))
    return output
