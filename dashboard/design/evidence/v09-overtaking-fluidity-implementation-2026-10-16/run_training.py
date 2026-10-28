from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,os
r=Path(__file__).resolve().parent
jobs=[(revision,seed) for seed in range(21,26) for revision in ('old','new')]
def run(job):
 revision,seed=job;source='/tmp/smartpc-rc21-overtake-baseline/dashboard' if revision=='old' else '/tmp/smartpc-rc22-overtake-study/dashboard'
 with (r/f'train-{revision}-{seed}.log').open('w') as stream:
  subprocess.run(['/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(r/'train_budget.py'),'--source',source,'--seed',str(seed),'--output',str(r/f'train-{revision}-{seed}.json')],env=dict(os.environ,OPENBLAS_NUM_THREADS='1'),stdout=stream,stderr=subprocess.STDOUT,check=True)
 print('Complete '+revision+' '+str(seed),flush=True)
with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(run,jobs))
