from pathlib import Path
import os,subprocess,concurrent.futures,json,hashlib
p=Path(__file__).resolve().parent
methods=['residual_ppo','residual_sac','residual_td3','residual_tactic']
def run(method):
 output=p/('release-reproduced-'+method+'-31.json')
 with (p/('release-reproduced-'+method+'-31.log')).open('w') as log:
  subprocess.run(['/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(p/'train.py'),'--method',method,'--seed','31','--base',str(p/('tactical-base-policy.json' if method=='residual_tactic' else 'product-base-policy.json')),'--output',str(output)],env=dict(os.environ,PYTHONPATH='dashboard',OPENBLAS_NUM_THREADS='1'),stdout=log,stderr=subprocess.STDOUT,check=True)
 a=json.loads((p/('final-'+method+'-31.json')).read_text());b=json.loads(output.read_text())
 keys=['champion','candidate','stats','physicalSteps','decisions','updates','results']
 equal={k:a[k]==b[k] for k in keys};assert all(equal.values()),(method,equal)
 print(method,'exact',flush=True);return dict(method=method,equal=equal)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:results=list(executor.map(run,methods))
sourceHashes=json.loads((p/'release-reproduced-residual_ppo-31.json').read_text())['sourceHashes']
(p/'final-source-reproduction.json').write_text(json.dumps(dict(status='passed',exactChampionAndActor=True,results=results,sourceHashes=sourceHashes,scope='Four exact seed-31 full-budget repeats from shipped A/B neural bases; current source'),indent=2)+'\n')
