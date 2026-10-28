"""Resume only missing quota-interrupted runs, on the exact frozen source."""
from pathlib import Path
import concurrent.futures,subprocess,json,hashlib,os
P=Path(__file__).parent;private=Path('/tmp/smartpc-attack-implementation-20261022');source=private/'final-source'
expected=json.loads((P/'final-source.json').read_text());assert all(hashlib.sha256((source/n).read_bytes()).hexdigest()==h for n,h in expected.items())
active=subprocess.check_output(['ps','-eo','args'],text=True)
jobs=[]
for m in ('residual_ppo','residual_sac','residual_td3','residual_tactic'):
 for s in (741,742,743,744,745):
  for baseline in (False,True):
   name=f'{m}-{s}-'+('baseline' if baseline else 'candidate')
   if (P/'final-cohorts'/(name+'.json')).exists():continue
   if str(private/'final-models'/(name+'.json')) in active:continue
   jobs.append((m,s,baseline,name))
def run(job):
 m,s,baseline,name=job;out=P/'final-cohorts'/(name+'.json')
 with out.with_suffix('.log').open('a') as log:
  cmd=['/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(P/'train.py'),'--method',m,'--seed',str(s),'--coefficient','0','--output',str(out),'--private',str(private/'final-models'/(name+'.json'))]
  if baseline:cmd+=['--baseline']
  r=subprocess.run(cmd,env=dict(os.environ,PYTHONPATH=str(source),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'),stdout=log,stderr=subprocess.STDOUT)
 return dict(name=name,exitCode=r.returncode)
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 for r in pool.map(run,jobs):rows.append(r);(P/'quota-resume-results.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(r),flush=True)
