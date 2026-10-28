"""Offline, physically executed references. Never a controller for neural races."""
from pathlib import Path
from copy import deepcopy
import itertools,json,time,statistics
import numpy as np
from game_academy import Episode
from game_direct import controls
from game_direct_bootstrap import direct_profile
from game_driving_school import actions,plan
from game_driving_memory import current_context
from game_rewards import specification

OUT=Path(__file__).parent;started=time.monotonic();rows=[]
def trial(seed,grip,lane,apex,utilization):
    context=deepcopy(current_context('oval-1'));context['condition']['grip_factor']*=grip
    e=Episode('oval-1','pace',seed,protocol='driving-memory-1',single_lap=False,
              reward_spec=specification(direct_profile(2,'residual_ppo')),context=context)
    while not e.reason:
        if e.ticks%6==0:held=actions(e.world,[0],lane,apex,utilization,traffic=False)[0]
        controls(e.world,held,[0]);e.step(held,return_observation=False)
    flying=[r['time'] for r in e.world.lap_times[0][1:] if r['clean']]
    return dict(seed=seed,grip=grip,lane=lane,apex=apex,utilization=utilization,reason=e.reason,
        flyingMedian=statistics.median(flying) if len(flying)==2 and e.reason=='success' and not e.world.track_limits[0] else None,
        seconds=e.age,limits=int(e.world.track_limits[0]),contacts=e.contact_count,
        estimatedSeconds=plan(e.world,lane,apex,utilization)['estimatedSeconds'])
for lane,apex,utilization in itertools.product((-1.,0.,1.),(1.,3.,5.),(.65,.8,.95)):
    r=trial(992001,1.,lane,apex,utilization);rows.append(r)
    print(lane,apex,utilization,r['reason'],r['flyingMedian'],flush=True)
valid=[r for r in rows if r['flyingMedian'] is not None]
winner=min(valid,key=lambda r:r['flyingMedian']);final=[]
for grip in (1.,.85):
    for seed in (993001,993002,993003,993004,993005):
        final.append(trial(seed,grip,winner['lane'],winner['apex'],winner['utilization']))
OUT.joinpath('physical-reference.json').write_text(json.dumps(dict(selection=rows,winner=winner,heldOut=final,
    wallSeconds=time.monotonic()-started,scope='Finite physical search, not a global optimum; offline diagnostic teacher only. No neural model or production state replaced.'),indent=2)+'\n')
