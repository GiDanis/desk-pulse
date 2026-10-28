from pathlib import Path
import subprocess,concurrent.futures,os,json,time
p=Path(__file__).parent
jobs=[('residual_ppo',2,98304),('residual_sac',3,98304),('residual_td3',4,98304),('residual_tactic',5,131072)]
def run(job):
 method,seed,budget=job;name=f'reproduced-{method}-{seed}'
 if (p/(name+'.json')).exists():return method,seed
 with (p/(name+'.log')).open('w') as out:
  subprocess.run(['/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(p/'train_school.py'),'--method',method,'--seed',str(seed),'--budget',str(budget),'--base',str(p/('traffic-policy.json' if method=='residual_tactic' else 'school-policy.json')),'--output',str(p/(name+'.json'))],env=dict(os.environ,OPENBLAS_NUM_THREADS='1',PYTHONPATH='dashboard'),stdout=out,stderr=subprocess.STDOUT,check=True)
 print(method,'reproduced',flush=True)
 return method,seed
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(run,jobs))
rows=[];hashes=None
for method,seed,budget in jobs:
 d=json.loads((p/f'reproduced-{method}-{seed}.json').read_text());original=p/f'mixture-final-{method}-{seed}.json'
 deadline=time.monotonic()+1200
 while not original.exists():
  assert time.monotonic()<deadline,original
  time.sleep(3)
 old=json.loads(original.read_text())
 keys=['champion','candidate','stats','evaluations','physicalSteps','decisions','updates','results','recipe']
 same={k:d[k]==old[k] for k in keys};assert all(same.values()),same
 if hashes is None:hashes=d['sourceHashes']
 assert hashes==d['sourceHashes']
 rows.append(dict(method=method,seed=seed,budget=budget,exact=same))
(p/'final-source-reproduction.json').write_text(json.dumps(dict(status='passed',exactChampionAndActor=True,sourceHashes=hashes,rows=rows),indent=2)+'\n')
