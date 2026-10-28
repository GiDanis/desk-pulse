"""Diagnostic only: change one observation feature, never steering/pedal actions."""
from pathlib import Path
import sys,json
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from game_academy import Episode
from game_learning import Policy,Evolution
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
s=json.loads(Path(sys.argv[1]).read_text());d=next(d for d in s['tables']['drivers'] if d['name']=='Evo');p=json.loads(d['profile']);c=s['artifacts'][d['checkpoint']]['value']
policies={'candidate':Policy(Evolution(p,c['learner'],evo_v2=True).candidate_policy()),'memoryBase':Policy(c['memory']['baseline'])}
a=Episode('oval-1','pace',901,protocol='driving-memory-1',single_lap=True);b=Episode('oval-1','control',901,protocol='driving-memory-1',single_lap=True)
result=dict(initialPhysicalStatesEqual=bool(np.array_equal(a.world.state,b.world.state)),initialObservationChangedIndices=np.flatnonzero(a.observations()!=b.observations()).tolist(),rows=[],scope='Private diagnostic observation adapter; one feature changed before inference, no action override or production modifications')
for name,policy in policies.items():
 for cue in (1.,2/9,1/9):
  w=World(1,1,laps=4,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True,lazy_sensors=True);w.native_sensors=True;w.reset(varied=False)
  while w.active[0] and w.time<150:
   obs=w.observations(version='race-68-v3')[0];obs[67]=cue
   action=policy.act(obs,world=w,index=0)
   w.step(np.array([action]),return_observations=False)
  row=dict(policy=name,cue=cue,seconds=w.time,retired=bool(w.retired[0]),gates=int(w.checkpoint[0]),trackLimits=int(w.track_limits[0]),laps=w.lap_times[0],finished=bool(np.isfinite(w.finish[0])))
  result['rows'].append(row);print(row,flush=True)
Path(sys.argv[2]).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
