from pathlib import Path
import sys,json,time,subprocess,os
from concurrent.futures import ProcessPoolExecutor
ROOT=Path('/home/giuseppe/Documenti/Workspace/SmartPC');sys.path.insert(0,str(ROOT/'dashboard'))
from check_game_residual_gates import run
from game_residual import profile,snapshot
R=ROOT/'dashboard/design/evidence/v09-timing-improvements-2026-10-16';old=R.parent/'v09-residual-implementation-2026-10-16'
while not all((R/f'tactic-{s}.json').exists() for s in range(11,16)):time.sleep(3)
jobs=[('base',snapshot(profile(1,'race_master')))]
for seed in range(11,16):
 for tag,path in [('rc20',old/f'accepted-tactic-{seed}.json'),('rc21',R/f'tactic-{seed}.json')]:
  data=json.loads(path.read_text());jobs.append((f'{tag}-{seed}',data['champion']))
def evaluate(job):
 name,policy=job;start=time.monotonic();rows=[]
 for phase in ('overtake','corner','defend'):
  for seed in range(94101,94121):rows.append(dict(run(policy,'oval-1',phase,seed,spatial_rules=True),phase=phase,seed=seed))
  print(name,phase,'complete',flush=True)
 groups={p:dict(valid=sum(r['success'] for r in rows if r['phase']==p),total=20,contacts=sum(r['contacts'] for r in rows if r['phase']==p)) for p in ('overtake','corner','defend')}
 result=dict(name=name,policy=policy,seedBank=[94101,94120],rules='spatial-rules-2',trainingTransitions=0,groups=groups,results=rows,seconds=time.monotonic()-start)
 (R/f'heldout-{name}.json').write_text(json.dumps(result,indent=2)+'\n');print(name,groups,flush=True)
with ProcessPoolExecutor(max_workers=3) as pool:list(pool.map(evaluate,jobs))
