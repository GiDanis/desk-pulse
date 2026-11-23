"""Exclusive EGLFS acceptance; always bring the production service back up."""
import hashlib,json,subprocess
from pathlib import Path
W=Path('/var/lib/smartpc-dashboard/maintenance-work');D=W/'source/dashboard';PY=Path('/var/lib/smartpc-dashboard/game-runtime/bin/python')
manifest=json.loads((D/'release-manifest.json').read_text());assert manifest['version']=='0.10.1-rc.1'
assert all(hashlib.sha256((D/n).read_bytes()).hexdigest()==h for n,h in manifest['sha256'].items())
base_env=dict(QT_QPA_PLATFORM='eglfs',QT_QPA_EGLFS_INTEGRATION='eglfs_kms',QT_QPA_EGLFS_KMS_CONFIG='/etc/smartpc/eglfs-kms.json',QT_QPA_EGLFS_HIDECURSOR='1',QSG_RHI_BACKEND='opengl',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',HOME='/var/lib/smartpc-dashboard')
rows=[];subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 for theme in ('base','functional','apple'):
  cases=[('aquarium',[str(D/'check_aquarium_ui.py'),'--theme',theme,'--seconds','3','--warmup','2','--bundle',str(W/'source/theme-projects/apple-calm/bundle')]),('main',[str(W/'smoke-main.py'),'--dashboard',str(D),'--theme',theme])]
  for label,command in cases:
   out=W/('native-'+label+'-'+theme);out.mkdir(exist_ok=True);subprocess.run(['chown','-R','smartpc:smartpc',str(out)],check=True)
   with (W/('native-'+label+'-'+theme+'.txt')).open('w') as log:
    r=subprocess.run(['runuser','-u','smartpc','--','env',*[k+'='+v for k,v in base_env.items()],str(PY),*command,'--output',str(out)],stdout=log,stderr=subprocess.STDOUT,timeout=240)
   row={'case':label,'theme':theme,'exitCode':r.returncode};rows.append(row);print(json.dumps(row),flush=True)
   assert r.returncode==0,row
   report=json.loads((out/'report.json').read_text());assert report['status']=='passed' and not report.get('qmlWarnings') and not report.get('warnings') and not report.get('networkAttempts')
 receipt={'status':'passed','version':manifest['version'],'diagnosticManifestSha256':hashlib.sha256((D/'release-manifest.json').read_bytes()).hexdigest(),'cases':rows,'platform':'EGLFS/KMS','display':[960,640],'physicalFramesQualified':False,'scope':'Private actual Main/Worker, navigation, aquarium and Start/Pause/Save across three themes'}
 (W/'native-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
