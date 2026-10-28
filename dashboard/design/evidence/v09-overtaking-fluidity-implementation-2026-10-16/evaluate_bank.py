"""Frozen scenario bank; all entrants use the same new environment and limits."""
import argparse,json,sys,time,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--input',type=Path);p.add_argument('--policy',choices=('champion','candidate'),default='champion');p.add_argument('--bank',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.source))
from game_residual import profile,snapshot
from game_learning import Policy
from game_rewards import specification
from game_academy import Episode
import numpy as np
bank=json.loads(a.bank.read_text());policy=json.loads(a.input.read_text())[a.policy] if a.input else snapshot(profile(1,'race_master'))
controller=Policy(policy);rows=[];start=time.monotonic();reward=specification(profile(1,'residual_tactic'))
for case in bank['cases']:
 phase,seed=case['phase'],case['seed']
 e=Episode('oval-1',phase,seed,protocol='driving-memory-1',single_lap=True,reward_spec=reward)
 w=e.world
 for i in range(w.count):
  distance=0 if i==0 else case['gap']
  lateral=case['ownLane'] if i==0 else case['otherLane']
  w.state[i,:3]=w.track.pose(case['start']+distance,lateral)
  w.state[i,3]=case['ownSpeed'] if i==0 else case['otherSpeed']
  w.progress[i]=distance
 w.previous_phase=w.coordinates()[2].copy();w.progress_origin=w.previous_phase.copy();w.initialize_gates()
 e.style=case['style'];e.initial_speed=case['ownSpeed'];e.start_distance=case['start']
 if phase!='pace':e.spec.update(distance=case.get('distance',240.),limitSeconds=50.)
 while not e.reason:e.step(controller.act(None,world=w,index=0))
 r=e.result();rows.append(dict(case=case,reason=r['reason'],cause=r['terminationCause'],seconds=e.age,
  passes=e.passes,contacts=e.contact_count,trackLimits=r['trackLimits'],rules=r['racecraft'].get('violations',0),reward=e.return_total,
  progress=e.valid_progress,manoeuvre=r['manoeuvre']))
result=dict(version=bank['version'],bankHash=hashlib.sha256(a.bank.read_bytes()).hexdigest(),policyHash=hashlib.sha256(json.dumps(policy,sort_keys=True).encode()).hexdigest(),
 input=str(a.input) if a.input else 'Maestro',role=a.policy,seconds=time.monotonic()-start,rows=rows)
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(output=str(a.output),seconds=result['seconds'],success=sum(r['reason']=='success' for r in rows))),flush=True)
