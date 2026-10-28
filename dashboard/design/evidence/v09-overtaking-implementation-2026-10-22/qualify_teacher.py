"""Selection-bank validation of a privately prepared traffic network."""
from pathlib import Path
import argparse,json,time,statistics
from game_learning import Policy
from game_academy import Episode
from game_rewards import specification
from game_direct_bootstrap import direct_profile
from game_overtaking import scenario
from game_school_lessons import RaceProof
p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
policy=json.loads(a.model.read_text());profile={**direct_profile(policy['recipe']['seed'],'residual_tactic'),'trafficLearning':'attack-1'};rows=[];races=[]
for family in ('complete','attack','corner','defend'):
 for seed in range(979201,979206):
  e=scenario('oval-1',family,seed,profile);driver=Policy(policy)
  while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
  rows.append(dict(family=family,result=e.result()))
 print(family,sum(r['result']['reason']=='success' for r in rows if r['family']==family),flush=True)
for bots in (1,2,3):
 for seed in range(979301,979306):
  e=Episode('oval-1','overtake',seed,objective='impara_sorpasso',bots=bots,protocol='driving-memory-1',reward_spec=specification(profile));driver=Policy(policy)
  while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
  rows.append(dict(family='traffic-'+str(bots),result=e.result()))
 print('traffic',bots,'contacts',sum(r['result']['contacts'] for r in rows if r['family']=='traffic-'+str(bots)),'exits',sum(r['result']['trackLimits'] for r in rows if r['family']=='traffic-'+str(bots)),flush=True)
for slot in (0,2,4):
 r=RaceProof(policy,'oval-1',979400+slot,slot)
 while not r.tick():pass
 races.append(r.result());print('grid',slot,r.result(),flush=True)
valid=all(not r['result']['contacts'] and not r['result']['trackLimits'] and (r['result']['reason']=='success' if not r['family'].startswith('traffic') else r['result']['passes']>=1) for r in rows)
valid=valid and all(r['reason']=='success' and r['finished']==5 for r in races)
a.output.write_text(json.dumps(dict(status='passed' if valid else 'rejected',bank='selection-not-final',model=str(a.model),rows=rows,races=races),indent=2)+'\n')
