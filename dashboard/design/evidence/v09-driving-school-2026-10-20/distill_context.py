from pathlib import Path
import json
import numpy as np
from game_learning import forward,backward,Adam,random_weights
from game_direct import snapshot
from game_direct_bootstrap import direct_profile
r=Path(__file__).parent;data=np.load(r/'preserved-data-driving.npz');x=data['x'];original_y=data['y'];traffic=x[:,[17,24,31]].sum(axis=1)>0
for role in ('driving','traffic'):
 old=json.loads((Path('/tmp/smartpc-driving-school-baseline')/('game-direct-base.json' if role=='driving' else 'game-direct-tactical-base.json')).read_text())['policy'];y=original_y.copy();y[traffic]=np.tanh(forward(np.array(old['weights']),x[traffic],64))
 rng=np.random.default_rng(76401);weights=random_weights(rng,128,inputs=90);weights[:90*128].reshape(90,128)[np.max(abs(x),axis=0)<1e-12]=0;optimizer=Adam(len(weights))
 for k in range(14000):
  ids=rng.integers(0,len(x),128);raw,c=forward(weights,x[ids],128,cache=True);act=np.tanh(raw);g=backward(c,(act-y[ids])*(1-act*act)*np.array([8.,1.])/len(ids));optimizer.step(weights,g,.0008 if k<10000 else .0002)
  if k%4000==0:print(role,k,np.mean((np.tanh(forward(weights,x,128))-y)**2,axis=0).tolist(),flush=True)
 p=direct_profile(76401,'residual_ppo' if role=='driving' else 'residual_tactic');p['hidden']=128
 (r/('distilled-'+role+'.json')).write_text(json.dumps(dict(policy=snapshot(p,weights),source='Teacher physics for solo; previously prepared neural traffic expert; no reward-study champion',hidden=128,samples=len(x)),indent=2)+'\n')
