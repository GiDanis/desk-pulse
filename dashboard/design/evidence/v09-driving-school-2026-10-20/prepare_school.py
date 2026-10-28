from pathlib import Path
import argparse,json,time
from functools import partial
import numpy as np
from game_direct_bootstrap import direct_profile,random_examples,fit,rollout,physical_context
from game_direct import snapshot
from game_learning import random_weights
from game_driving_school import actions
p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=76001);p.add_argument('--traffic',action='store_true');p.add_argument('--following',action='store_true');p.add_argument('--rounds',type=int,default=6);p.add_argument('--utilization',type=float,default=.65);p.add_argument('--output',required=True);a=p.parse_args()
teacher=partial(actions,lane=0.,apex=3.,utilization=a.utilization,follow=a.following);start=time.monotonic();rng=np.random.default_rng(a.seed)
x,y=random_examples(a.seed+100,count=16384,teacher_fn=teacher)
for j,phase in enumerate((('pace','bend','recovery','follow','grid','race4') if a.following else ('pace','bend','recovery','overtake','corner','defend','grid','race4')) if a.traffic else ('pace','bend','recovery')):
 for k in range(2):
  result,xx,yy=rollout(None,a.seed+200+j*10+k,phase,teacher=True,teacher_fn=teacher)
  x=np.r_[x,xx];y=np.r_[y,yy]
weights=random_weights(rng,64,inputs=90);optimizer,error=fit(weights,x,y,rng,9000);trace=[]
for r in range(a.rounds):
 results=[]
 for j in range(5):
  phase=((('pace','bend','recovery','follow','grid','race4') if a.following else ('pace','bend','recovery','overtake','corner','defend','grid','race4'))[((r*5+j)%(6 if a.following else 8))] if a.traffic else ('pace','pace','bend','recovery','pace')[j])
  result,xx,yy=rollout(weights,a.seed+300+r*10+j,phase,collect=True,teacher_fn=teacher,context=physical_context(rng,j%2==1))
  results.append(result);x=np.r_[x,xx];y=np.r_[y,yy]
 optimizer,error=fit(weights,x,y,rng,3500,optimizer)
 trace.append(dict(round=r,mse=error.tolist(),results=results,samples=len(x)));print(json.dumps(dict(round=r,mse=error.tolist(),outcomes=[(z['phase'],z['reason'],round(z['seconds'],2)) for z in results])),flush=True)
policy=snapshot(direct_profile(a.seed,'residual_tactic' if a.traffic else 'residual_ppo'),weights,dict(kind='driving-school-preparation',version='driving-school-1',seed=a.seed))
Path(a.output).write_text(json.dumps(dict(policy=policy,trace=trace,seed=a.seed,traffic=a.traffic,samples=len(x),teacher=dict(lane=0.,apex=3.,utilization=a.utilization),seconds=time.monotonic()-start),indent=2)+'\n')
