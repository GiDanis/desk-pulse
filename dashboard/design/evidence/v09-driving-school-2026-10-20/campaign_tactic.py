from pathlib import Path
import concurrent.futures,subprocess,os
p=Path(__file__).parent
def run(seed):
 with (p/f'mixture-final-residual_tactic-{seed}.log').open('w') as out:
  subprocess.run(['/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(p/'train_school.py'),'--method','residual_tactic','--seed',str(seed),'--budget','131072','--base',str(p/'traffic-policy.json'),'--output',str(p/f'mixture-final-residual_tactic-{seed}.json')],env=dict(os.environ,OPENBLAS_NUM_THREADS='1',PYTHONPATH='dashboard'),stdout=out,stderr=subprocess.STDOUT,check=True)
 print('Tattico',seed,'complete',flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(run,(5,31,32,33,34)))
