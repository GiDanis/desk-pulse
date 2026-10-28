from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,os
r=Path(__file__).resolve().parent
def run(seed):
 with (r/f'train-capability-{seed}.log').open('w') as f:
  subprocess.run(['/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(r/'train_budget.py'),'--source','/tmp/smartpc-rc22-overtake-study/dashboard','--variant','capability','--seed',str(seed),'--output',str(r/f'train-capability-{seed}.json')],env=dict(os.environ,OPENBLAS_NUM_THREADS='1'),stdout=f,stderr=subprocess.STDOUT,check=True)
 print('Complete capability '+str(seed),flush=True)
with ThreadPoolExecutor(max_workers=5) as pool:list(pool.map(run,range(21,26)))
