"""Measure worker components with timers; do not alter installed files."""
import importlib.util,json,sys,time
from pathlib import Path
spec=importlib.util.spec_from_file_location('resource_audit','/tmp/smartpc-resource-audit.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
def timed_worker(command,frames,root,request):
 from game_academy_trainer import AcademyTrainer
 from game_worker import worker_main
 samples={'frame':[],'tick':[]}
 for name,key in (('frame','frame'),('tick','tick')):
  original=getattr(AcademyTrainer,name)
  def timed(*args,_original=original,_key=key,**kwargs):
   start=time.perf_counter()
   try:return _original(*args,**kwargs)
   finally:
    samples[_key].append((time.perf_counter()-start)*1000)
    if _key=='frame' and len(samples[_key])==64:
     Path('/tmp/smartpc-preview-components.json').write_text(json.dumps(samples))
  setattr(AcademyTrainer,name,timed)
 try:worker_main(command,frames,root,request)
 finally:Path('/tmp/smartpc-preview-components.json').write_text(json.dumps(samples))
audit.worker_main=None
# worker_case imports its target locally; replace that module function only in
# this process. The spawned timed wrapper imports the real installed target.
def main():
 import game_worker,subprocess
 game_worker.worker_main=timed_worker
 Path('/tmp/smartpc-preview-components.json').unlink(missing_ok=True)
 service=int(subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','MainPID','--value']));gui=int(subprocess.check_output(['ps','--ppid',str(service),'-o','pid=']).decode().split()[0])
 r=audit.worker_case(gui,'impara');r['componentMs']=json.loads(Path('/tmp/smartpc-preview-components.json').read_text());Path('/tmp/smartpc-preview-audit.json').write_text(json.dumps(r,indent=2))
if __name__=='__main__':main()
