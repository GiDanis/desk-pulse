"""Product base preparation, independent of old research checkpoints."""
import argparse,json,time,hashlib
from pathlib import Path
import numpy as np
from game_direct_bootstrap import direct_profile,random_examples,fit,rollout,physical_context
from game_direct import snapshot
from game_learning import random_weights
p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=75001);p.add_argument('--factor',type=float,default=1.35);p.add_argument('--traffic',action='store_true');p.add_argument('--teacher-style',default='passing');p.add_argument('--output',required=True);a=p.parse_args()
start=time.monotonic();rng=np.random.default_rng(a.seed);x,y=random_examples(a.seed+100,count=8192,factor=a.factor)
if a.traffic:
 for j,phase in enumerate(('overtake','defend','corner','grid','race4')*2):
  result,xx,yy=rollout(None,a.seed+200+j,phase,teacher=True,factor=a.factor,teacher_style=a.teacher_style)
  x=np.r_[x,xx];y=np.r_[y,yy]
weights=random_weights(rng,64,inputs=90);optimizer,error=fit(weights,x,y,rng,6000);trace=[]
for r in range(8):
 results=[]
 for j in range(4):
  phase=('pace',('pace' if r%2 else 'recovery'),('overtake','corner','defend')[r%3],('grid' if r%2 else 'race4'))[j] if a.traffic else 'pace'
  result,xx,yy=rollout(weights,a.seed+300+r*10+j,phase,collect=True,factor=a.factor,context=physical_context(rng,j%2==1),teacher_style=a.teacher_style)
  results.append(result);x=np.r_[x,xx];y=np.r_[y,yy]
 optimizer,error=fit(weights,x,y,rng,2500,optimizer)
 trace.append(dict(round=r,mse=error.tolist(),results=results,samples=len(x)))
 print(json.dumps(trace[-1]),flush=True)
policy=snapshot(direct_profile(a.seed,'residual_ppo'),weights,dict(kind='teacher-preparation',trainingSeed=a.seed,factor=a.factor))
result=dict(version='direct-base-1',status='candidate',trainingSeed=a.seed,factor=a.factor,traffic=a.traffic,teacherStyle=a.teacher_style,trace=trace,samples=len(x),wallSeconds=time.monotonic()-start,policy=policy)
Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
