"""One exact final-source replication for each method, before delivery."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json,os,hashlib
R=Path(__file__).resolve().parent;S=Path('/tmp/smartpc-incentives-final-project/dashboard')
script=R.parent/'v09-overtaking-fluidity-implementation-2026-10-16/train_budget.py'
def run(method):
    out=R/f'reproduced-{method}-31.json'
    with out.with_suffix('.log').open('w') as log:
        subprocess.run(['nice','-n','10','/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(script),'--source',str(S),'--method',method,'--seed','31','--budget','49152','--output',str(out)],env=dict(os.environ,OPENBLAS_NUM_THREADS='1'),stdout=log,stderr=subprocess.STDOUT,check=True)
    actual=json.loads(out.read_text());reference=json.loads((R/('dev-prior-31.json' if method=='residual_ppo' else f'new-{method}-31.json')).read_text())
    assert actual['champion']==reference['champion'],method+' champion differs'
    assert actual['candidate']==reference['candidate'],method+' actor differs'
    assert actual['stats']==reference['stats'],method+' statistics differ'
    assert actual['recipe']==reference['recipe'],method+' recipe differs'
    return method
with ThreadPoolExecutor(max_workers=4) as pool:methods=list(pool.map(run,['residual_ppo','residual_sac','residual_td3','residual_tactic']))
(R/'final-source-reproduction.json').write_text(json.dumps(dict(status='passed',methods=methods,seed=31,budget=49152,exactChampionAndActor=True,
    manifestSha256=hashlib.sha256((S/'release-manifest.json').read_bytes()).hexdigest()),indent=2)+'\n')
print('Final source exactly reproduced all four methods',flush=True)
