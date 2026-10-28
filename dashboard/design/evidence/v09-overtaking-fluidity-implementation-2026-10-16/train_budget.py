"""Fixed collection budget; evaluation/updates are counted separately."""
import argparse,sys,time,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--method',default='residual_tactic');p.add_argument('--variant',choices=('fixed','capability'),default='fixed');p.add_argument('--source',type=Path,required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--budget',type=int,default=196608);a=p.parse_args()
sys.path.insert(0,str(a.source))
from game_residual import profile
from game_residual_trainer import ResidualTrainer
if a.variant=='capability':
 from capability_variant import CapabilityTrainer
 ResidualTrainer=CapabilityTrainer
r=profile(a.seed,a.method);t=ResidualTrainer(r,'oval-1');start=time.monotonic();last=0
while t.steps<a.budget or t.check or t.iterator:
 t.tick()
 if t.steps//32768>last:
  last=t.steps//32768;print(json.dumps(dict(seed=a.seed,steps=t.steps,seconds=time.monotonic()-start)),flush=True)
# No additional collection to finish a partial action: checkpoint keeps inflight.
result=dict(method=a.method,variant=a.variant,capability=t.state.get('capabilityExperiment'),seed=a.seed,physicalSteps=t.steps,decisions=t.decisions,seconds=time.monotonic()-start,
 evaluationSeconds=t.state.get('evaluationSeconds',0),evaluationSteps=t.state.get('evaluationSteps',0),
 stats=t.state['stats'],evaluations=t.state['evaluations'],champion=t.state['champion']['policy'],candidate=t.learner.policy(),recipe=t.spec,
 sourceHashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in a.source.glob('game_*.py')})
a.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('seed','physicalSteps','decisions','seconds','stats')}),flush=True)
