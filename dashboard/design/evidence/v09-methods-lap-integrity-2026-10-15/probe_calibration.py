"""One-seed short learning calibration through private Start preparation."""
from pathlib import Path
from copy import deepcopy
import argparse,json,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from game_store import GameStore
from game_academy_trainer import AcademyTrainer
from game_academy import Episode
from game_learning import PPO,PPOSmooth,Imitation,Policy
from game_rewards import specification
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--name',required=True);p.add_argument('--budget',type=int,default=50000);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
s=json.loads(a.source.read_text());d=next(d for d in s['tables']['drivers'] if d['name']==a.name);profile=json.loads(d['profile']);c=deepcopy(s['artifacts'].get(d['checkpoint'],{}).get('value'))

def test(policy,profile):
 rows=[];policy=Policy(policy)
 for goal in (1.,20.):
  for seed in (9901000,9901001):
   e=Episode('oval-1','launch',seed,protocol='driving-memory-1',launch_distance=goal,reward_spec=specification(profile))
   while not e.reason:e.step(policy.act(e.observations(),world=e.world,index=0))
   rows.append(dict(goal=goal,seed=seed,reason=e.reason,seconds=e.age,progress=e.valid_progress))
 return rows

with tempfile.TemporaryDirectory(prefix='smartpc-method-calibration-') as private:
 store=GameStore(private);identity=store.create_driver('Calibrazione privata',profile['algorithm']);store.set_profile(identity,profile,allow_reconfigure=True)
 if c:
  cls={'ppo':PPO,'ppo_smooth':PPOSmooth,'imitation':Imitation}[profile['algorithm']]
  obj=cls(profile,c['learner']);store.save_training(identity,c,obj.policy(),c['steps'],c['seconds'],curriculum=c.get('curriculum'))
 store.activate_academy(identity);store.prepare_driving(identity);driver=store.driver(identity);profile=driver['profile'];saved=store.load(driver['checkpoint']) if driver['checkpoint'] else None
 t=AcademyTrainer(profile,'oval-1',saved,balanced=True,batched=True)
 before=test(t.learner.policy(),profile);start=t.steps;begin=time.monotonic();waiting=0;ticks=0
 while t.steps-start<a.budget:
  previous=t.steps;t.tick();ticks+=1;waiting+=int(previous==t.steps and bool(t.review or t.evaluation))
  if time.monotonic()-begin>240:raise RuntimeError('Diagnostic deadline')
 result=dict(name=a.name,profile=profile,budget=a.budget,trainingSteps=t.steps-start,pcWallSeconds=time.monotonic()-begin,
  before=before,after=test(t.learner.policy(),profile),phase=t.phase,launchGoal=t.launch_goal,updates=t.state['updates'],
  parameterUpdates=getattr(t.learner,'sample_count',getattr(t.learner,'update_index',None)),
  metric=t.metric,reviewTicksWithNoTraining=waiting,reviewStillRunning=bool(t.review),stats={k:v for k,v in t.state['stats'].items() if k not in ('firstMeterTimes','tenMeterTimes')},
  scope='One-seed 50k-transition calibration on private copies; actual Start migration, no production training, not convergence certification')
 a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({k:result[k] for k in ('name','trainingSteps','pcWallSeconds','phase','launchGoal','updates','before','after')}),flush=True)
