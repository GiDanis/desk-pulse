"""Supplementary frozen latency and two-car bank, no feedback or tuning."""
from pathlib import Path
import json,argparse,statistics,hashlib
import numpy as np
from game_learning import Policy
from game_overtaking import scenario
from game_direct_bootstrap import direct_profile,base_asset
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_control import frozen_actions
P=Path(__file__).parent;p=argparse.ArgumentParser();p.add_argument('name');a=p.parse_args()
private=Path('/tmp/smartpc-attack-implementation-20261022/final-models');c=json.loads((private/(a.name+'.json')).read_text());state=c['curriculum'];policy=state.get('raceChampion',state['champion'])['policy'];seed=state['trainingProfile']['seed']
profile={**direct_profile(seed,policy['algorithm']),'trafficLearning':'attack-1','relativeAdvantage':0.};rows=[];grids=[]
for family in ('attack',):
 for s in range(977101,977111):
  e=scenario('oval-1',family,s,profile);driver=Policy(policy)
  while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
  rows.append(e.result())
for seed,slot in ((977501,0),(977502,1)):
 opponent=base_asset('traffic')['policy'];policies=[Policy(opponent)];policies.insert(slot,Policy(policy))
 w=World(2,seed,shared=True,laps=3,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True);w.native_sensors=True;w.race_lap_target=True
 contacts=set();ego=set()
 while True:
  w.step(frozen_actions(w,policies),return_observations=False)
  for event in w.events:
   if event.get('type')=='contact':
    key=(event['time'],tuple(event['cars']));contacts.add(key)
    if slot in event['cars']:ego.add(key)
  if w.retired.any() or not w.active.any() or w.time>=150.:break
 grids.append(dict(seed=seed,slot=slot,reason='retirement' if w.retired.any() else 'success' if not w.active.any() else 'timeout',seconds=w.time,finished=int(np.isfinite(w.finish).sum()),contacts=len(contacts),egoContacts=len(ego),limits=int(w.track_limits.sum()),egoLimits=int(w.track_limits[slot])))
(P/'supplement'/(a.name+'.json')).write_text(json.dumps(dict(rows=rows,races=grids,scope='Added after frozen primary bank; no model tuning',sourceHash=hashlib.sha256(Path(__import__('game_overtaking').__file__).read_bytes()).hexdigest()),indent=2)+'\n')
