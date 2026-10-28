"""Exclusive native graphics qualification; restores the installed service in finally."""
from pathlib import Path
import json,os,subprocess,time
H=Path('/var/lib/smartpc-dashboard')
P=H/'aquarium-proof-20261025'
PY=H/'game-runtime/bin/python'
B=P/'dashboard'
config=H/'.config/SmartPC'
import hashlib
before={str(p.relative_to(config)):hashlib.sha256(p.read_bytes()).hexdigest() for p in config.rglob('*') if p.is_file()}
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
results=[]
commands=[('base',[]),('functional',['--theme','functional']),('apple',['--theme','apple']),('rig6',['--benchmark-only','--theme','apple','--seconds','40']),('sprite6',['--benchmark-only','--theme','apple','--sprite','--seconds','40']),('rig16',['--benchmark-only','--theme','apple','--population','16','--seconds','20'])]
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 for name,extra in commands:
  out=P/'native'/name;out.mkdir(parents=True,exist_ok=True)
  cmd=['runuser','-u','smartpc','--','env','HOME='+str(H),'QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1',str(PY),str(B/'check_aquarium_ui.py'),'--output',str(out),'--bundle',str(P/'theme-projects/apple-calm/bundle'),*extra]
  subprocess.run(['chown','-R','smartpc:smartpc',str(out)],check=True)
  with (out/'run.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=160)
  assert r.returncode==0,(name,r.returncode,(out/'run.log').read_text()[-2500:])
  report=json.loads((out/'report.json').read_text());results.append({k:v for k,v in report.items() if k not in ('rawIntervalsMs',)})
  print(name,report['callbacksPerSecond'],report['p95Ms'],report['near60SoftwareGate'],flush=True)
  (P/'native-progress.json').write_text(json.dumps(results,indent=2)+'\n')
finally:
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 after={str(p.relative_to(config)):hashlib.sha256(p.read_bytes()).hexdigest() for p in config.rglob('*') if p.is_file()}
 (P/'native-receipt.json').write_text(json.dumps({'results':results,'sameBoot':boot==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'preferencesPreserved':before==after,'serviceRestarted':True},indent=2)+'\n')
