"""Frozen measured flying laps; these are private simulations, not installed certificates."""
from pathlib import Path
import json,time,statistics,sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from game_residual import profile,snapshot
from game_learning import Policy
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
root=Path(__file__).resolve().parent;rows=[]
for method in ('race_master','residual_ppo','residual_sac','residual_td3'):
 p=profile(11,method)
 source=None if method=='race_master' else root/f'v2-{method}-11.json'
 data=snapshot(p) if source is None else snapshot(p,json.loads(source.read_text())['champion']['weights'])
 policy=Policy(data);world=World(1,84001,laps=4,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True)
 start=time.monotonic()
 while world.active.any() and world.time<240:
  world.step(policy.act(None,world=world),return_observations=False)
 flying=[lap['time'] for lap in world.lap_times[0] if lap['clean'] and not lap['standingStart']]
 assert len(flying)==3 and not world.retired[0],world.rows()
 rows.append(dict(method=method,source=str(source) if source else 'neutral-base',standing=world.lap_times[0][0],flying=flying,median=statistics.median(flying),maxSpeedKmh=float(world.max_speed[0]*3.6),seconds=time.monotonic()-start))
base=rows[0]['median']
for row in rows:row['gain']=1-row['median']/base
(root/'frozen-flying-laps.json').write_text(json.dumps(dict(status='passed',track='oval-1',width=12,seed=84001,results=rows),indent=2)+'\n');print(json.dumps(rows))
