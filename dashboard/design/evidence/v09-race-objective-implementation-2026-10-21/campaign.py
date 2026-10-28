from pathlib import Path
import concurrent.futures,subprocess,os,argparse,json,time
p=argparse.ArgumentParser();p.add_argument('--variants',nargs='+',default=['baseline','reward-only'])
p.add_argument('--workers',type=int,default=6);p.add_argument('--source',default=None)
p.add_argument('--methods',nargs='+');p.add_argument('--seeds',nargs='+',type=int);p.add_argument('--budget',type=int)
p.add_argument('--label',default='');a=p.parse_args()
root=Path(__file__).parent
jobs=[(v,m,s) for v in a.variants for m,first in [('residual_ppo',2),('residual_sac',3),('residual_td3',4),('residual_tactic',5)] for s in (a.seeds or (first,31,32,33,34))]
if a.methods:jobs=[job for job in jobs if job[1] in a.methods]
def run(job):
    variant,method,seed=job;dest=root/a.label/variant;dest.mkdir(exist_ok=True,parents=True);output=dest/f'{method}-{seed}.json'
    if output.exists():return
    source=a.source or ('/home/giuseppe/.cache/smartpc-rc26-race-objective-reference' if variant=='baseline' else '/home/giuseppe/.cache/smartpc-racing-reward-only-reference')
    with output.with_suffix('.log').open('w') as log:
        subprocess.run(['/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(root/'train_racing.py'),
            '--method',method,'--seed',str(seed),'--variant',variant,'--budget',str(a.budget or (131072 if method=='residual_tactic' else 98304)),
            '--output',str(output)],env=dict(os.environ,PYTHONPATH=source,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'),
            stdout=log,stderr=subprocess.STDOUT,check=True)
    d=json.loads(output.read_text());print(variant,method,seed,'done',round(d['learningSeconds'],1),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:list(pool.map(run,jobs))
