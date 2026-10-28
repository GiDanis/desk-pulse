from pathlib import Path
from functools import partial
import argparse,json,time
import numpy as np
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_control import frozen_actions
from game_learning import Policy,Adam,forward,backward
from game_direct import snapshot,features
from game_direct_bootstrap import random_examples,rollout,physical_context,direct_profile
from game_driving_school import actions
from game_residual import profile,snapshot as old_snapshot
p=argparse.ArgumentParser();p.add_argument('--role',choices=('driving','traffic'),default='driving');a=p.parse_args();r=Path(__file__).parent
oldroot=Path('/tmp/smartpc-driving-school-baseline');old=json.loads((oldroot/('game-direct-tactical-base.json' if a.role=='traffic' else 'game-direct-base.json')).read_text())['policy'];base=np.array(old['weights']);rng=np.random.default_rng(76101);teacher=partial(actions,lane=0.,apex=0.,utilization=.65)
x,y=random_examples(76102,16384,teacher_fn=teacher)
for j in range(4):
 z,xx,yy=rollout(None,76110+j,'pace' if j<2 else 'bend',teacher=True,teacher_fn=teacher,context=physical_context(rng,j%2==1));x=np.r_[x,xx];y=np.r_[y,yy]
rx=[];ry=[]
for seed in (76201,76202):
 w=World(5,seed,shared=True,laps=3,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True);w.native_sensors=True;w.race_lap_target=True
 pols=[Policy(old) for _ in range(4)]+[Policy(old_snapshot(profile(1,'race_master')))];tick=0
 while w.active.any() and w.time<150:
  commands=frozen_actions(w,pols)
  if tick%6==0:
   for i in range(4):
    if w.active[i]:rx.append(features(w,i));ry.append(commands[i].copy())
  w.step(commands,return_observations=False);tick+=1
 print('safe rollout',seed,int(np.isfinite(w.finish).sum()),w.track_limits.tolist(),flush=True)
rx=np.array(rx);ry=np.array(ry);x=np.r_[x,rx,rx];y=np.r_[y,ry,ry]
np.savez(r/('preserved-data-'+a.role+'.npz'),x=x,y=y)
for frozen in (True,False):
 weights=base.copy();optimizer=Adam(len(weights))
 for iteration in range(10000):
  ids=rng.integers(0,len(x),128);raw,c=forward(weights,x[ids],64,cache=True);actual=np.tanh(raw)
  g=backward(c,(actual-y[ids])*(1-actual*actual)*np.array([8.,1.])/len(ids))
  if frozen:g[:91*64]=0.
  optimizer.step(weights,g,.0003 if iteration<7000 else .0001)
 label=a.role+('-frozen' if frozen else '-finetuned');z=[]
 for j in range(2):
  result,_,_=rollout(weights,76301+j,'pace');z.append(result)
 out=dict(policy=snapshot(direct_profile(76101,'residual_tactic' if a.role=='traffic' else 'residual_ppo'),weights),provenance=dict(parentPolicyHash=old.get('origin'),source='Previous prepared product base; school demonstrations plus preserved traffic behaviour',frozenFeatureLayer=frozen),samples=len(x),results=z)
 (r/('preserved-'+label+'.json')).write_text(json.dumps(out,indent=2)+'\n');print(label,[(v['reason'],v['seconds']) for v in z],flush=True)
