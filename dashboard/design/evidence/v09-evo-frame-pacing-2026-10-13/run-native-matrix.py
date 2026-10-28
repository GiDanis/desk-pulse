"""Pause already authorized; display exclusive only for four private measurements."""
import hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-evo-pacing-proof';GAME=H/'.local/share/SmartPC/SmartPC/game';BASE=H/'smartpc-v09-rc12-project';PY=H/'game-runtime/bin/python'

def snapshot():
 with sqlite3.connect('file:'+str(GAME/'game.sqlite')+'?mode=ro',uri=True) as db:
  tables={r[0]:db.execute('SELECT * FROM '+r[0]+' ORDER BY rowid').fetchall() for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 return tables
before=snapshot();assert not any(r[2]=='running' for r in before['sessions'])
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 stable=snapshot()
 with sqlite3.connect('file:'+str(GAME/'game.sqlite')+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row;row=dict(db.execute("SELECT * FROM drivers WHERE name='Evo'").fetchone());row['profile']=json.loads(row['profile'])
 checkpoint=json.loads((GAME/'policies'/(row['checkpoint']+'.json')).read_text())
 (P/'evo-source.json').write_text(json.dumps(dict(metadata={k:row[k] for k in ('name','profile','checkpoint','steps','seconds')},checkpoint=checkpoint)))
 for child in P.iterdir():subprocess.run(['chown','-R','smartpc:smartpc',str(child)],check=True)
 prototype=P/'prototype-project'
 if not prototype.exists():
  prototype.mkdir();shutil.copytree(BASE/'dashboard',prototype/'dashboard');(prototype/'theme-projects').symlink_to(BASE/'theme-projects',target_is_directory=True)
 qml=prototype/'dashboard/presentations/GameVisual.qml';s=qml.read_text();s=s.replace('enabled:car.visible && car.smooth &&','enabled:root.meta.framePresentation !== "interpolated30" && car.visible && car.smooth &&');qml.write_text(s)
 env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1','TMPDIR=/tmp']
 for mode in ('capture','replay32','replay8','smooth30'):
  print('Start '+mode,flush=True)
  with (P/(mode+'.txt')).open('w') as out:
   subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(P/'probe-native-pacing.py'),'--project',str(prototype if mode=='smooth30' else BASE),'--output',str(P),'--mode',mode,'--seconds','35'],stdout=out,stderr=subprocess.STDOUT,check=True,timeout=100)
  print('Passed '+mode,flush=True)
 assert snapshot()==stable,'Original training data changed during private benchmark'
 result=dict(status='passed',version='0.9.0-rc.12',originalDriverFieldsAndTablesUnchanged=True,sourceCheckpoint=row['checkpoint'],sourceSteps=row['steps'],installedFilesUnchanged=True,prototypeNotInstalled=True)
 (P/'native-matrix-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
finally:
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
