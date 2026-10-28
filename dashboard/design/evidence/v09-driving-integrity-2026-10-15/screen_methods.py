"""Private equal-transition screening, isolated RNG processes, held scenarios.

No production GameStore; reports contain metrics, never model weights.
"""
from pathlib import Path
import argparse,json,sys,time,concurrent.futures,os
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from game_academy import Episode,academy_profile
from game_academy_trainer import AcademyTrainer
from game_profiles import preset
from game_learning import Policy
from game_evo_plan import stage_scenario


def run(job):
 method,seed,variant,budget=job
 saved=Path(__file__).with_name(f'screen-{method}-{variant}-{seed}.json')
 if saved.exists():
  result=json.loads(saved.read_text())
  if result['transitions']==budget:return result
 p=academy_profile(preset(seed,method))
 if variant=='lr-low':p['learningRate']=.0001
 if method=='neat':
  options={'old':(.3,.3,.15),'weights':(.08,.3,.15),'bias':(.08,.05,.15),'local':(.08,.05,.06)}
  wi,bi,mp=options[variant];p['neatTuning']=dict(weightInit=wi,biasInit=bi,mutationPower=mp)
 t=AcademyTrainer(p,'oval-1',balanced=True,batched=True)
 if variant=='gae-short':t.learner.configure_runtime({'gaeLambda':.97})
 if variant=='batch-large':t.learner.configure_runtime({'batchSize':128})
 if variant=='warm':
  from game_academy import upgrade_learner
  snap=json.loads(Path('/tmp/smartpc-methods-current-20261015.json').read_text())
  d=next(d for d in snap['tables']['drivers'] if d['name']=='PPO-Smooth')
  old=snap['artifacts'][d['checkpoint']]['value']
  from game_transfer import candidate
  from game_driving_memory import seed_learner
  from game_rewards import migrate
  policy=candidate(old,p);backend=seed_learner(p,policy,old['learner'])
  t=AcademyTrainer(p,'oval-1',dict(configuration=t.checkpoint(0)['configuration'],learner=backend,inputContract=policy['inputContract']),balanced=True,batched=True)
 start=time.monotonic();ticks=0
 while t.steps<budget:
  t.tick();ticks+=1
  if time.monotonic()-start>1500:raise RuntimeError('Screen deadline')
 snapshot=t.learner.candidate_policy() if hasattr(t.learner,'candidate_policy') else t.learner.policy()
 policy=Policy(snapshot);rows=[]
 for level in (3,5,7,10):
  for held in (9801001,9801002):
   scenario=stage_scenario('oval-1',level,held)
   e=Episode('oval-1',scenario['phase'],held,protocol='driving-memory-1',scenario=scenario,single_lap=True)
   e.world.native_sensors=True
   while not e.reason:e.step(policy.act(e.observations(),world=e.world,index=0))
   rows.append(dict(level=level,reason=e.reason,meters=e.valid_progress,seconds=e.age))
 result=dict(method=method,seed=seed,variant=variant,transitions=t.steps,wallSeconds=time.monotonic()-start,
  stage=t.evo_plan.data['level'],updates=t.state['updates'],evaluationSeconds=t.state.get('evaluationSeconds',0),
  evaluationSteps=t.evo_plan.data.get('evaluationSteps',0),held=rows,
  qualification='screening only; no convergence, optical FPS or production training claim')
 Path(__file__).with_name(f'screen-{method}-{variant}-{seed}.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ('method','seed','variant','transitions','wallSeconds','stage')}),flush=True)
 return result

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--budget',type=int,default=250000);parser.add_argument('--workers',type=int,default=3);parser.add_argument('--quick',action='store_true');a=parser.parse_args()
 jobs=[(m,s,v,a.budget) for m,variants in [('neat',('old','weights','bias','local')),('ppo',('baseline',)),('ppo_smooth',('fresh','warm')),('imitation',('baseline',))] for v in variants for s in (1,2,3)]
 if a.quick:jobs=[('neat',1,'local',a.budget),('ppo',1,'baseline',a.budget),('imitation',1,'baseline',a.budget)]
 with concurrent.futures.ProcessPoolExecutor(a.workers) as executor:results=list(executor.map(run,jobs))
 Path(__file__).with_name('screen-summary.json').write_text(json.dumps(results,indent=2)+'\n')
