"""Private physics and scheduler probes; no GameStore and no production writes."""
import json,sys,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from game_academy import Episode,academy_profile
from game_academy_trainer import AcademyTrainer
from game_profiles import preset
from game_rewards import specification
from game_control import pursuit_actions,racing_actions


def reference(detour=False,objective='impara'):
 p=academy_profile(preset());e=Episode('oval-1','control',901,protocol='driving-memory-1',single_lap=True,reward_spec=specification(p),objective=objective)
 crossings=[];missed=[]
 while not e.reason:
  w=e.world;before=w.state[0,:2].copy();old=float(w.progress[0]);gate=int(w.checkpoint[0])
  lane=4.6 if detour and 40<old<100 else 0.
  action=pursuit_actions(w,[0],speed_factor=.6 if detour else 1.,lateral_targets=np.array([lane]))[0]
  e.step(action)
  if old<(gate+1)*w.track.length/4<=w.progress[0] and w.checkpoint[0]==gate:
   missed.append(dict(gate=gate+1,time=e.age,outside=bool(w.was_offroad[0]),progress=float(w.progress[0])))
  if before[0]<0<=w.state[0,0] and w.state[0,1]<-20:
   crossings.append(dict(time=e.age,progress=float(w.progress[0]),valid=e.valid_progress,gate=int(w.checkpoint[0]),reason=e.reason,active=bool(w.active[0]),trackLimits=int(w.track_limits[0])))
 result=e.result();return dict(reason=e.reason,age=e.age,progress=float(w.progress[0]),valid=e.valid_progress,gate=int(w.checkpoint[0]),trackLimits=int(w.track_limits[0]),outsideSeconds=float(w.offroad_seconds[0]),physicalFinishCrossings=crossings,missedGates=missed,result=result)


def window(method):
 p=academy_profile(preset(1,method));t=AcademyTrainer(p,'oval-1',balanced=True,batched=True,objective='impara_infinito')
 for e in t.episodes:
  e.reason='window';e.truncated=True;e.recorded=True;e.age=60.;e.world.time=60.;e.world.progress[0]=2*e.world.track.length;e.world.checkpoint[0]=8;e.lap_seen=2
 for _ in range(64):
  t.tick()
  if not any(e.reason=='window' for e in t.episodes):break
 return dict(method=method,worldTime=t.episodes[0].world.time,age=t.episodes[0].age,checkpoint=int(t.episodes[0].world.checkpoint[0]),revision=t.episodes[0].revision,generation=getattr(t.learner,'generation',getattr(t.learner,'update_index',None)),scope='Synthetic completed window to isolate scheduler, not a physical 60 s training run')

out=dict(cleanLap=reference(),outsideAndReentry=reference(True),continuousReference=reference(objective='impara_infinito'),windowBoundary=[window(m) for m in ('evolution','neat','ppo','imitation')])
Path(sys.argv[1]).write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
for k,r in out.items():print(k, {j:v for j,v in r.items() if j not in ('result',)} if isinstance(r,dict) else r,flush=True)
