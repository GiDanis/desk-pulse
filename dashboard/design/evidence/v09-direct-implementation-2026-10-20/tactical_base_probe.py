from pathlib import Path
import json
import numpy as np
from game_direct_bootstrap import direct_profile,base_asset
from game_direct import snapshot
from game_learning import Policy
from game_residual import profile,snapshot as legacy
from game_control import frozen_actions
from game_catalog import RACE_PHYSICS_VERSION
from game_simulation import World
r=Path(__file__).resolve().parent;a=base_asset()['policy']['weights'];out=[]
for variant in ('base-v2-before-grid','rejected-grid-base'):
 b=json.loads((r/(variant+'.json')).read_text())['policy']['weights']
 for seed in (811001,811002):
  rng=np.random.default_rng(seed);w=World(5,seed,shared=True,laps=3,physics=RACE_PHYSICS_VERSION,telemetry=True);w.native_sensors=True;w.race_lap_target=True
  for i in range(5):w.perturb(i,float(rng.uniform(-.05,.05)),float(rng.uniform(-.005,.005)))
  controllers=[Policy(snapshot(direct_profile(i+2,'residual_ppo'),a)) for i in range(3)]+[Policy(snapshot(direct_profile(5,'residual_tactic'),b)),Policy(legacy(profile(1,'race_master')))];seen=set()
  while w.active.any() and w.time<160:
   w.step(frozen_actions(w,controllers),return_observations=False)
   for e in w.events:
    if e.get('type')=='contact':seen.add((e['time'],tuple(e['cars'])))
  row=dict(variant=variant,seed=seed,finished=int(np.isfinite(w.finish).sum()),retired=w.retired.tolist(),limits=w.track_limits.tolist(),contacts=len(seen),rows=w.rows());out.append(row)
  print(variant,seed,row['finished'],row['retired'],row['limits'],row['contacts'],flush=True)
(r/'tactical-base-probe.json').write_text(json.dumps(out,indent=2)+'\n')
