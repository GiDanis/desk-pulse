"""Preparation retention: solo flying laps and continuous two-bot traffic."""
from pathlib import Path
import json
import numpy as np
from game_direct_bootstrap import base_asset,direct_profile
from game_direct import snapshot
from game_academy import Episode
from game_learning import Policy
from game_rewards import specification
P=Path(__file__).parent;rows=[]
profile={**direct_profile(71,'residual_tactic'),'trafficLearning':'attack-1'}
for variant,scale,role in (('driving',1.,'driving'),('traffic',1.,'traffic'),('warm-gate',.5,'traffic'),('softer-gate',.25,'traffic')):
 w=np.array(base_asset(role)['policy']['weights']);w[-91:]*=scale;policy=snapshot(profile,w)
 for traffic in (False,True):
  for seed in (975201,975202,975203,975204,975205):
   e=Episode('oval-1','overtake' if traffic else 'pace',seed,protocol='driving-memory-1',objective='impara_sorpasso' if traffic else 'impara',bots=2,reward_spec=specification(profile),pace_pressure=1.)
   driver=Policy(policy)
   while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
   row=dict(variant=variant,traffic=traffic,seed=seed,result=e.result());rows.append(row)
   (P/'extended-preparation-controls.json').write_text(json.dumps(dict(rows=rows,status='diagnostic'),indent=2)+'\n')
  group=[r['result'] for r in rows if r['variant']==variant and r['traffic']==traffic]
  print(variant,traffic,'contacts',sum(r['contacts'] for r in group),'limits',sum(r['trackLimits'] for r in group),'passes',sum(r['passes'] for r in group),flush=True)
