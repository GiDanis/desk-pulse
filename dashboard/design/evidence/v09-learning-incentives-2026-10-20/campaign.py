"""Five complete seeds per method/revision, same physical collection budget."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import subprocess,os,time,json
R=Path(__file__).resolve().parent
script=R.parent/'v09-overtaking-fluidity-implementation-2026-10-16/train_budget.py'
sources=dict(old=Path('/tmp/smartpc-incentives-rc23-baseline/dashboard'),new=Path('/tmp/smartpc-incentives-candidate'))
jobs=[(revision,method,seed) for seed in range(31,36) for method in ('residual_ppo','residual_sac','residual_td3','residual_tactic') for revision in ('old','new')]
started=time.monotonic();completed=[];errors=[]
def run(job):
    revision,method,seed=job;name=f'{revision}-{method}-{seed}'
    with (R/(name+'.log')).open('w') as out:
        subprocess.run(['nice','-n','10','/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(script),'--source',str(sources[revision]),'--method',method,'--seed',str(seed),'--budget','49152','--output',str(R/(name+'.json'))],
            env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'),stdout=out,stderr=subprocess.STDOUT,check=True)
    return name
with ThreadPoolExecutor(max_workers=8) as pool:
    futures={pool.submit(run,j):j for j in jobs}
    for f in as_completed(futures):
        try:completed.append(f.result());print('Completed '+completed[-1],flush=True)
        except Exception as e:errors.append(dict(job=futures[f],error=str(e)));print('Failed '+str(futures[f]),flush=True)
        (R/'campaign-status.json').write_text(json.dumps(dict(completed=completed,errors=errors,total=len(jobs),wallSeconds=time.monotonic()-started),indent=2)+'\n')
if errors:raise RuntimeError(errors)
