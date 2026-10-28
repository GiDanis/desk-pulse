"""Continue copied real checkpoints with the release recipe, never production."""
from pathlib import Path
import concurrent.futures,subprocess,json,os
P=Path(__file__).parent;private=Path('/tmp/smartpc-racing-implementation-private-20261021/snapshot')
meta=json.loads((private/'saved-meta.json').read_text());out=P/'saved-continuations';out.mkdir(exist_ok=True)
def run(d):
    if d['name']=='Maestro' or not d['checkpoint']:return
    profile=json.loads(d['profile']);target=out/(d['name']+'.json')
    with target.with_suffix('.log').open('w') as log:
        subprocess.run(['/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(P/'train_racing.py'),
            '--method',profile['algorithm'],'--seed',str(profile['seed']),'--variant','production',
            '--budget','131072' if profile['algorithm']=='residual_tactic' else '98304',
            '--resume',str(private/'models'/(d['checkpoint']+'.json')),'--output',str(target)],
            env=dict(os.environ,PYTHONPATH='/home/giuseppe/.cache/smartpc-racing-production-reference',OPENBLAS_NUM_THREADS='1'),
            stdout=log,stderr=subprocess.STDOUT,check=True)
    print(d['name'],'continued on copy',flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(run,meta['drivers']))
