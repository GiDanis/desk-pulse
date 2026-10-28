from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,os
r=Path(__file__).resolve().parent
jobs=[(m,s) for s in range(21,26) for m in ('residual_ppo','residual_sac','residual_td3')]
def run(job):
 m,s=job
 with (r/f'method-{m}-{s}.log').open('w') as stream:
  subprocess.run(['nice','-n','10','/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(r/'train_budget.py'),'--source','/tmp/smartpc-rc22-overtake-study/dashboard','--method',m,'--seed',str(s),'--budget','49152','--output',str(r/f'method-{m}-{s}.json')],env=dict(os.environ,OPENBLAS_NUM_THREADS='1'),stdout=stream,stderr=subprocess.STDOUT,check=True)
 print('Complete '+m+' '+str(s),flush=True)
with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(run,jobs))
