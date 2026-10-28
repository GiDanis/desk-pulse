"""Offline physical teacher audit and traffic-expert preparation on copies."""
from pathlib import Path
from copy import deepcopy
from functools import partial
import argparse,json,time
import numpy as np
from game_academy import Episode
from game_direct_bootstrap import direct_profile,base_asset,fit
from game_direct import snapshot,features,controls
from game_driving_school import actions
from game_learning import Policy
from game_neural_mixture import EXPERT_SIZE
from game_rewards import specification
P=Path(__file__).parent;p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--seed',type=int,default=821);p.add_argument('--permutation',action='store_true');a=p.parse_args()
if a.permutation:
 def fit(weights,x,y,rng,iterations,optimizer=None):
  from game_learning import Adam,forward,backward
  optimizer=optimizer or Adam(len(weights))
  for step in range(iterations):
   ix=rng.integers(0,len(x),128);batch=x[ix].copy();order=np.argsort(rng.random((128,3)),axis=1)
   for start,width in ((11,7),(55,3)):
    blocks=batch[:,start:start+3*width].reshape(128,3,width).copy()
    batch[:,start:start+3*width]=np.take_along_axis(blocks,order[:,:,None],axis=1).reshape(128,3*width)
   raw,cache=forward(weights,batch,64,cache=True);act=np.tanh(raw)
   gradient=backward(cache,(act-y[ix])*(1-act*act)*np.array([4.,1.])/128)
   optimizer.step(weights,gradient,.0005 if step<iterations*2/3 else .00015)
  return optimizer,np.mean((np.tanh(forward(weights,x,64))-y)**2,axis=0)
private=Path('/tmp/smartpc-attack-implementation-20261022/teacher');private.mkdir(parents=True,exist_ok=True)
profile={**direct_profile(a.seed,'residual_tactic'),'trafficLearning':'attack-1'};teacher=partial(actions,utilization=.55)
x=[];y=[];rows=[];start=time.monotonic()
for count in (1,2,3):
 for seed in (979101,979102,979103):
  e=Episode('oval-1','overtake',seed,protocol='driving-memory-1',objective='impara_sorpasso',bots=count,reward_spec=specification(profile))
  while not e.reason:
   if round(e.world.time*60)%6==0:
    z=features(e.world);command=teacher(e.world,[0])[0];x.append(z);y.append(command.copy())
   controls(e.world,command,[0]);e.step(command,return_observation=False)
  rows.append(dict(bots=count,seed=seed,result=e.result()));print('teacher',count,seed,'passes',e.passes,'contacts',e.contact_count,'limits',int(e.world.track_limits[0]),flush=True)
(P/'physical-teacher-controls.json').write_text(json.dumps(dict(physicalTeacherDecisions=len(x),seconds=time.monotonic()-start,rows=rows,productionChanges=False),indent=2)+'\n')
np.savez(private/'labels.npz',x=np.asarray(x),y=np.asarray(y))
if a.prepare:
 weights=np.asarray(base_asset('traffic')['policy']['weights']).copy();b=weights[EXPERT_SIZE:2*EXPERT_SIZE].copy();rng=np.random.default_rng(a.seed)
 opt,error=fit(b,np.asarray(x),np.asarray(y),rng,10000);trace=[]
 for round_number in range(4):
  weights[EXPERT_SIZE:2*EXPERT_SIZE]=b;policy=snapshot(profile,weights)
  for count in (1,2,3):
   e=Episode('oval-1','overtake',a.seed*100+round_number*10+count,protocol='driving-memory-1',objective='impara_sorpasso',bots=count,reward_spec=specification(profile));driver=Policy(policy)
   teacher_lane=e.world.racing_lane.copy()
   while not e.reason:
    if round(e.world.time*60)%6==0:
     z=features(e.world);lane=e.world.racing_lane.copy();e.world.racing_lane[:]=teacher_lane
     label=teacher(e.world,[0])[0];teacher_lane=e.world.racing_lane.copy();e.world.racing_lane[:]=lane
     x.append(z);y.append(label.copy())
    e.step(driver.act(None,world=e.world,index=0),return_observation=False)
   trace.append(dict(round=round_number,bots=count,result=e.result()))
  opt,error=fit(b,np.asarray(x),np.asarray(y),rng,4000,opt)
  print('fit',round_number,'mse',error.tolist(),flush=True)
 weights[EXPERT_SIZE:2*EXPERT_SIZE]=b
 (private/(str(a.seed)+'.json')).write_text(json.dumps(snapshot(profile,weights)))
 (P/('teacher-preparation-'+str(a.seed)+'.json')).write_text(json.dumps(dict(seed=a.seed,samples=len(x),mse=error.tolist(),trace=trace,seconds=time.monotonic()-start,teacherAtInference=False,modelsPrivate=True),indent=2)+'\n')
