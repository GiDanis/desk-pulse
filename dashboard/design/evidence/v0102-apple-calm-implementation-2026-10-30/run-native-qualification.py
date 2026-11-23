"""Native EGLFS candidate checks; always restore the installed service."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,time
p=argparse.ArgumentParser();p.add_argument("--case",action="append");chosen=p.parse_args().case
W=Path(__file__).resolve().parent;S=W/'candidate-source';D=S/'dashboard';PY=Path('/var/lib/smartpc-dashboard/game-runtime/bin/python')
E=W/'eglfs';E.mkdir(exist_ok=True)
env=dict(os.environ,QT_QPA_PLATFORM='eglfs',QT_QPA_EGLFS_INTEGRATION='eglfs_kms',QT_QPA_EGLFS_KMS_CONFIG='/etc/smartpc/eglfs-kms.json',QT_QPA_EGLFS_HIDECURSOR='1',QSG_RHI_BACKEND='opengl',QT_DISABLE_SHADER_DISK_CACHE='1',LD_PRELOAD=str(D/'libsmartpc_egl_context_bridge.so'),SMARTPC_AQUARIUM_RENDERER='3d',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
for k in ['QT_QUICK_BACKEND','QSG_INFO','QSG_RHI_PIPELINE_CACHE_LOAD','QSG_RHI_PIPELINE_CACHE_SAVE']:env.pop(k,None)
def run(label,args,extra=None):
 with (E/(label+'.log')).open('w') as output:
  completed=subprocess.run([str(PY),*map(str,args)],cwd=S,env={**env,**(extra or {})},stdout=output,stderr=subprocess.STDOUT,timeout=900)
 assert completed.returncode==0,(label,completed.returncode)
 print('PASS '+label,flush=True)
record={'baselineManifestSha256':hashlib.sha256(Path('/opt/smartpc/dashboard/release-manifest.json').read_bytes()).hexdigest(),'candidateManifestSha256':hashlib.sha256((W/'runtime/release-manifest.json').read_bytes()).hexdigest(),'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'scope':'Synthetic isolated native tests, no user data mutation; service temporarily stopped','cases':[]}
subprocess.run(['sudo','-n','systemctl','stop','smartpc-dashboard'],check=True)
try:
 jobs=[
  ('day',[S/'theme-projects/apple-calm/tools/verify_main.py','--all','--palette','day','--output',E/'day'],None),
  ('night',[S/'theme-projects/apple-calm/tools/verify_main.py','--palette','night','--output',E/'night'],None),
  ('readability-day',[S/'theme-projects/apple-calm/tools/verify_readability.py','--output',E/'readability-day'],None),
  ('readability-night',[S/'theme-projects/apple-calm/tools/verify_readability.py','--palette','night','--output',E/'readability-night'],None),
  ('scenes',[S/'theme-projects/apple-calm/tools/verify_readability.py','--scenes-only','--output',E/'scenes'],None),
  ('motion',[S/'scripts/benchmark-calm-motion.py','--seconds','10','--output',E/'motion.json'],{'QSG_INFO':'1'})]
 for label,args,extra in jobs:
  if chosen and label not in chosen:continue
  run(label,args,extra);record['cases'].append(label)
 record['status']='passed'
finally:
 subprocess.run(['sudo','-n','systemctl','start','smartpc-dashboard'],check=True)
 record['serviceRestarted']=True;record['sameBoot']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()==record['bootId']
 (E/'qualification.json').write_text(json.dumps(record,indent=2)+'\n')
