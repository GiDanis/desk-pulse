from pathlib import Path
import json
import numpy as np
from game_learning import Policy
from game_school_lessons import Lesson,SKILLS
from game_academy import Episode
from game_direct_bootstrap import direct_profile
from game_direct import snapshot
from game_rewards import specification
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_control import frozen_actions
from game_residual import profile,snapshot as legacy
r=Path(__file__).parent;rows=[];race=[]
a=json.loads((r/'school-policy.json').read_text());b=json.loads((r/'traffic-policy.json').read_text())
for role,p in [('driving',a),('traffic',b)]:
 driver=Policy(p)
 for skill in SKILLS:
  for seed in (973001,973002,973003):
   e=Lesson('oval-1',skill,seed)
   while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
   rows.append(dict(role=role,kind=skill,seed=seed,reason=e.reason,seconds=e.age,limits=int(e.world.track_limits[0]),contacts=e.contact_count,measurements=e.lesson));print(role,skill,seed,e.reason,flush=True)
 for seed in (974001,974002,974003,974004,974005):
  e=Episode('oval-1','pace',seed,protocol='driving-memory-1',single_lap=True,reward_spec=specification(direct_profile(2,'residual_ppo')),pace_pressure=1.)
  while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
  rows.append(dict(role=role,kind='solo',seed=seed,reason=e.reason,seconds=e.age,limits=int(e.world.track_limits[0]),contacts=e.contact_count));print(role,'solo',seed,e.reason,round(e.age,3),flush=True)
 if role=='traffic':
  for phase in ('overtake','corner','defend'):
   for seed in (975001,975002,975003):
    e=Episode('oval-1',phase,seed,protocol='driving-memory-1',single_lap=True,reward_spec=specification(direct_profile(5,'residual_tactic')),pace_pressure=1.)
    while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
    rows.append(dict(role=role,kind=phase,seed=seed,reason=e.reason,seconds=e.age,limits=int(e.world.track_limits[0]),contacts=e.contact_count,passes=e.passes));print(role,phase,seed,e.reason,flush=True)
for slot,seed in enumerate((976001,976002,976003,976004,976005)):
 w=World(5,seed,shared=True,laps=3,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True);w.native_sensors=True;w.race_lap_target=True
 policies=[Policy(a) for _ in range(3)]+[Policy(legacy(profile(1,'race_master')))];policies.insert(slot,Policy(b));contacts=set()
 rng=np.random.default_rng(seed)
 for i in range(5):w.perturb(i,float(rng.uniform(-.08,.08)),float(rng.uniform(-.005,.005)))
 while w.active.any() and w.time<160:
  w.step(frozen_actions(w,policies),return_observations=False)
  for e in w.events:
   if e.get('type')=='contact':contacts.add((e['time'],tuple(e['cars'])))
 rr=dict(seed=seed,finished=int(np.isfinite(w.finish).sum()),limits=w.track_limits.tolist(),retired=w.retired.tolist(),contacts=len(contacts),rows=w.rows());race.append(rr);print('race',seed,rr['finished'],rr['limits'],rr['contacts'],flush=True)
(r/'mixture-qualification-final.json').write_text(json.dumps(dict(rows=rows,races=race,status='passed' if all(x['reason']=='success' for x in rows) and all(x['finished']==5 for x in race) else 'failed'),indent=2)+'\n')
