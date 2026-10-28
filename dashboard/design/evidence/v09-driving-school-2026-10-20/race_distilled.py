from pathlib import Path
import json,sys
import numpy as np
from game_simulation import World
from game_learning import Policy
from game_catalog import RACE_PHYSICS_VERSION
from game_control import frozen_actions
from game_residual import profile,snapshot
r=Path(__file__).parent;out=[]
for label,an,bn in [('distilled-128','distilled-driving.json','distilled-traffic.json')]:
 a=json.loads((r/an).read_text())['policy'];b=json.loads((r/bn).read_text())['policy']
 for seed in (968001,968002,968003):
  w=World(5,seed,shared=True,laps=3,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True);w.native_sensors=True;w.race_lap_target=True
  policies=[Policy(b)]+[Policy(a) for _ in range(3)]+[Policy(snapshot(profile(1,'race_master')))];contacts=set()
  while w.active.any() and w.time<170:
   w.step(frozen_actions(w,policies),return_observations=False)
   for e in w.events:
    if e.get('type')=='contact':contacts.add((e['time'],tuple(e['cars'])))
  row=dict(label=label,seed=seed,finished=int(np.isfinite(w.finish).sum()),limits=w.track_limits.tolist(),retired=w.retired.tolist(),contacts=len(contacts),rows=w.rows());out.append(row);print(label,row['finished'],row['limits'],row['contacts'],flush=True)
(r/'race-distilled-results.json').write_text(json.dumps(out,indent=2)+'\n')
