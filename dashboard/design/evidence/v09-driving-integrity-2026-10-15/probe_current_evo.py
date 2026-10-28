"""Frozen current Evo, no optimizer; actual 130 s and Qualifica worlds."""
from pathlib import Path
import json,sys,time
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from game_observation_contract import migrate
from game_academy_trainer import AcademyTrainer
from game_transfer import candidate
from game_learning import Policy
from game_academy import Episode
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
s=json.loads(Path(sys.argv[1]).read_text());d=next(d for d in s['tables']['drivers'] if d['name']=='Evo');c=s['artifacts'][d['checkpoint']]['value'];profile=json.loads(d['profile']);old=json.dumps(c,sort_keys=True)
p=Policy(candidate(c,profile));rows=[]
for mode in ('qualifica','infinito'):
 w=World(1,1,laps=4 if mode=='qualifica' else 1,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True,lazy_sensors=True);w.native_sensors=True;w.continuous=mode=='infinito'
 while w.active[0] and w.time<130:
  w.step(np.array([p.act(w.observations(version=profile['observation'])[0],world=w,index=0)]),return_observations=False)
 rows.append(dict(mode=mode,time=w.time,cleanLaps=int(w.clean_laps[0]),gates=int(w.checkpoint[0]),trackLimits=int(w.track_limits[0]),retired=bool(w.retired[0]),laps=w.lap_times[0]))
assert old==json.dumps(c,sort_keys=True)
assert rows[0]['cleanLaps']==4 and rows[0]['trackLimits']==0
assert rows[1]['cleanLaps']>=5 and not rows[1]['retired'] and rows[1]['time']>=130
result=dict(frozenWeightsUntouched=True,inputContract=p.snapshot['inputContract'],rows=rows)
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
