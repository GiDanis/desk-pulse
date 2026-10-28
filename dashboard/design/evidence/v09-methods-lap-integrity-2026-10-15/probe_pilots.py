"""Frozen learners, equal physical scenarios, no training or production imports."""
from copy import deepcopy
from collections import Counter
import sys,json,time,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from game_academy import Episode,academy_profile
from game_academy_trainer import AcademyTrainer
from game_learning import Evolution,Policy,PPO,PPOSmooth,Imitation
from game_neat import NEAT
from game_batch import BatchPhysics
from game_profiles import preset,reference_policy
from game_rewards import specification
from game_control import racing_actions
from game_evo_plan import stage_scenario

s=json.loads(Path(sys.argv[1]).read_text());out=Path(sys.argv[2]);profiles={d['name']:json.loads(d['profile']) for d in s['tables']['drivers']}
def checkpoint(name):
 d=next(d for d in s['tables']['drivers'] if d['name']==name)
 return deepcopy(s['artifacts'].get(d['checkpoint'],{}).get('value',{}))
def finish(e):
 w=e.world
 return dict(reason=e.reason,seconds=e.age,progress=float(w.progress[0]),valid=e.valid_progress,gate=int(w.checkpoint[0]),trackLimits=int(w.track_limits[0]),offroadSeconds=float(w.offroad_seconds[0]),reward=e.return_total,terms=e.term_totals,pedals=e.pedal_counts,maxSpeedKmh=float(w.max_speed[0])*3.6)
def population(name,phase,seeds,scenario_level=None):
 p=profiles[name];c=checkpoint(name);l=(Evolution(p,c['learner'],evo_v2=True) if name=='Evo' else NEAT(p,c['learner']));l.driving_balance=True
 rows=[];first=[];start=time.monotonic()
 for seed in seeds:
  scenario=stage_scenario('oval-1',scenario_level,seed) if scenario_level is not None else None
  eps=[Episode('oval-1',phase,seed,protocol='driving-memory-1',single_lap=True,reward_spec=specification(p),pace_pressure=(c.get('curriculum') or {}).get('pacePressure',0),scenario=scenario) for _ in range(32)]
  initial=l.act(np.array([e.observations() for e in eps]));first.append(dict(seed=seed,steerSaturated=int((abs(initial[:,0])>.9).sum()),steerOverHalf=int((abs(initial[:,0])>.5).sum()),gas=int((initial[:,1]>.05).sum()),brake=int((initial[:,1]<-.05).sum())))
  b=BatchPhysics()
  while not all(e.reason for e in eps):
   actions=l.act(np.array([e.observations() for e in eps]));packets=b.prepare(eps,actions)
   for i,e in enumerate(eps):
    if not e.reason:e.step(actions[i],physics=packets[i])
  for i,e in enumerate(eps):rows.append(dict(seed=seed,index=i,**finish(e)))
 result=dict(name=name,phase=phase,scope='Frozen population; fresh episodes, equal seed for all 32 candidates; no mutations or optimizer updates',seeds=seeds,firstActions=first,reasonCounts=dict(Counter(r['reason'] for r in rows)),rows=rows,pcWallSeconds=time.monotonic()-start)
 print(name,phase,result['reasonCounts'],first,flush=True);return result

def frozen(policy,label,phase,objective='impara',seeds=(901,902),scenario_level=None):
 p=profiles['Evo'];rows=[]
 for seed in seeds:
  scenario=stage_scenario('oval-1',scenario_level,seed) if scenario_level is not None else None
  e=Episode('oval-1',phase,seed,protocol='driving-memory-1',single_lap=True,reward_spec=specification(p),objective=objective,scenario=scenario)
  while not e.reason:e.step(policy.act(e.observations(),world=e.world,index=0))
  rows.append(dict(seed=seed,**finish(e)))
 print(label,phase,objective,[r['reason'] for r in rows],flush=True)
 return dict(label=label,phase=phase,objective=objective,rows=rows)

result=dict(sourceCaptured=s['captured'],sourceHashes=s['sourceSha256'],populations=[],policies=[],initialization=[])
result['populations'].append(population('Evo','pace',(1100704,1100705)))
neat_seed=checkpoint('Neat')['episodes'][0]['seed'];result['populations'].append(population('Neat','bend',(neat_seed,neat_seed+1)))
result['populations'].append(population('Neat','launch',(1100000,),scenario_level=0))
evo=checkpoint('Evo');policy=Policy(Evolution(profiles['Evo'],evo['learner'],evo_v2=True).candidate_policy())
obj=json.loads(s['tables']['objective_paths'][0]['state']);continuous=s['artifacts'][obj['checkpoint']]['value']
local=Policy(Evolution(profiles['Evo'],continuous['learner'],evo_v2=True).candidate_policy())
base=Policy(evo['memory']['baseline'])
for label,obj in [('Evo corrente',policy),('Evo locale infinito',local),('Evo base personale',base),('Riferimento dichiarato',Policy(reference_policy('oval-1',academy=True)))]:
 result['policies'].append(frozen(obj,label,'control'))
 result['policies'].append(frozen(obj,label,'control','impara_infinito'))
for name,method,cls in [('PPO','ppo',PPO),('PPO-Smooth','ppo_smooth',PPOSmooth),('Clone','imitation',Imitation)]:
 p=academy_profile(profiles[name]);c=checkpoint(name);backend=c.get('learner');obj=cls(p,backend);obj.driving_balance=True
 e=Episode('oval-1','launch',1100000,protocol='driving-memory-1',launch_distance=1.,reward_spec=specification(p));obs=np.repeat(e.observations()[None,:],32,axis=0)
 acts=obj.sample(obs)[0] if isinstance(obj,PPO) else obj.act(obs)
 result['initialization'].append(dict(name=name,kind='stored' if backend else 'cold-diagnostic-not-a-saved-model',steps=c.get('steps',0),update=(backend or {}).get('update'),gas=int((acts[:,1]>.05).sum()),brake=int((acts[:,1]<-.05).sum()),steerSaturated=int((abs(acts[:,0])>.9).sum()),meanAction=acts.mean(axis=0).tolist(),stdAction=acts.std(axis=0).tolist(),teacherAction=e.teacher_actions().tolist()))
 result['policies'].append(frozen(Policy(obj.policy()),name+' deterministico','launch',scenario_level=0))
 result['policies'].append(frozen(Policy(obj.policy()),name+' deterministico','control'))
result['scope']='Private frozen diagnostics, not a convergence benchmark or a reproduction of live optical jitter. No original pilot changes.'
out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
