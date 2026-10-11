import sys,json,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from game_learning import Evolution,Policy
from game_store import default_profile
from game_simulation import World,DT
r=[]
for seed in range(1,6):
 p=default_profile(seed);p['population']=32
 e=Evolution(p);w=World(32,seed);scores=np.zeros(32);start=time.monotonic()
 baseline=None;history=[]
 for generation in range(100):
  w.reset();scores[:]=0
  for step in range(3600):
   _,reward,done=w.step(e.act(w.observations()));scores+=reward
   if done.all():break
  metric=e.update(scores);history.append(metric)
  if baseline is None:baseline=max(scores)
  if generation%10==0:print(seed,generation,metric,flush=True)
  if metric['fitness']>40:break
 evaluation=[]
 for scenario in range(5):
  single=World(1,scenario+1);single.reset(varied=True);policy=Policy(e.policy())
  for step in range(6000):
   single.step(policy.act(single.observations()))
   if not single.active.any():break
  evaluation.append(single.rows()[0])
 record={'seed':seed,'baselineFitness':float(baseline),'history':history,'evaluation':evaluation,'wallSeconds':time.monotonic()-start,'policy':e.policy()}
 r.append(record);Path(__file__).with_name('learning-evolution.json').write_text(json.dumps(r,indent=2))
 print('evaluated',seed,evaluation,flush=True)
