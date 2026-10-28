"""Frozen A/B: identical network/physical start, changed phase cue/deployment."""
from pathlib import Path
import sys,json
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from game_learning import Evolution,Policy
from game_academy import Episode
from game_rewards import specification
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
s=json.loads(Path(sys.argv[1]).read_text());d=next(d for d in s['tables']['drivers'] if d['name']=='Evo');p=json.loads(d['profile']);c=s['artifacts'][d['checkpoint']]['value']
policies={'candidate':Policy(Evolution(p,c['learner'],evo_v2=True).candidate_policy()),'memoryBase':Policy(c['memory']['baseline'])}
rows=[]
for name,policy in policies.items():
 for phase,objective in [('pace','impara'),('control','impara'),('pace','impara_infinito'),('control','impara_infinito')]:
  for seed in (901,902):
   e=Episode('oval-1',phase,seed,protocol='driving-memory-1',single_lap=True,objective=objective,reward_spec=specification(p),pace_pressure=1. if phase=='pace' else 0.)
   obs=e.observations();initial=policy.act(obs,world=e.world,index=0).tolist()
   while not e.reason:e.step(policy.act(e.observations(),world=e.world,index=0))
   rows.append(dict(policy=name,phase=phase,objective=objective,seed=seed,phaseCue=float(obs[67]),initialAction=initial,reason=e.reason,seconds=e.age,progress=float(e.world.progress[0]),valid=e.valid_progress,trackLimits=int(e.world.track_limits[0]),gates=int(e.world.checkpoint[0])))
 for mode in ('qualifica',):
  w=World(1,1,laps=4,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True,lazy_sensors=True);w.native_sensors=True;w.reset(varied=False)
  o=w.observations(version=p['observation'])[0];initial=policy.act(o,world=w,index=0).tolist()
  while w.active[0] and w.time<150:
   obs=w.observations(version=p['observation']);w.step(np.array([policy.act(obs[0],world=w,index=0)]),return_observations=False)
  rows.append(dict(policy=name,mode=mode,seed=1,phaseCue=float(o[67]),initialAction=initial,reason='contact' if w.retired[0] else 'finished' if not w.active[0] else 'diagnostic-limit',seconds=w.time,progress=float(w.progress[0]),trackLimits=int(w.track_limits[0]),gates=int(w.checkpoint[0]),lapTimes=w.lap_times[0]))
Path(sys.argv[2]).write_text(json.dumps(dict(scope='Frozen private A/B; phase cue differs even with identical physical launch, real qualification World uses cue 1',rows=rows),indent=2,allow_nan=False)+'\n')
for r in rows:print(r,flush=True)
