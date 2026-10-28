"""Finite-budget matched training; private checkpoints, public cost/outcomes."""
from pathlib import Path
import argparse,json,time,hashlib
import numpy as np
from game_direct_bootstrap import direct_profile,base_asset
from game_direct import snapshot
from game_direct_trainer import DirectTrainer
from game_learning import Policy
from game_overtaking import scenario
from game_residual import key
p=argparse.ArgumentParser();p.add_argument('--method',required=True);p.add_argument('--seed',type=int,required=True)
p.add_argument('--coefficient',type=float,default=.25);p.add_argument('--budget',type=int,default=196608)
p.add_argument('--output',type=Path,required=True);p.add_argument('--private',type=Path,required=True)
p.add_argument('--baseline',action='store_true');a=p.parse_args()
profile=direct_profile(a.seed,a.method)
if not a.baseline:profile.update(trafficLearning='attack-1',relativeAdvantage=a.coefficient)
# Same initial weights for paired old/new curriculum comparisons. This is not
# five independently prepared teachers, which is reported explicitly.
weights=np.asarray(base_asset('traffic')['policy']['weights']).copy();weights[-91:]*=.5
initial=snapshot(profile,weights)
resumed=json.loads(a.private.read_text()) if a.private.exists() else None
t=DirectTrainer(profile,'oval-1',resumed or dict(initialPolicy=initial),objective='impara_sorpasso')
start=time.monotonic();cpu=time.process_time();last=0
def save():
 a.private.parent.mkdir(parents=True,exist_ok=True)
 temporary=a.private.with_suffix('.tmp');temporary.write_text(json.dumps(t.checkpoint(0.)));temporary.chmod(0o600);temporary.replace(a.private)
while t.steps<a.budget or t.check or t.iterator:
 t.tick()
 if t.steps//32768>last:
  last=t.steps//32768;save();print('steps',t.steps,'updates',t.learner.update_index,'wall',round(time.monotonic()-start,1),flush=True)
learning=time.monotonic()-start
save()
results={}
# Development only; final bank is separately frozen before selection.
eval_profile={**profile,'trafficLearning':'attack-1','relativeAdvantage':a.coefficient}
for role,policy in (('initial',initial),('candidate',t.learner.policy()),('solo',t.state['champion']['policy']),('traffic',t.state.get('attackChampion',t.state.get('raceChampion',t.state['champion']))['policy'])):
 rows=[]
 for family in ('complete','attack','corner','defend'):
  for seed in (976101,976102,976103):
   e=scenario('oval-1',family,seed,eval_profile);driver=Policy(policy)
   while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
   rows.append(dict(family=family,result=e.result()))
 results[role]=dict(policyHash=key(policy),rows=rows)
root=Path(__import__('game_direct').__file__).parent
out=dict(method=a.method,seed=a.seed,coefficient=a.coefficient,baseline=a.baseline,physicalSteps=t.steps,
 resumedFromSteps=(resumed or {}).get('steps',0),timingsCoverWholeRun=resumed is None,
 decisions=t.decisions,updates=t.learner.update_index,learningSeconds=learning,wallSeconds=time.monotonic()-start,cpuSeconds=time.process_time()-cpu,
 evaluationSeconds=t.state.get('evaluationSeconds',0),evaluationSteps=t.state.get('evaluationSteps',0),teacherCalls=0,
 stats=t.state['stats'],evaluations=t.state['evaluations'],results=results,recipe=t.spec,
 sourceHashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in root.glob('game*.py')},commonPreparedBase=True,modelsPrivate=True)
a.output.write_text(json.dumps(out,indent=2)+'\n');print('done',a.method,a.seed,a.coefficient,a.baseline,flush=True)
