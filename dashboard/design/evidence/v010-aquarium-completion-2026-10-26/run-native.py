"""Exclusive EGLFS checks of the additive theme revision; always restore service."""
from pathlib import Path
import hashlib,json,subprocess,os
H=Path('/var/lib/smartpc-dashboard');P=H/'aquarium-completion-20261026';B=P/'source/dashboard';R=Path('/opt/smartpc/dashboard');PY=H/'game-runtime/bin/python'
manifest=json.loads((B/'release-manifest.json').read_text());assert manifest['version']=='0.10.0-rc.2'
assert all(hashlib.sha256((B/n).read_bytes()).hexdigest()==h for n,h in manifest['sha256'].items())
cache=json.loads((P/'theme-projects/apple-calm/evidence/preflight-cache.json').read_text());assert cache['result']['status']=='passed' and cache['identity']['version']=='1.6.5'
config=H/'.config/SmartPC';before={str(p.relative_to(config)):hashlib.sha256(p.read_bytes()).hexdigest() for p in config.rglob('*') if p.is_file()}
env=['HOME='+str(H),'QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 for name,command in [('icon-ui',[str(P/'check-icon-ui.py'),'--dashboard',str(B),'--bundle',str(P/'theme-projects/apple-calm/bundle')]),*[(theme+'-ui',[str(B/'check_aquarium_ui.py'),'--theme',theme]) for theme in ('base','functional')],('aquarium-ui',[str(B/'check_aquarium_ui.py'),'--theme','apple','--bundle',str(P/'theme-projects/apple-calm/bundle'),'--warmup','60','--seconds','120'])]:
  out=P/name;out.mkdir(exist_ok=True);subprocess.run(['chown','-R','smartpc:smartpc',str(out)],check=True)
  with (P/(name+'.log')).open('w') as log:subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),*command,'--output',str(out)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=320)
  report=json.loads((out/'report.json').read_text());assert report['status']=='passed' and not report.get('warnings') and not report.get('qmlWarnings') and not report['networkAttempts']
  if name!='icon-ui':
   assert report['near60SoftwareGate']
   assert report['checks'].count('requestedThemeSurvivesReentry')==20
  print(name,'passed',report.get('callbacksPerSecond'),report.get('p95Ms'),flush=True)
 assert before=={str(p.relative_to(config)):hashlib.sha256(p.read_bytes()).hexdigest() for p in config.rglob('*') if p.is_file()}
 (P/'native-receipt.json').write_text(json.dumps({'status':'passed','coreVersion':manifest['version'],'runtimeManifestSha256':hashlib.sha256((B/'release-manifest.json').read_bytes()).hexdigest(),'runtimeHashesVerified':682,'theme':cache['identity'],'preferencesPreserved':True,'cases':['icon-ui','base-ui','functional-ui','aquarium-ui'],'scope':'Actual private Main EGLFS; supplementary120s on new theme, original30min belongs to1.6.4; not optical/HID/live qualification'},indent=2)+'\n')
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
