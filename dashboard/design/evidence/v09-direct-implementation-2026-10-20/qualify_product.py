from pathlib import Path
from copy import deepcopy
import json
import numpy as np
from game_direct_bootstrap import base_asset,rollout,physical_context,direct_profile
from game_direct import snapshot
from game_learning import Policy
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_control import frozen_actions
from game_residual import profile,snapshot as legacy_snapshot
r=Path(__file__).resolve().parent;asset=base_asset();weights=asset['policy']['weights'];rng=np.random.default_rng(800000);rows=[];races=[]
for j in range(15):
 phase='recovery' if j>=10 else 'pace';context=physical_context(rng,True) if 5<=j<10 else None
 result,_,_=rollout(weights,800001+j,phase,context=context);rows.append(result)
for count in (2,5):
 for seed in (801001,801002,801003):
  w=World(count,seed,shared=True,laps=3,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True);w.native_sensors=True;w.race_lap_target=True
  for i in range(count):w.perturb(i,float(rng.uniform(-.10,.10)),float(rng.uniform(-.008,.008)))
  # Match the shipping roster: fastest neural qualifiers before Maestro.
  policies=[Policy(snapshot(direct_profile(i+1,'residual_ppo'),weights)) for i in range(count-1)]+[Policy(legacy_snapshot(profile(1,'race_master')))]
  seen=set()
  while w.active.any() and w.time<160:
   w.step(frozen_actions(w,policies),return_observations=False)
   for e in w.events:
    if e.get('type')=='contact':seen.add((e['time'],tuple(e['cars'])))
  row=dict(seed=seed,count=count,seconds=w.time,rows=w.rows(),contacts=len(seen),limits=w.track_limits.tolist(),retired=w.retired.tolist(),finished=int(np.isfinite(w.finish).sum()))
  races.append(row);print('Race',count,seed,row['finished'],row['contacts'],row['limits'],flush=True)
result=dict(status='passed' if all(x['valid'] for x in rows) and all(x['finished']==x['count'] for x in races) else 'failed',policyHash=asset['policyHash'],rows=rows,races=races,scope='Initial standard driving, limited physical variation and short mixed races. Not autonomous expert overtaking/generalization.')
(r/'product-qualification-final.json').write_text(json.dumps(result,indent=2)+'\n');print('Qualification',result['status'],flush=True)
