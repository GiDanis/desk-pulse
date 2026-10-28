from pathlib import Path
from copy import deepcopy
import json,sys,time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
ROOT=Path('/home/giuseppe/Documenti/Workspace/SmartPC');sys.path.insert(0,str(ROOT/'dashboard'))
from game_residual import profile,snapshot
from check_game_residual_gates import run
R=ROOT/'dashboard/design/evidence/v09-timing-improvements-2026-10-16'
learned=json.loads((R/'tactic-11.json').read_text())['champion'];pace=deepcopy(learned)
w=np.array(pace['weights']);w[(90+1)*pace['hidden']:].reshape(pace['hidden']+1,2)[:,0]=0;pace['weights']=w.tolist()
def evaluate(job):
 name,policy=job;rows=[dict(run(policy,'oval-1','corner',seed,spatial_rules=True),seed=seed) for seed in range(95201,95211)]
 result=dict(name=name,seedBank=[95201,95210],kind='development-ablation-no-training',policy=policy,valid=sum(r['success'] for r in rows),total=len(rows),results=rows)
 (R/f'ablation-{name}.json').write_text(json.dumps(result,indent=2)+'\n');print(name,result['valid'],flush=True)
with ProcessPoolExecutor(max_workers=3) as pool:list(pool.map(evaluate,[('base',snapshot(profile(1,'race_master'))),('pace-only',pace),('line-and-pace',learned)]))
