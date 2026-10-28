"""Four additional held-out slots; per-result locks prevent duplicate work."""
from pathlib import Path
import concurrent.futures,subprocess,json,os,time
P=Path(__file__).parent;private=Path('/tmp/smartpc-attack-implementation-20261022');out=P/'heldout';out.mkdir(exist_ok=True)
active=subprocess.check_output(['ps','-eo','args'],text=True)
jobs=[f'{m}-{s}-{v}' for m in ('residual_ppo','residual_sac','residual_td3','residual_tactic') for s in (741,742,743,744,745) for v in ('candidate','baseline')]
jobs=[n for n in jobs if not (out/(n+'.json')).exists() and str(out/(n+'.json')) not in active]
def run(name):
 while not (P/'final-cohorts'/(name+'.json')).exists():time.sleep(5)
 with (out/(name+'-extra.log')).open('w') as log:
  r=subprocess.run(['/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(P/'evaluate_final.py'),'--checkpoint',str(private/'final-models'/(name+'.json')),'--output',str(out/(name+'.json'))],env=dict(os.environ,PYTHONPATH=str(private/'evaluation-source'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'),stdout=log,stderr=subprocess.STDOUT)
 return dict(name=name,exitCode=r.returncode)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for row in pool.map(run,jobs):print(json.dumps(row),flush=True)
