from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,os
r=Path('/home/giuseppe/Documenti/Workspace/SmartPC/dashboard/design/evidence/v09-timing-improvements-2026-10-16');probe=r.parent/'v09-residual-implementation-2026-10-16/train_probe.py'
def run(seed):
 with (r/f'tactic-{seed}.log').open('w') as f:
  subprocess.run(['/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(probe),'--source','/tmp/smartpc-rc21-study/dashboard','--method','residual_tactic','--seed',str(seed),'--decisions','16384','--output',str(r/f'tactic-{seed}.json')],env=dict(os.environ,OPENBLAS_NUM_THREADS='1'),stdout=f,stderr=subprocess.STDOUT,check=True)
 print('Seed '+str(seed)+' complete',flush=True)
with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(run,range(11,16)))
