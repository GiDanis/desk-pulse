from pathlib import Path
import concurrent.futures,subprocess,time,os
P=Path(__file__).parent;(P/'supplement').mkdir(exist_ok=True)
names=[f'{m}-{s}-{v}' for m in ('residual_ppo','residual_sac','residual_td3','residual_tactic') for s in range(741,746) for v in ('candidate','baseline')]
def run(n):
 while not (P/'final-cohorts'/(n+'.json')).exists():time.sleep(5)
 with (P/'supplement'/(n+'.log')).open('w') as log:
  r=subprocess.run(['/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(P/'evaluate_extra.py'),n],env=dict(os.environ,PYTHONPATH=str(P.parents[2]),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'),stdout=log,stderr=subprocess.STDOUT)
 return n,r.returncode
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for n,code in pool.map(run,names):print(n,code,flush=True)
