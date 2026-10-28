from pathlib import Path
import concurrent.futures,subprocess,os,json
p=Path(__file__).parent
jobs=[(m,seed) for m,first in [('residual_ppo',2),('residual_sac',3),('residual_td3',4)] for seed in (first,31,32,33,34)]
def run(job):
 m,seed=job
 with (p/f'mixture-final-{m}-{seed}.log').open('w') as log:
  subprocess.run(['/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(p/'train_school.py'),'--method',m,'--seed',str(seed),'--budget','98304','--base',str(p/'school-policy.json'),'--output',str(p/f'mixture-final-{m}-{seed}.json')],env=dict(os.environ,OPENBLAS_NUM_THREADS='1',PYTHONPATH='dashboard'),stdout=log,stderr=subprocess.STDOUT,check=True)
 print(m,seed,'complete',flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(run,jobs))
