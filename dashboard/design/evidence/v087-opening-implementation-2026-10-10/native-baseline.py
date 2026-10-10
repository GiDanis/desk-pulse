"""Measure frozen rc.1 in an isolated EGLFS process, restore kiosk in finally."""
import json,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v087-opening-proof';S=H/'smartpc-v087-opening-baseline/project';D=S/'dashboard'
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','PYTHONPATH='+str(D)]
egl=['QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 for theme in ['apple','base']:
  name='baseline-'+theme+'-off'
  args=[D/'verify_opening_ui.py','--theme',theme,'--motion','off','--bundle-project',S/'theme-projects/apple-calm/bundle','--output',P/(name+'.json')]
  with (P/(name+'.txt')).open('w') as out:
   subprocess.run(['runuser','-u','smartpc','--','env',*env,*egl,'python3',*map(str,args)],stdout=out,stderr=subprocess.STDOUT,check=True,timeout=420)
  x=json.loads((P/(name+'.json')).read_text());assert x['status']=='passed' and x['platform']=='eglfs' and not x['qml_messages'] and not x['network_attempts']
  print(json.dumps({'name':name,'statistics':x['statistics']}),flush=True)
finally:
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 print(subprocess.check_output(['systemctl','show','smartpc-dashboard','--property=ActiveState,SubState,NRestarts'],text=True),flush=True)
