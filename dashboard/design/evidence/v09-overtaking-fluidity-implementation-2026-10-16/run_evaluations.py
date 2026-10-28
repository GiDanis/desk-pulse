from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,os,argparse,time,json
p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=5);p.add_argument('--bank',choices=('selection','final','final-v2','development'),required=True);p.add_argument('--variant',choices=('old','new','capability','all'),default='all');a=p.parse_args();r=Path(__file__).resolve().parent
variants=('old','new','capability') if a.variant=='all' else (a.variant,)
jobs=[(v,s) for v in variants for s in range(21,26)]
if a.variant in ('all','new'):jobs+=[('base',0)]
def run(job):
 v,s=job;out=r/f'eval-{a.bank}-{v}-{s}.json'
 if out.exists():return
 cmd=['nice','-n','10','/home/giuseppe/.cache/smartpc-population-py312/bin/python',str(r/'evaluate_bank.py'),'--source','/tmp/smartpc-rc22-overtake-study/dashboard','--bank',str(r/f'bank-{a.bank}.json'),'--output',str(out)]
 if v!='base':
  source=r/f'train-{v}-{s}.json';deadline=time.monotonic()+3600
  while True:
   try:json.loads(source.read_text());break
   except (OSError,ValueError):
    if time.monotonic()>deadline:raise RuntimeError('Missing training input '+str(source))
    time.sleep(5)
  cmd+=['--input',str(source)]
 with (r/f'eval-{a.bank}-{v}-{s}.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True,env=dict(os.environ,OPENBLAS_NUM_THREADS='1'))
 print('Complete '+a.bank+' '+v+' '+str(s),flush=True)
with ThreadPoolExecutor(max_workers=a.workers) as pool:list(pool.map(run,jobs))
