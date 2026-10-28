from pathlib import Path
from copy import deepcopy
import json
import numpy as np
from game_learning import Policy
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_control import frozen_actions
from game_residual import profile,snapshot
r=Path(__file__).parent;a=json.loads((r/'school-policy.json').read_text());original=json.loads((r/'traffic-policy.json').read_text());out=[]
for bias in (-.10,-.20,-.30):
 b=deepcopy(original);b['weights'][-1]+=bias
 for slot in (0,2,4):
  seed=967001+slot;w=World(5,seed,shared=True,laps=3,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True);w.native_sensors=True;w.race_lap_target=True
  pol=[Policy(a) for _ in range(3)]+[Policy(snapshot(profile(1,'race_master')))];pol.insert(slot,Policy(b));rng=np.random.default_rng(seed)
  for i in range(5):w.perturb(i,float(rng.uniform(-.08,.08)),float(rng.uniform(-.005,.005)))
  seen=set()
  while w.active.any() and w.time<170:
   w.step(frozen_actions(w,pol),return_observations=False)
   for e in w.events:
    if e.get('type')=='contact':seen.add((e['time'],tuple(e['cars'])))
  row=dict(bias=bias,slot=slot,finished=int(np.isfinite(w.finish).sum()),limits=w.track_limits.tolist(),contacts=len(seen),retired=w.retired.tolist());out.append(row);print(row,flush=True)
 (r/('traffic-calibrated-'+str(bias)+'.json')).write_text(json.dumps(dict(policy=b,calibration=dict(pedalLogitBias=bias,scope='Offline actor calibration, no runtime action adjustment')),indent=2)+'\n')
(r/'calibration-races.json').write_text(json.dumps(out,indent=2)+'\n')
