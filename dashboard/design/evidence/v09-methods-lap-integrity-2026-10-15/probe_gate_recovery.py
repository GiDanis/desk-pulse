"""Actual continuous motion: one missed sector, subsequent fully in-road lap."""
from pathlib import Path
import json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from game_academy import Episode,academy_profile
from game_profiles import preset
from game_rewards import specification
from game_control import pursuit_actions
p=academy_profile(preset());e=Episode('oval-1','control',901,protocol='driving-memory-1',objective='impara_infinito',reward_spec=specification(p));crossings=[];windows=[]
while e.age<130:
 if e.reason:
  if e.reason!='window':break
  windows.append(e.age);e.next_window()
 w=e.world;before=w.state[0,:2].copy();progress=float(w.progress[0]);lane=4.6 if 40<progress<100 else 0.
 action=pursuit_actions(w,[0],speed_factor=.6,lateral_targets=np.array([lane]))[0];e.step(action)
 if before[0]<0<=w.state[0,0] and w.state[0,1]<-20:
  crossings.append(dict(time=e.age,progress=float(w.progress[0]),gates=int(w.checkpoint[0]),trackLimits=int(w.track_limits[0]),outsideSeconds=float(w.offroad_seconds[0]),active=bool(w.active[0]),lapRecords=len(w.lap_times[0])))
result=dict(scope='Private real continuous physics with scripted 40-100 m detour; no telemetry teleport or learned-policy claim',windows=windows,physicalFinishCrossings=crossings,final=dict(age=e.age,reason=e.reason,gates=int(w.checkpoint[0]),progress=float(w.progress[0]),trackLimits=int(w.track_limits[0]),lapRecords=w.lap_times[0]))
Path(sys.argv[1]).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result),flush=True)
