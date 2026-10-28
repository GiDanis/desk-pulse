"""Read-only saved-policy diagnosis. Pedal perturbations are private counterfactuals."""
from pathlib import Path
import json,time
import numpy as np
from game_learning import Policy
from game_direct import controls
from game_direct_bootstrap import initial_policy,direct_profile
from game_academy import Episode
from game_rewards import specification
root=Path('/tmp/smartpc-current-direct-diagnosis');out=Path(__file__).parent;rows=[]
for name,method in [('Crono','residual_ppo'),('Memoria','residual_sac')]:
 meta=next(x for x in json.loads((root/'snapshot.json').read_text()) if x['name']==name);prof=json.loads(meta['profile'])
 for role in ('initial','policy','candidate'):
  data=initial_policy(prof) if role=='initial' else json.loads((root/(name+'-'+role+'.json')).read_text())
  for boost in (0.,.25,.5,1.):
   e=Episode('oval-1','pace',91001,protocol='driving-memory-1',single_lap=True,reward_spec=specification(prof),pace_pressure=1.);driver=Policy(data);trace=[]
   while not e.reason:
    a=driver.act(None,world=e.world,index=0);w=e.world;x,y=w.state[0,:2]
    straight=abs(x)<20 and abs(y)>28 and abs(w.state[0,5])<.05
    if straight and boost:a[1]=max(a[1],boost);controls(w,a,[0])
    if round(w.time*60)%6==0:trace.append(dict(time=w.time,x=float(x),y=float(y),speed=float(w.state[0,3]*3.6),pedal=float(a[1]),steer=float(a[0]),straight=bool(straight)))
    e.step(a,return_observation=False)
   ss=[x for x in trace if x['straight']];rr=e.result();row=dict(name=name,role=role,pedalFloorOnMiddleStraight=boost,seconds=e.age,reason=e.reason,contacts=e.contact_count,limits=int(w.track_limits[0]),maxSpeed=max(x['speed'] for x in trace),meanStraightPedal=float(np.mean([x['pedal'] for x in ss])) if ss else None,straightPedalMin=min((x['pedal'] for x in ss),default=None),straightPedalMax=max((x['pedal'] for x in ss),default=None),reward=e.return_total,terms=e.term_totals,trace=trace)
   rows.append(row);print(name,role,boost,round(e.age,3),e.reason,round(row['meanStraightPedal'] or 0,3),round(row['maxSpeed'],2),flush=True)
(out/'policy-counterfactuals.json').write_text(json.dumps(dict(snapshotMeta=json.loads((root/'snapshot.json').read_text()),rows=rows,scope='Saved snapshot, same seed 91001, nominal standard oval. Counterfactual actuator floors only in a private probe; no trained or installed assist.'),indent=2)+'\n')
