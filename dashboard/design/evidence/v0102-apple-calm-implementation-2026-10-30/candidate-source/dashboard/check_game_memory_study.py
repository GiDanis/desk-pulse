"""Reproducible five-seed screening, copies only, fixed transition/CPU budgets."""
import argparse,json,time,concurrent.futures
from pathlib import Path
from game_academy import academy_profile
from game_academy_trainer import AcademyTrainer
from game_catalog import configuration
from game_profiles import preset
from game_driving_memory import PROTOCOL,seed_learner


def build(method,seed,track,backend=None,memory=None,tuning=None):
 p=academy_profile(preset(seed,method))
 c=dict(configuration=configuration(track,p['observation']),protocol=PROTOCOL,learner=backend,memory=memory or {})
 if tuning:c['tuning']=tuning
 return AcademyTrainer(p,track,c)


def train(t,budget,cpu_cap):
 start=time.process_time();steps=t.steps;calls=0
 while t.steps-steps<budget and time.process_time()-start<cpu_cap:
  t.tick();calls+=1
 stats=t.state['stats'];duration=time.process_time()-start
 return dict(steps=t.steps-steps,cpuSeconds=duration,calls=calls,phase=t.phase,goal=t.launch_goal,
  episodes=stats['episodes'],success=stats['success'],stalls=stats['no_progress'],recoveries=stats['recoverySuccess'],
  updates=t.state['updates'],learnerGeneration=getattr(t.learner,'generation',None),learnerUpdates=getattr(t.learner,'update_index',None),evaluationRound=t.state['round'],metric=t.metric,
  stopped='transitions' if t.steps-steps>=budget else 'cpu-budget')


def case(args):
 method,seed,kind,budget,cap=args
 if kind=='transfer':
  source=build(method,seed,'oval-1');source_result=train(source,budget,cap)
  policy=source.learner.candidate_policy() if hasattr(source.learner,'candidate_policy') else source.learner.policy()
  inherited=seed_learner(source.profile,policy,source.learner.checkpoint())
  modes=[]
  for mode in ('scratch','transfer','transfer-replay'):
   memory=dict(coverage=[dict(track='oval-1',phase='launch')]) if mode=='transfer-replay' else {}
   target=build(method,seed,'technical-1',inherited if mode!='scratch' else None,memory)
   # Screening has the same training task, no certification or skipped stages.
   result=train(target,budget,cap);modes.append(dict(mode=mode,**result))
  return dict(kind=kind,method=method,seed=seed,source=source_result,modes=modes)
 tuning={}
 if kind.startswith('ppo:'):
  _,batch,lam=kind.split(':');tuning=dict(batchSize=int(batch),gaeLambda=float(lam))
 t=build(method,seed,'oval-1',tuning=tuning)
 if kind.startswith('mutation:'):t.learner.profile={**t.profile,'mutation':float(kind.split(':')[1])}
 return dict(kind=kind,method=method,seed=seed,**train(t,budget,cap))


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--steps',type=int,default=12000);p.add_argument('--cpu-seconds',type=float,default=20);p.add_argument('--workers',type=int,default=2);a=p.parse_args()
 cases=[]
 for seed in range(1,6):
  for method in ('evolution','neat','ppo','ppo_smooth','imitation'):cases.append((method,seed,'transfer',a.steps,a.cpu_seconds))
  for mutation in (.05,.1,.15):cases.append(('evolution',seed,'mutation:'+str(mutation),a.steps,a.cpu_seconds))
  for batch,lam in ((64,.95),(128,.95),(128,.9921)):
   cases.append(('ppo',seed,f'ppo:{batch}:{lam}',a.steps,a.cpu_seconds))
 result=dict(scope='Five-seed initial-task screening, not mature racing qualification',protocol=PROTOCOL,
  stepsPerStage=a.steps,cpuBudgetPerStage=a.cpu_seconds,seeds=list(range(1,6)),results=[])
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
  futures={pool.submit(case,c):c for c in cases}
  for f in concurrent.futures.as_completed(futures):
   c=futures[f]
   try:row=f.result()
   except Exception as error:row=dict(method=c[0],seed=c[1],kind=c[2],error=str(error))
   result['results'].append(row);a.output.write_text(json.dumps(result,indent=2)+'\n')
   print(c[0],c[1],c[2],'done',flush=True)
 result['status']='passed' if all('error' not in r for r in result['results']) else 'failed'
 a.output.write_text(json.dumps(result,indent=2)+'\n')
 if result['status']!='passed':raise RuntimeError('Screening case failed')


if __name__=='__main__':main()
