"""Matched private Evo start conditions; fixed transition budget, no GameStore."""
import argparse,json,sys,time
from pathlib import Path
from copy import deepcopy
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from game_academy_trainer import AcademyTrainer
from game_academy import Episode
from game_learning import Evolution,Policy
from game_driving_memory import seed_learner
from game_evo_plan import STAGES,stage_scenario
from game_rewards import specification


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=Path('/tmp/smartpc-evo-current-analysis.json'))
    p.add_argument('--condition',choices=('current','memory','cold'),required=True);p.add_argument('--seed',type=int,default=1)
    p.add_argument('--checkpoint-output',type=Path);p.add_argument('--budget',type=int,default=250000);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    data=json.loads(a.source.read_text());profile={**data['profile'],'seed':a.seed};old=deepcopy(data['checkpoint'])
    if a.condition=='cold':checkpoint=None
    elif a.condition=='current':checkpoint=old
    else:
        backend=seed_learner(profile,old['memory']['baseline'])
        checkpoint=dict(configuration=old['configuration'],protocol=old['protocol'],learner=backend,steps=0,seconds=0,memory=deepcopy(old['memory']))
    t=AcademyTrainer(profile,'oval-1',checkpoint,balanced=True,batched=True)
    t.learner.rng=np.random.default_rng(a.seed+39001)
    start=t.steps;initial_eval_seconds=t.state.get('evaluationSeconds',0.);begin=time.monotonic();trace=[];last=None;last_gen=-1
    while t.steps-start<a.budget:
        t.tick()
        level=t.evo_plan.data['level'];generation=t.evo_plan.data['generations']
        if level!=last or generation>=last_gen+10:
            row=dict(steps=t.steps-start,level=level,generation=generation,seconds=time.monotonic()-begin,
                lastCheck=t.state['evaluations'][-1]['candidate']['valid'] if t.state['evaluations'] else None,
                selection=t.metric)
            trace.append(row);last=level;last_gen=generation
            print(json.dumps(dict(condition=a.condition,seed=a.seed,**row)),flush=True)
        if time.monotonic()-begin>900:raise RuntimeError('Trial budget not completed within diagnostic deadline')
    trained=time.monotonic()-begin;checkpoint=t.checkpoint(trained)
    if a.checkpoint_output:a.checkpoint_output.write_text(json.dumps(dict(profile=profile,checkpoint=checkpoint),allow_nan=False))
    policy=Policy(t.learner.candidate_policy());cases=[]
    for level in (3,4,5,7,8,10):
        for index in range(4):
            seed=9900000+level*64+index
            scenario=stage_scenario('oval-1',level,seed)
            e=Episode('oval-1',STAGES[level][0],seed,protocol='driving-memory-1',scenario=scenario,reward_spec=specification(profile),single_lap=True)
            while not e.reason:e.step(policy.act(e.observations(),world=e.world,index=0))
            cases.append(dict(level=level,seed=seed,reason=e.reason,progress=e.valid_progress,seconds=e.age))
    result=dict(condition=a.condition,seed=a.seed,budget=a.budget,steps=t.steps-start,trainedSeconds=trained,
        level=t.evo_plan.data['level'],generations=t.evo_plan.data['generations'],trace=trace,evaluationSteps=t.evo_plan.data.get('evaluationSteps'),evaluationSeconds=t.state.get('evaluationSeconds',0.)-initial_eval_seconds,evaluationSecondsLifetime=t.state.get('evaluationSeconds',0.),evaluationCounterScope='Stage-check steps; evaluator time excludes memory Reviews',
        epoch=t.state['epochStats'],checks=[{k:r[k] for k in ('stage','candidate')} for r in t.state['evaluations'] if 'stage' in r],
        heldOut=cases,scope='Private copy; trained model not installed; fixed training transitions, evaluation cost reported separately')
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('condition','seed','steps','trainedSeconds','level','generations')}),flush=True)
if __name__=='__main__':main()
