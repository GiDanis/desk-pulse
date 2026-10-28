from pathlib import Path
import json,itertools
import numpy as np
from game_learning import forward,Adam,Policy
from game_direct import features,controls
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_control import frozen_actions
from game_residual import profile,snapshot
r=Path(__file__).parent;fast=json.loads((r/'school-candidate.json').read_text())['policy'];oldroot=Path('/tmp/smartpc-driving-school-baseline')
x=np.c_[np.array(list(itertools.product((0.,1.),repeat=3))),np.ones(8)];y=(x[:,:3].sum(axis=1)>0).astype(float);gate=np.zeros(4);opt=Adam(4)
for _ in range(3000):
 pred=1/(1+np.exp(-x@gate));opt.step(gate,x.T@(pred-y)/8,.03)
g=np.zeros(91);g[[17,24,31,90]]=gate;print('Gate',gate.tolist(),'pred',pred.tolist(),flush=True)
class Driver:
 kind='direct';inputs=68;snapshot={'controller':'neural-mixture-prototype'}
 def __init__(self,role):
  self.traffic=np.array(json.loads((oldroot/('game-direct-tactical-base.json' if role=='traffic' else 'game-direct-base.json')).read_text())['policy']['weights']);self.fast=np.array(fast['weights']);self.cache={}
 def act(self,obs=None,world=None,index=0):
  tick=round(world.time*60);key=(id(world),index);cached=self.cache.get(key)
  if cached is None or tick<cached[0] or tick-cached[0]>=6:
   z=features(world,index);gate=float(1/(1+np.exp(-np.r_[z,1.]@g)));raw=(1-gate)*forward(self.fast,z,64)+gate*forward(self.traffic,z,64);cached=(tick,np.tanh(raw));self.cache[key]=cached
  return controls(world,cached[1],[index])[0]
rows=[]
for slot in range(5):
 seed=969001+slot;w=World(5,seed,shared=True,laps=3,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True);w.native_sensors=True;w.race_lap_target=True
 policies=[Driver('driving') for _ in range(3)]+[Policy(snapshot(profile(1,'race_master')))];policies.insert(slot,Driver('traffic'));rng=np.random.default_rng(seed)
 for i in range(5):w.perturb(i,float(rng.uniform(-.08,.08)),float(rng.uniform(-.005,.005)))
 seen=set()
 while w.active.any() and w.time<170:
  w.step(frozen_actions(w,policies),return_observations=False)
  for e in w.events:
   if e.get('type')=='contact':seen.add((e['time'],tuple(e['cars'])))
 row=dict(slot=slot,finished=int(np.isfinite(w.finish).sum()),limits=w.track_limits.tolist(),contacts=len(seen),retired=w.retired.tolist(),rows=w.rows());rows.append(row);print('mixture',slot,row['finished'],row['limits'],row['contacts'],flush=True)
(r/'mixture-prototype.json').write_text(json.dumps(dict(gate=g.tolist(),rows=rows),indent=2)+'\n')
