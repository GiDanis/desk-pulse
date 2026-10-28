from pathlib import Path
import json,itertools
import numpy as np
from game_academy import Episode
from game_direct_bootstrap import direct_profile
from game_rewards import specification
from game_driving_school import actions,plan
rows=[]
for utilization,lane,apex in itertools.product((.65,.70,.75),(-1.5,0.,1.5),(0.,3.)):
 e=Episode('oval-1','pace',141001,protocol='driving-memory-1',single_lap=True,reward_spec=specification(direct_profile(2,'residual_ppo')),pace_pressure=1.)
 gas=brake=0;vmax=0.;command=None
 while not e.reason:
  if round(e.world.time*60)%6==0:command=actions(e.world,[0],lane,apex,utilization)[0]
  e.step(command,return_observation=False);gas+=command[1]>.95;brake+=command[1]<-.1;vmax=max(vmax,e.world.state[0,3]*3.6)
 row=dict(utilization=utilization,lane=lane,apex=apex,seconds=e.age,reason=e.reason,limits=int(e.world.track_limits[0]),gas=int(gas),brake=int(brake),vmax=float(vmax),estimate=plan(e.world,lane,apex,utilization)['estimatedSeconds']);rows.append(row);print(row,flush=True)
Path(__file__).with_name('teacher-probe.json').write_text(json.dumps(rows,indent=2)+'\n')
