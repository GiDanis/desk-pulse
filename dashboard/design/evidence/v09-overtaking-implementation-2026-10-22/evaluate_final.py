"""Blind held-out evaluation of the exact frozen policy selected for racing."""
from pathlib import Path
import argparse,json,time,statistics,fcntl
from game_learning import Policy
from game_academy import Episode
from game_direct_bootstrap import direct_profile
from game_overtaking import scenario
from game_rewards import specification
from game_school_lessons import RaceProof
from game_residual import key
from game_direct import snapshot
P=Path(__file__).parent;p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
lock=a.output.with_suffix('.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX)
if a.output.exists():
 try:
  previous=json.loads(a.output.read_text())
  if len(previous.get('rows',[]))==58 and len(previous.get('races',[]))==2:raise SystemExit(0)
 except json.JSONDecodeError:pass
bank=json.loads((P/'final-bank.json').read_text());c=json.loads(a.checkpoint.read_text());state=c['curriculum']
policy=state.get('raceChampion',state['champion'])['policy'];method=policy['algorithm'];seed=state['trainingProfile']['seed']
profile={**direct_profile(seed,method),'trafficLearning':'attack-1','relativeAdvantage':0.}
rows=[];races=[];start=time.monotonic()
for case in bank['cases']:
 e=scenario('oval-1',case['family'],case['seed'],profile);driver=Policy(policy)
 while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
 rows.append(dict(family=case['family'],result=e.result()))
for case in bank['continuous']:
 e=Episode('oval-1','overtake',case['seed'],protocol='driving-memory-1',objective='impara_sorpasso',bots=case['bots'],reward_spec=specification(profile));driver=Policy(policy)
 while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
 rows.append(dict(family='traffic-'+str(case['bots']),result=e.result()))
for s in bank['soloSeeds']:
 e=Episode('oval-1','pace',s,protocol='driving-memory-1',reward_spec=specification(profile));driver=Policy(policy)
 while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
 flying=[r['time'] for r in e.world.lap_times[0][1:] if r['clean']]
 rows.append(dict(family='solo',flyingMedian=statistics.median(flying) if len(flying)==2 else None,result=e.result()))
for s,slot in ((977402,2),(977404,4)):
 race=RaceProof(policy,'oval-1',s,slot)
 while not race.tick():pass
 races.append(race.result())
temporary=a.output.with_suffix('.tmp')
temporary.write_text(json.dumps(dict(method=method,seed=seed,policyHash=key(policy),candidateHash=key(snapshot(state['trainingProfile'],c['learner']['actor'])),
 scope='Exact race policy only; raw candidate is exploratory and not silently substituted',rows=rows,races=races,wallSeconds=time.monotonic()-start,
 productionChanges=False,teacherCalls=0,bankVersion=bank['version']),indent=2)+'\n');temporary.replace(a.output)
print('heldout',method,seed,a.output.name,flush=True)
