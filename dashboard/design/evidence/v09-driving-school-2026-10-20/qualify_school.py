from pathlib import Path
import json
from functools import partial
import numpy as np
from game_direct_bootstrap import rollout,direct_profile
from game_learning import Policy
from game_school_lessons import Lesson,SKILLS
from game_academy import Episode
from game_driving_school import actions
r=Path(__file__).parent;d=json.loads((r/'school-candidate.json').read_text());driver=Policy(d['policy']);rows=[]
for skill in SKILLS:
 for seed in (951001,951002,951003):
  e=Lesson('oval-1',skill,seed)
  while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
  row=e.result();rows.append(row);print(skill,seed,e.reason,round(e.age,3),e.lesson,flush=True)
for seed in (952001,952002,952003,952004,952005):
 e=Episode('oval-1','pace',seed,protocol='driving-memory-1',objective='impara_infinito',reward_spec={'version':'direct-driving-2','progressPerLap':1.,'timeControl':1.,'timePace':1.,'cleanLap':0.,'exit':.5,'outside':2.,'retirement':3.,'understeer':1.,'stall':3.,'passReward':.5,'smooth':.1,'referenceSpeed':9.},pace_pressure=1.)
 while not e.reason and e.world.clean_laps[0]<3:
  e.step(driver.act(None,world=e.world,index=0),return_observation=False)
  if e.reason=='window':e.next_window()
 row=dict(seed=seed,threeLaps=int(e.world.clean_laps[0]),limits=int(e.world.track_limits[0]),contacts=e.contact_count,seconds=e.age);rows.append(row);print('series',row,flush=True)
(r/'school-development.json').write_text(json.dumps(rows,indent=2)+'\n')
