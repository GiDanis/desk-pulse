import json,hashlib
from pathlib import Path
import numpy as np
from game_direct_bootstrap import rollout,physical_context,direct_profile
from game_direct import snapshot
from game_learning import Policy
from game_simulation import World
from game_control import frozen_actions
from game_catalog import RACE_PHYSICS_VERSION
r=Path(__file__).resolve().parent;data=json.loads((r/'product-base-candidate.json').read_text());weights=data['policy']['weights'];rng=np.random.default_rng(76000)
rows=[]
for phase in ('pace','overtake','corner','defend','recovery'):
 for j in range(5):
  ctx=physical_context(rng,True) if phase=='pace' and j%2 else None
  result,_,_=rollout(weights,76001+j+100*('pace','overtake','corner','defend','recovery').index(phase),phase,context=ctx)
  rows.append(result)
series=[]
for count in (1,2,5):
 w=World(count,76901,shared=count>1,laps=3,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True);w.native_sensors=True
 policies=[Policy(snapshot(direct_profile(i+1,'residual_ppo'),weights)) for i in range(count)]
 while w.active.any() and w.time<160:w.step(frozen_actions(w,policies),return_observations=False)
 series.append(dict(count=count,seconds=w.time,laps=w.lap_count.tolist(),clean=w.clean_laps.tolist(),retired=w.retired.tolist(),limits=w.track_limits.tolist(),finish=[float(x) if np.isfinite(x) else None for x in w.finish]))
report=dict(rows=rows,series=series,scope='Frozen neural base, no bot ego control or learning; physical variations and traffic held out from preparation')
(r/'product-base-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
