"""Private fixed-budget reinforcement, initialized by a teacher-trained network."""
import argparse,json,time,hashlib
from pathlib import Path
import numpy as np
from game_residual import profile
from game_direct import snapshot
from game_direct_trainer import DirectTrainer
from game_academy import Episode
from game_learning import Policy
from game_rewards import specification

p=argparse.ArgumentParser();p.add_argument('--variant',default='final');p.add_argument('--method',required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--budget',type=int,default=None);p.add_argument('--base',required=True);p.add_argument('--output',required=True);a=p.parse_args()
if a.budget is None:a.budget=98304 if a.method=='residual_tactic' else 49152
source_root=Path(__import__('game_direct').__file__).parent
source_hashes={f:hashlib.sha256((source_root/f).read_bytes()).hexdigest() for f in ('game_direct.py','game_direct_trainer.py','game_residual_trainer.py','game_residual_learning.py','game_learning.py','game_simulation.py','game_rewards.py','game_academy.py','game_racecraft.py','game_direct_bootstrap.py','game_catalog.py','game_control.py','game_driving_memory.py','game-direct-base.json','game-direct-tactical-base.json','game_school_lessons.py','game_driving_school.py','game_neural_mixture.py')}
r=profile(a.seed,a.method);r.update(hidden=64,controlMode='direct')
if a.variant not in ('final','anchor'):r['directExperiment']=a.variant
base=json.loads(Path(a.base).read_text());r['hidden']=base['hidden'];initial=snapshot(r,base['weights'],base.get('origin'))
t=DirectTrainer(r,'oval-1',dict(initialPolicy=initial,origin='Rete da esempi del Maestro · nessun bot in guida'))
start=time.monotonic()
while t.steps<a.budget or t.check or t.iterator:t.tick()
results={}
for label,policy in (('initial',initial),('candidate',t.learner.policy()),('champion',t.state['champion']['policy'])):
 driver=Policy(policy);cases=[]
 for seed in ((961001,961002,961003,961004,961005) if a.variant=='final' else (720001,720002,720003,720004,720005)):
  e=Episode('oval-1','pace',seed,protocol='driving-memory-1',single_lap=True,reward_spec=specification(r),pace_pressure=1.)
  e.world.native_sensors=True;vmax=0.;pedal=[]
  while not e.reason:
   action=driver.act(None,world=e.world,index=0);e.step(action,return_observation=False)
   vmax=max(vmax,float(e.world.state[0,3])*3.6);pedal.append(float(action[1]))
  cases.append(dict(seed=seed,reason=e.reason,seconds=e.age,progress=e.valid_progress,limits=int(e.world.track_limits[0]),contacts=e.contact_count,vmax=vmax,fullThrottleFraction=float(np.mean(np.array(pedal)>.95))))
 results[label]=cases
Path(a.output).write_text(json.dumps(dict(method=a.method,seed=a.seed,physicalSteps=t.steps,decisions=t.decisions,updates=t.learner.update_index,teacherLabelsInRL=0,teacherOverridesEgo=0,stats=t.state['stats'],evaluations=t.state['evaluations'],results=results,champion=t.state['champion']['policy'],candidate=t.learner.policy(),recipe=t.spec,wallSeconds=time.monotonic()-start,sourceHashes=source_hashes),indent=2)+'\n')
print(json.dumps(dict(method=a.method,seed=a.seed,steps=t.steps,updates=t.learner.update_index,seconds=time.monotonic()-start,results=results)),flush=True)
