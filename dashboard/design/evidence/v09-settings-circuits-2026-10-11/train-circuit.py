"""Fresh/weight-transfer comparison, real evolution policies on the new track."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import argparse,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from game_store import default_profile
from game_learning import Evolution
from game_simulation import World
from game_curriculum import initial_state,pace_weight,Evaluation,consider
from game_catalog import scope_hash

def run(seed,transfer,generations,budget=0):
    if budget and budget%32:raise ValueError('Budget must be divisible by population 32')
    profile=default_profile(seed);learner=Evolution(profile);state=initial_state()
    if transfer:
        source=json.loads(Path(__file__).parents[1].joinpath('v09-game-settings-pace-2026-10-11','learning-seed-'+str(seed)+'.json').read_text())
        if not source['state']['champion']:raise ValueError('Source has no qualified policy')
        weights=np.asarray(source['state']['champion']['policy']['weights'])
        learner.best=weights.copy();learner.population[:8]=weights
    world=World(profile['population'],seed,track_id='technical-1');started=time.monotonic();steps=0;history=[];first=None
    gen=-1
    while steps<budget if budget else gen+1<generations:
        gen+=1
        world.reset();dy,da=world.rng.uniform(-.7,.7),world.rng.uniform(-.08,.08)
        for i in range(world.count):world.perturb(i,dy,da)
        scores=np.zeros(world.count)
        for tick in range(profile['episodeSeconds']*60):
            _,reward,done=world.step(learner.act(world.observations(active_only=True)),pace=pace_weight(state),return_observations=False)
            scores+=reward;steps+=world.count
            if done.all() or (budget and steps>=budget):break
        metric=learner.update(scores);state['updates']+=1;state['phaseUpdates']+=1
        if gen%5==0:
            state['round']+=1;champion=state['champion']
            ev=Evaluation(learner.candidate_policy(),champion['policy'] if champion else None,state['round'],track_id='technical-1')
            while not ev.step():pass
            result,old=ev.results();promoted,changed,proof=consider(state,learner.candidate_policy(),result,old,ev.scenarios,scope_hash('technical-1'),profile)
            if changed:learner.change_reward()
            if state['champion'] and first is None:first={'generation':gen+1,'steps':steps,'seconds':time.monotonic()-started}
            record={'seed':seed,'transfer':transfer,'generation':gen+1,'steps':steps,'valid':result['valid'],'median':result['median'],'promoted':promoted}
            history.append(record);print(json.dumps(record),flush=True)
        # Equal generation caps, not equal transition budgets: retired batches
        # consume fewer steps. Report both; this does not establish causality.
    policy=state['champion']['policy'] if state['champion'] else learner.policy()
    final=Evaluation(policy,round_number=100000+seed,track_id='technical-1')
    while not final.step():pass
    heldout=final.results()[0]
    oval=Evaluation(policy,round_number=100000+seed)
    while not oval.step():pass
    record={'seed':seed,'transfer':transfer,'generations':gen+1,'steps':steps,'commonStepBudget':budget,'stepUnit':'population times World.step calls, including retired slots','wallSeconds':time.monotonic()-started,
            'profile':profile,'state':state,'policy':policy,'history':history,'firstQualification':first,
            'heldout':heldout,'ovalRetention':oval.results()[0],
            'scope':'Actual learned policies, independent held-out seeds >=1000000. No reference controller overrides actions.'}
    Path(__file__).parent.joinpath('matched' if budget else '.',('transfer-' if transfer else 'fresh-')+str(seed)+'.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'seed':seed,'transfer':transfer,'finished':True,'heldout':heldout['valid'],'seconds':record['wallSeconds']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,required=True);p.add_argument('--generations',type=int,default=60);p.add_argument('--transfer',action='store_true')
    p.add_argument('--steps-budget',type=int,default=0)
    a=p.parse_args();run(a.seed,a.transfer,a.generations,a.steps_budget)
