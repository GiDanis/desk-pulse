"""Freeze sources and run complete paired development cohorts."""
from pathlib import Path
import concurrent.futures,subprocess,json,shutil,os
P=Path(__file__).parent;private=Path('/tmp/smartpc-attack-implementation-20261022');source=private/'source'
source.mkdir(parents=True,exist_ok=True)
root=P.parents[2]
for f in root.iterdir():
 if f.is_file() and (f.suffix in ('.py','.so') or f.name.startswith('game-') and f.suffix=='.json'):shutil.copy2(f,source/f.name)
(P/'development').mkdir(exist_ok=True)
jobs=[(seed,coefficient,baseline) for seed in (721,722) for coefficient,baseline in ((0.,True),(0.,False),(.25,False),(.5,False))]
def run(job):
 seed,coefficient,baseline=job;name=f'td3-{seed}-'+('baseline' if baseline else str(coefficient));out=P/'development'/(name+'.json')
 with out.with_suffix('.log').open('w') as log:
  cmd=['/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(P/'train.py'),'--method','residual_td3','--seed',str(seed),'--coefficient',str(coefficient),'--output',str(out),'--private',str(private/'models'/(name+'.json'))]
  if baseline:cmd+=['--baseline']
  result=subprocess.run(cmd,env=dict(os.environ,PYTHONPATH=str(source),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'),stdout=log,stderr=subprocess.STDOUT)
 return dict(name=name,exitCode=result.returncode)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for result in pool.map(run,jobs):print(json.dumps(result),flush=True)
