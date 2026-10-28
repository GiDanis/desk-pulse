from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import subprocess,sys,os,json,time
r=Path(__file__).resolve().parent;target=r/'final-bank.json'
if not target.exists():target.write_text(json.dumps(dict(version='direct-final-1',solo=[820001,820002,820003,820004,820005],traffic=dict(overtake=[821001,821002,821003],corner=[822001,822002,822003],defend=[823001,823002,823003])),indent=2)+'\n')
def run(job):
 m,s=job;name=f'final-{m}-{s}'
 with (r/(name+'.log')).open('w') as out:
  subprocess.run([sys.executable,str(r/'train.py'),'--seed',str(s),'--method',m,'--base',str(r/'product-base-policy.json'),'--output',str(r/(name+'.json'))],stdout=out,stderr=subprocess.STDOUT,check=True)
 return name
jobs=[(m,s) for m in ('residual_ppo','residual_sac','residual_td3','residual_tactic') for s in range(31,36)]
results=[];errors=[]
with ThreadPoolExecutor(max_workers=8) as pool:
 for f in as_completed([pool.submit(run,j) for j in jobs]):
  try:results.append(f.result());print('Completed',results[-1],flush=True)
  except Exception as e:errors.append(str(e));print('FAILED',str(e),flush=True)
  (r/'campaign-status.json').write_text(json.dumps(dict(completed=results,errors=errors,total=len(jobs)),indent=2)+'\n')
if errors:raise RuntimeError(errors)
