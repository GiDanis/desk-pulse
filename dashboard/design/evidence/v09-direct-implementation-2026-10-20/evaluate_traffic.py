from pathlib import Path
import json
from game_academy import Episode
from game_learning import Policy
from game_rewards import specification
r=Path(__file__).resolve().parent;bank=json.loads((r/'final-bank.json').read_text());rows=[]
for seed in range(31,36):
 data=json.loads((r/f'final-residual_tactic-{seed}.json').read_text())
 initial=json.loads((r/'tactical-base-policy.json').read_text())
 for role,policy in [('initial',initial),('champion',data['champion'])]:
  driver=Policy(policy);spec=specification(dict(algorithm='residual_tactic',controlMode='direct'))
  for phase,seeds in bank['traffic'].items():
   for scenario in seeds:
    e=Episode('oval-1',phase,scenario,protocol='driving-memory-1',single_lap=True,reward_spec=spec)
    while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
    result=e.result();rows.append(dict(seed=seed,role=role,phase=phase,scenario=scenario,reason=e.reason,contacts=e.contact_count,limits=int(e.world.track_limits[0]),passes=e.passes,seconds=e.age,violations=getattr(e,'racecraft',{}).get('violations',0)))
  print(seed,role,sum(x['reason']=='success' for x in rows if x['seed']==seed and x['role']==role),flush=True)
(r/'traffic-final.json').write_text(json.dumps(dict(rows=rows,scope='Five frozen Tattico champions versus initial base, nine held-out traffic cases each'),indent=2)+'\n')
