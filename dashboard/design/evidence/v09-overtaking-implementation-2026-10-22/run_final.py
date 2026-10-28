"""Complete five-seed paired cohorts for every actual learning method."""
from pathlib import Path
import concurrent.futures,subprocess,json,shutil,os,hashlib,time
P=Path(__file__).parent;private=Path('/tmp/smartpc-attack-implementation-20261022');source=private/'final-source'
source.mkdir(parents=True,exist_ok=True);root=P.parents[2]
for f in root.iterdir():
 if f.is_file() and (f.suffix in ('.py','.so') or f.name.startswith('game-') and f.suffix=='.json'):shutil.copy2(f,source/f.name)
(P/'final-cohorts').mkdir(exist_ok=True)
(P/'final-source.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in source.iterdir() if f.is_file()},indent=2)+'\n')
jobs=[(method,seed,baseline) for method in ('residual_ppo','residual_sac','residual_td3','residual_tactic') for seed in (741,742,743,744,745) for baseline in (False,True)]
def run(job):
 method,seed,baseline=job;name=f'{method}-{seed}-'+('baseline' if baseline else 'candidate');out=P/'final-cohorts'/(name+'.json')
 if out.exists():return dict(name=name,exitCode=0,reused=True)
 with out.with_suffix('.log').open('a') as log:
  cmd=['/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(P/'train.py'),'--method',method,'--seed',str(seed),'--coefficient','0','--output',str(out),'--private',str(private/'final-models'/(name+'.json'))]
  if baseline:cmd+=['--baseline']
  result=subprocess.run(cmd,env=dict(os.environ,PYTHONPATH=str(source),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'),stdout=log,stderr=subprocess.STDOUT)
 return dict(name=name,exitCode=result.returncode)
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 for r in pool.map(run,jobs):
  rows.append(r);(P/'final-progress.json').write_text(json.dumps(dict(total=len(jobs),rows=rows),indent=2)+'\n');print(json.dumps(r),flush=True)
