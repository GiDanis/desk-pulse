from pathlib import Path
import json
import numpy as np
from game_direct_bootstrap import direct_profile
from game_direct import snapshot
from game_learning import Policy
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_control import frozen_actions
r=Path(__file__).resolve().parent;out=[]
for name in ('rejected-base-first','base-v2-before-grid','product-base-candidate'):
 data=json.loads((r/(name+'.json')).read_text());weights=data['policy']['weights']
 for count in (2,5):
  w=World(count,79001,shared=True,laps=3,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True);w.native_sensors=True;w.race_lap_target=True
  seen=set();policies=[Policy(snapshot(direct_profile(i+1,'residual_ppo'),weights)) for i in range(count)];contacts=0
  while w.active.any() and w.time<150:
   w.step(frozen_actions(w,policies),return_observations=False)
   for event in w.events:
    if event.get('type')=='contact':seen.add((event['time'],tuple(event['cars'])))
   contacts=len(seen)
  row=dict(name=name,count=count,seconds=w.time,laps=w.lap_count.tolist(),clean=w.clean_laps.tolist(),retired=w.retired.tolist(),limits=w.track_limits.tolist(),contacts=contacts,finish=[float(x) if np.isfinite(x) else None for x in w.finish])
  out.append(row);print(json.dumps(row),flush=True)
(r/'base-race-selection.json').write_text(json.dumps(out,indent=2)+'\n')
