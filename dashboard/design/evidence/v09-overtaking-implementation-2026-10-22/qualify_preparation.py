"""Matched neural preparation controls; no training, no production access."""
from pathlib import Path
from copy import deepcopy
import json,time
import numpy as np
from game_direct_bootstrap import base_asset,direct_profile
from game_direct import snapshot
from game_learning import Policy
from game_overtaking import scenario
P=Path(__file__).parent;rows=[]
profile={**direct_profile(71,'residual_tactic'),'trafficLearning':'attack-1'}
for variant,scale,role in (('driving',1.,'driving'),('traffic',1.,'traffic'),('warm-gate',.5,'traffic'),('softer-gate',.25,'traffic')):
 w=np.array(base_asset(role)['policy']['weights']);w[-91:]*=scale;policy=snapshot(profile,w)
 for family in ('complete','attack','corner','defend'):
  for seed in (975101,975102,975103,975104,975105):
   e=scenario('oval-1',family,seed,profile);driver=Policy(policy)
   while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
   rows.append(dict(variant=variant,family=family,seed=seed,result=e.result()))
   (P/'preparation-controls.json').write_text(json.dumps(dict(status='diagnostic',rows=rows),indent=2)+'\n')
  group=[r['result'] for r in rows if r['variant']==variant and r['family']==family]
  print(variant,family,'valid',sum(r['reason']=='success' for r in group),'contacts',sum(r['contacts'] for r in group),'limits',sum(r['trackLimits'] for r in group),flush=True)
