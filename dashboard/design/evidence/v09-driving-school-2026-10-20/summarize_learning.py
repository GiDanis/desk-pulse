from pathlib import Path
import json,time,statistics
import numpy as np
from game_learning import Policy
from game_school_lessons import Lesson,SKILLS
from game_academy import Episode
from game_direct_bootstrap import direct_profile
from game_rewards import specification
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_control import frozen_actions
from game_residual import profile,snapshot as legacy
p=Path(__file__).parent;methods=('residual_ppo','residual_sac','residual_td3','residual_tactic');rows=[];products={}
for mi,method in enumerate(methods):
 for seed in (mi+2,31,32,33,34):
  f=p/f'mixture-final-{method}-{seed}.json';deadline=time.monotonic()+1000
  while not f.exists():
   assert time.monotonic()<deadline,f
   time.sleep(3)
  d=json.loads(f.read_text());policy=d['champion'];driver=Policy(policy);skills=[]
  for si,skill in enumerate(SKILLS):
   e=Lesson('oval-1',skill,977001+si)
   while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
   skills.append(dict(skill=skill,seed=e.seed,reason=e.reason,contacts=e.contact_count,limits=int(e.world.track_limits[0]),measurements=e.lesson))
  traffic=[]
  if method=='residual_tactic':
   for phase in ('overtake','corner','defend'):
    for n in (978001,978002,978003):
     e=Episode('oval-1',phase,n,protocol='driving-memory-1',single_lap=True,reward_spec=specification(direct_profile(seed,method)),pace_pressure=1.)
     while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
     traffic.append(dict(phase=phase,seed=n,reason=e.reason,passes=e.passes,contacts=e.contact_count,limits=int(e.world.track_limits[0])))
  initial=statistics.median(r['seconds'] for r in d['results']['initial']);champion=statistics.median(r['seconds'] for r in d['results']['champion'])
  valid=all(r['reason']=='success' and not r['contacts'] and not r['limits'] for r in d['results']['champion'])
  rows.append(dict(method=method,seed=seed,physicalSteps=d['physicalSteps'],initial=initial,champion=champion,improvementPercent=(1-champion/initial)*100,soloValid=valid,skills=skills,traffic=traffic,updates=d['updates']))
  if seed==mi+2:products[method]=policy
  print(method,seed,round(initial,3),round(champion,3),[r['reason'] for r in skills],flush=True)
races=[]
for slot,n in enumerate(range(979001,979006)):
 w=World(5,n,shared=True,laps=3,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True);w.native_sensors=True;w.race_lap_target=True
 policies=[Policy(products[m]) for m in methods[:3]]+[Policy(legacy(profile(1,'race_master')))];policies.insert(slot,Policy(products['residual_tactic']));contacts=set()
 rng=np.random.default_rng(n)
 for i in range(5):w.perturb(i,float(rng.uniform(-.08,.08)),float(rng.uniform(-.005,.005)))
 while w.active.any() and w.time<160:
  w.step(frozen_actions(w,policies),return_observations=False)
  for e in w.events:
   if e.get('type')=='contact':contacts.add((e['time'],tuple(e['cars'])))
 races.append(dict(seed=n,tacticGridSlot=slot,finished=int(np.isfinite(w.finish).sum()),limits=w.track_limits.tolist(),contacts=len(contacts),rows=w.rows()));print('learned race',n,races[-1]['finished'],flush=True)
passed=all(r['soloValid'] and all(x['reason']=='success' for x in r['skills']+r['traffic']) for r in rows) and all(r['finished']==5 for r in races)
summary=[]
for m in methods:
 group=[r for r in rows if r['method']==m];summary.append(dict(method=m,seeds=len(group),improved=sum(r['champion']<r['initial']*.999 for r in group),initialMedian=statistics.median(r['initial'] for r in group),championMedian=statistics.median(r['champion'] for r in group)))
(p/'final-summary.json').write_text(json.dumps(dict(status='passed' if passed else 'failed',rows=rows,methods=summary,learnedRaces=races,teacherOverridesEgo=0,teacherLabelsInRL=0,preparedAssetQualification='mixture-qualification-final.json',scope='Oval-1, standard car, held-out seeds; no universal convergence or traffic optimality claim'),indent=2)+'\n')
print(json.dumps(summary),flush=True)
