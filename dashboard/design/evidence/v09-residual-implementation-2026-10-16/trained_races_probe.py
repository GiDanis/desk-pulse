from pathlib import Path
import json,time
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_learning import Policy
from game_residual import snapshot,profile
from game_control import frozen_actions
r=Path(__file__).resolve().parent;rows=[]
policies=[Policy(snapshot(profile(1,'race_master')))]+[Policy(json.loads((r/f'v2-{m}-11.json').read_text())['champion']) for m in ('residual_ppo','residual_sac','residual_td3')]+[Policy(json.loads((r/'accepted-tactic-11.json').read_text())['champion'])]
for laps in (3,5):
 w=World(5,8,shared=True,laps=laps,physics=RACE_PHYSICS_VERSION,telemetry=True);w.race_lap_target=True;start=time.monotonic()
 first=None
 while w.active.any() and w.time<300:
  w.step(frozen_actions(w,policies),return_observations=False)
  if first is None and any(__import__('numpy').isfinite(w.finish)):first=w.time
 rows.append(dict(laps=laps,results=w.rows(),events=w.events,seconds=time.monotonic()-start,firstFinish=first,lastTime=w.time,active=w.active.tolist()))
(r/'trained-five-car-races.json').write_text(json.dumps(dict(status='executed',scope='Private trained policies, actual contacts retained, all cars remain represented; full-distance physics, not Worker finish-window certification.',cases=rows),indent=2)+'\n')
print([(x['laps'],[(v['status'],v['lap']) for v in x['results']]) for x in rows])
