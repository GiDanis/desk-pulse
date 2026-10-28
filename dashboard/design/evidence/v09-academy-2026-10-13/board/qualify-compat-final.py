"""Backup first, recover orphan rollback journal, test isolated native UI."""
import hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-academy-proof';PROJECT=H/'smartpc-v09-rc9-project';PY=H/'game-runtime/bin/python'
SOURCE=H/'.local/share/SmartPC/SmartPC/game';P.mkdir(exist_ok=True)
manifest=json.loads((PROJECT/'dashboard/release-manifest.json').read_text())
assert manifest['version']=='0.9.0-rc.9'
assert all(hashlib.sha256((PROJECT/'dashboard'/k).read_bytes()).hexdigest()==v for k,v in manifest['sha256'].items())
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard',
  'QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json',
  'QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1']
 commands=[('base-final',['check_game_ui.py','--theme','base','--method','neat','--soak-seconds','8'],120)]
 reports=[]
 for label,args,timeout in commands:
  print('Native start: '+label,flush=True)
  with (P/(label+'.txt')).open('w') as out:
   subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(PROJECT/'dashboard'/args[0]),*args[1:],'--capture-dir',str(P/label)],cwd=PROJECT,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=timeout)
  report=json.loads((P/label/'report.json').read_text());assert report['status']=='passed' and not report['qmlWarnings']
  assert 'Traceback' not in (P/(label+'.txt')).read_text()
  reports.append({'label':label,**report});print('Native passed: '+label,flush=True)
 (P/'native-compat-final.json').write_text(json.dumps({'status':'passed','version':manifest['version'],'profiles':reports},indent=2)+'\n')
finally:
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
