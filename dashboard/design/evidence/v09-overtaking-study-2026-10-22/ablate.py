"""Causal expert ablation on copies. No actuator override, no proposed release."""
from copy import deepcopy
import json
from probe import run,HERE
from game_direct_bootstrap import base_asset
from game_neural_mixture import EXPERT_SIZE
p=deepcopy(base_asset('driving')['policy'])
p['weights'][EXPERT_SIZE:2*EXPERT_SIZE]=p['weights'][:EXPERT_SIZE]
rows=[]
for seed in (961101,961102,961103):
 r=run('Base driving','solo-expert-in-both-branches',p,seed,True);rows.append(r)
 print(seed,'passes',r['passes'],'v',r['meanSpeedAfter5'],'contacts',r['contacts'],'limits',r['limits'],'reason',r['reason'],flush=True)
 (HERE/'expert-ablation.json').write_text(json.dumps(dict(status='diagnostic-only',productionChanges=False,newTraining=False,teacherAtLearnerInference=False,intervention='Copied neural expert A into B on a disposable factory policy; original gate and actual traffic observations retained',scope='Isolates conservative traffic expert effects; does not validate a replacement or trained overtaking',rows=rows),indent=2)+'\n')
