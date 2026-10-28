"""Five independent student fits to the same frozen neural preparation teacher.

No new privileged information, no physical teacher or production pilot is used.
This compares representational retention, not equal preparation compute.
"""
from pathlib import Path
import concurrent.futures,json,time
import numpy as np
from game_direct_bootstrap import direct_profile,base_asset,fit
from game_direct import snapshot,features
from game_learning import Policy,forward
from game_neural_mixture import EXPERT_SIZE
from game_overtaking import scenario
P=Path(__file__).parent;private=Path('/tmp/smartpc-attack-implementation-20261022/dense');private.mkdir(parents=True,exist_ok=True)
profile={**direct_profile(811,'residual_td3'),'trafficLearning':'attack-1'}
weights=np.asarray(base_asset('traffic')['policy']['weights']).copy();weights[-91:]*=.5
teacher=snapshot(profile,weights);x=[];y=[];calls=0
for family in ('complete','attack','corner','defend','pace','recover','traffic'):
 for seed in (978101,978102):
  e=scenario('oval-1',family,seed,profile);driver=Policy(teacher)
  while not e.reason:
   tick=round(e.world.time*60)
   if tick%6==0:
    z=features(e.world);x.append(z);y.append(np.tanh(forward(weights,z,128)));calls+=1
   e.step(driver.act(None,world=e.world,index=0),return_observation=False)
x=np.asarray(x);y=np.asarray(y);np.savez(private/'labels.npz',x=x,y=y)
def fit_one(seed):
 start=time.monotonic();rng=np.random.default_rng(seed);w=weights[EXPERT_SIZE:2*EXPERT_SIZE].copy()
 _,mse=fit(w,x,y,rng,6000)
 p={**profile,'seed':seed,'hidden':64};policy=snapshot(p,w);out=[]
 for family in ('complete','attack','corner','defend','pace','traffic'):
  for scenario_seed in (978201,978202):
   e=scenario('oval-1',family,scenario_seed,p);driver=Policy(policy)
   while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
   out.append(dict(family=family,result=e.result()))
 (private/(str(seed)+'.json')).write_text(json.dumps(policy))
 return dict(seed=seed,mse=mse.tolist(),seconds=time.monotonic()-start,rows=out)
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for r in pool.map(fit_one,range(811,816)):
  rows.append(r);(P/'dense-controls.json').write_text(json.dumps(dict(neuralTeacherCalls=calls,physicalTeacherCalls=0,sharedFrozenCorpus=True,equalCompute=False,modelsPrivate=True,rows=rows),indent=2)+'\n')
  print('dense',r['seed'],sum(v['result']['reason']=='success' for v in r['rows']),len(r['rows']),flush=True)
