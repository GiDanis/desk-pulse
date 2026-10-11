"""Five fresh evolution seeds: continued training, paired promotion and held-out laps."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import argparse,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from game_learning import Evolution
from game_store import default_profile
from game_simulation import World
from game_curriculum import initial_state,Evaluation,consider,pace_weight
from game_catalog import scope_hash
parser=argparse.ArgumentParser();parser.add_argument('--seed',type=int,required=True);parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
p=default_profile(args.seed);learner=Evolution(p);state=initial_state();world=World(p['population'],p['seed'])
started=time.monotonic();first=None;history=[];steps=0
budget=json.loads(Path(__file__).with_name('learning-seed-'+str(args.seed)+'.json').read_text())['steps'] if args.baseline else None
for gen in range(100):
 world.reset();dy,da=world.rng.uniform(-.7,.7),world.rng.uniform(-.08,.08)
 world.state[:,1]+=dy;world.state[:,2]+=da;scores=np.zeros(p['population'])
 for tick in range(3600):
  _,r,done=world.step(learner.act(world.observations()),pace=0 if args.baseline else pace_weight(state));scores+=r;steps+=len(scores)
  if done.all():break
 metric=learner.update(scores);candidate=learner.candidate_policy();history.append({**metric,'phase':state['phase'],'pace':pace_weight(state),'steps':steps})
 old_weight=pace_weight(state);state['updates']+=1;state['phaseUpdates']+=1
 if not args.baseline and old_weight!=pace_weight(state):learner.change_reward()
 if gen%5==0:
  state['round']+=1;champ=state['champion'];ev=Evaluation(candidate,champ['policy'] if champ else None,state['round'])
  while not ev.step():pass
  candidate_result,champ_result=ev.results()
  promoted,changed,proof=consider(state,candidate,candidate_result,champ_result,ev.scenarios,scope_hash(),p)
  if first is None and state['champion']:first=state['champion']['policy']
  if changed and not args.baseline:learner.change_reward()
  print(json.dumps({'seed':args.seed,'generation':gen+1,'phase':state['phase'],'valid':candidate_result['valid'],'median':candidate_result['median'],'promoted':promoted}),flush=True)
 if args.baseline and steps>=budget:break
 if not args.baseline and state['phase']=='pace' and state['phaseUpdates']>=25:break
comparison=None
if state['champion'] and first:
 final=Evaluation(state['champion']['policy'],first,100000+args.seed)
 while not final.step():pass
 a,b=final.results();comparison={'scenarios':final.scenarios,'final':a,'firstQualified':b,'medianGain':b['median']-a['median'] if a['median'] and b['median'] else None}
record={'experiment':'control_reward' if args.baseline else 'progressive_reward','transitionBudget':budget,'seed':args.seed,'profile':p,'state':state,'history':history,'comparison':comparison,'steps':steps,'wallSeconds':time.monotonic()-started,
        'scope':'Fresh training with own random networks; paired selection windows; held-out scenarios >=1000000; no driving controller for pilots'}
Path(__file__).with_name(('learning-baseline-seed-' if args.baseline else 'learning-seed-')+str(args.seed)+'.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'seed':args.seed,'done':True,'seconds':record['wallSeconds'],'comparison':comparison}),flush=True)
