"""ABBA controller/visual-projection timings; not a frame-rate measurement."""
import sys,time,json,argparse,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--mature',type=Path);a=p.parse_args();sys.path.insert(0,str(a.source))
import numpy as np
from game_residual import profile,snapshot,initial_weights
from game_learning import Policy
from game_simulation import World,RAY_ANGLES
from game_control import frozen_actions
from game_catalog import RACE_PHYSICS_VERSION
runs=[];states=[]
for batch in (False,True,True,False):
 policies=[]
 for i,m in enumerate(('race_master','residual_ppo','residual_sac','residual_td3','residual_tactic')):
  pr=profile(i+1,m);weights=None if i==0 else initial_weights(pr)
  if a.mature and i==1:weights=np.asarray(json.loads(a.mature.read_text())['learner']['actor'])
  policies.append(Policy(snapshot(pr,weights)))
 w=World(5,47,shared=True,laps=10,physics=RACE_PHYSICS_VERSION,telemetry=True);w.native_sensors=True;w.reset(varied=False)
 start=time.monotonic();control=physics=projection=0.
 for k in range(1000):
  at=time.monotonic();u=frozen_actions(w,policies) if batch else np.array([p.act(None,world=w,index=i) for i,p in enumerate(policies)])
  end=time.monotonic();control+=end-at;w.step(u,return_observations=False);physics+=time.monotonic()-end
  if k%2==0:
   at=time.monotonic();rows=w.rows()
   if batch:rays=np.clip(w.sensor_rays(w.state[:1],RAY_ANGLES,150)[0]/150,0,1)
   else:rays=w.observations(version='race-68-v3')[0,:5]
   projection+=time.monotonic()-at
 states.append(w.state.copy());runs.append(dict(batch=batch,wallSeconds=time.monotonic()-start,controlSeconds=control,physicsSeconds=physics,visualProjectionSeconds=projection))
for state in states[1:]:np.testing.assert_allclose(states[0],state,atol=1e-9,rtol=0)
a.output.write_text(json.dumps(dict(runs=runs,physicalParity=True,ticks=1000,cars=5,maturePPO=bool(a.mature),matureHash=hashlib.sha256(a.mature.read_bytes()).hexdigest() if a.mature else None),indent=2)+'\n');print(json.dumps(runs))
