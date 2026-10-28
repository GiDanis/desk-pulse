"""Exclusive native qualification on private driver state; restore kiosk on exit."""
import hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-pacing-optimization-proof';NEW=H/'smartpc-v09-rc13-project';OLD=H/'smartpc-v09-rc12-project';PY=H/'game-runtime/bin/python';GAME=H/'.local/share/SmartPC/SmartPC/game'
def snapshot():
 with sqlite3.connect('file:'+str(GAME/'game.sqlite')+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  return {r[0]:db.execute('SELECT * FROM '+r[0]+' ORDER BY rowid').fetchall() for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
before=snapshot();assert not any(r[2]=='running' for r in before['sessions']),'Pause and await Saved first'
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 stable=snapshot()
 for table in before:
  if table!='sessions':assert before[table]==stable[table],table
 checkpoint=json.loads((P.parent/'v09-evo-pacing-proof/evo-source.json').read_text())
 (P/'evo-source.json').write_text(json.dumps(checkpoint))
 shutil.copy2(P.parent/'v09-evo-pacing-proof/capture-scenes.json.gz',P/'capture-scenes.json.gz')
 if not (NEW/'theme-projects').exists():(NEW/'theme-projects').symlink_to(OLD/'theme-projects',target_is_directory=True)
 subprocess.run(['chown','-R','smartpc:smartpc',str(P),str(NEW)],check=True)
 env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1']
 cases=[('materialized',NEW,'replay32',[]),('fresh32',NEW,'capture',['--fresh-population'])]
 for label,project,mode,extra in cases:
  print('Native '+label,flush=True)
  with (P/(label+'.txt')).open('w') as out:
   subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(P/'probe-native.py'),'--project',str(project),'--output',str(P),'--mode',mode,'--label',label,'--seconds','35',*extra],stdout=out,stderr=subprocess.STDOUT,check=True,timeout=150)
  print(json.dumps({k:v for k,v in json.loads((P/(label+'.json')).read_text()).items() if k in ('frameHz','frameGaps','sceneGaps','qmlWarnings','steps')}),flush=True)
 assert snapshot()==stable,'Production tables changed during private tests'
 (P/'matrix-receipt.json').write_text(json.dumps(dict(status='passed',originalTablesUnchangedAfterOrdinaryPauseClosure=True,prototypeNotInstalled=True,source='rc12 actual Evo sequence + private fresh population from saved Evo weights',cases=[x[0] for x in cases]),indent=2)+'\n')
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
