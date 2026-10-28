from pathlib import Path
import json
import numpy as np
from game_direct_bootstrap import initial_policy,direct_profile
from game_learning import Policy
from game_residual import profile,snapshot
from game_control import frozen_actions
from game_catalog import RACE_PHYSICS_VERSION
from game_simulation import World
out=[]
for slot in range(5):
 brains=[Policy(initial_policy(direct_profile(i+2,'residual_ppo'))) for i in range(3)]+[Policy(snapshot(profile(1,'race_master')))]
 brains.insert(slot,Policy(initial_policy(direct_profile(5,'residual_tactic'))))
 w=World(5,812000+slot,shared=True,laps=3,physics=RACE_PHYSICS_VERSION,telemetry=True);w.native_sensors=True;w.race_lap_target=True
 while w.active.any() and w.time<160:w.step(frozen_actions(w,brains),return_observations=False)
 row=dict(slot=slot,finished=int(np.isfinite(w.finish).sum()),limits=w.track_limits.tolist(),retired=w.retired.tolist(),rows=w.rows());out.append(row)
 print(slot,row['finished'],row['limits'],row['retired'],flush=True)
Path(__file__).with_name('tactical-grid-slots.json').write_text(json.dumps(out,indent=2)+'\n')
