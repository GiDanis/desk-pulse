"""Driving memory and race records delivery, private native tests and preserved originals."""
import hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-driving-memory-proof';PROJECT=H/'smartpc-v09-rc12-project';SOURCE=PROJECT/'dashboard';TARGET=Path('/opt/smartpc/dashboard');PY=H/'game-runtime/bin/python';GAME=H/'.local/share/SmartPC/SmartPC/game'
P.mkdir(exist_ok=True)
subprocess.run(['chown','smartpc:smartpc',str(P)],check=True)
manifest=json.loads((SOURCE/'release-manifest.json').read_text())
assert manifest['version']=='0.9.0-rc.12'
assert all(hashlib.sha256((SOURCE/k).read_bytes()).hexdigest()==v for k,v in manifest['sha256'].items())
def snapshot():
 with sqlite3.connect('file:'+str(GAME/'game.sqlite')+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  tables={r[0]:db.execute('SELECT * FROM '+r[0]+' ORDER BY rowid').fetchall() for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  drivers=db.execute('SELECT name,steps,checkpoint FROM drivers ORDER BY number').fetchall()
 return dict(tables=tables,drivers=drivers,artifacts={q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in (GAME/'policies').glob('*.json')})
def normalized(s):
 s=json.loads(json.dumps(s))
 for table in ('driver_memory','driving_archives','driving_contexts','track_records'):
  if table in s['tables']:
   assert not s['tables'][table],table+' must remain empty until explicit Start'
   del s['tables'][table]
 for r in s['tables']['sessions']:
  if r[0] in paused_ids:
   assert r[2] in ('paused','interrupted')
   r[2]='interrupted';r[4]='session closed during maintenance'
 return s
def health(label):
 path=P/(label+'.json');path.touch();subprocess.run(['chown','smartpc:smartpc',str(path)],check=True)
 subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen',str(PY),str(H/'v086-source-proof/board-health.py'),'--output',str(path)],check=True,stdout=subprocess.DEVNULL)
 return json.loads(path.read_text())
first=snapshot();active=[r for r in first['tables']['sessions'] if r[2]=='running'];assert not active,'Training must be paused before maintenance'
paused=[r for r in first['tables']['sessions'] if r[2]=='paused'];assert len(paused)<=1
paused_ids={r[0] for r in paused}
for name,steps,checkpoint in first['drivers']:
 if name=='Evo':
  saved=json.loads((GAME/'policies'/(checkpoint+'.json')).read_text());assert saved['steps']==steps
  (P/'evo-preserved.json').write_text(json.dumps(dict(steps=steps,checkpoint=checkpoint,generation=saved['learner']['generation']),indent=2)+'\n')
before=health('before-install');assert before['version']=='0.9.0-rc.11' and not before['manifestMismatches']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
backup=Path('/var/backups')/time.strftime('smartpc-before-driving-memory-%Y%m%d-%H%M%S');backup.mkdir(mode=0o700)
try:
 stable=snapshot();assert normalized(stable)==normalized(first)
 def copy_file(src,dst):
  if Path(src).parent==GAME/'policies':os.link(src,dst);return dst
  return shutil.copy2(src,dst)
 shutil.copytree(GAME,backup/'game',copy_function=copy_file)
 shutil.copytree(H/'.config/SmartPC',backup/'config')
 (P/'backup.json').write_text(json.dumps(dict(path=str(backup),immutableArtifactsHardlinked=len(stable['artifacts'])),indent=2)+'\n')
 os.sync()
 env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1']
 backend_files={k:v for k,v in manifest['sha256'].items() if k.startswith('game_') and k.endswith('.py') or k in ('check_game_memory.py','check_game_records.py','check_game_real_circuits.py')}
 backend_proof=P/'backend-qualified-files.json'
 if not backend_proof.exists() or json.loads(backend_proof.read_text())!=backend_files:
  with (P/'backend-tests.txt').open('w') as out:
   subprocess.run(['runuser','-u','smartpc','--','env','OPENBLAS_NUM_THREADS=1',str(PY),'-m','unittest','check_game_memory','check_game_records','check_game_real_circuits'],cwd=SOURCE,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=180)
  backend_proof.write_text(json.dumps(backend_files,indent=2)+'\n')
 with (P/'existing-drivers.txt').open('w') as out:
  subprocess.run(['runuser','-u','smartpc','--','env','OPENBLAS_NUM_THREADS=1',str(PY),str(PROJECT/'check-existing-drivers.py')],cwd=SOURCE,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=120)
 reports=[]
 cases=[
  ('base-evo','check_game_ui.py',['--theme','base','--method','evolution','--soak-seconds','8']),
  ('functional-neat','check_game_ui.py',['--theme','functional','--method','neat','--soak-seconds','8']),
  ('apple-ppo','check_game_ui.py',['--theme','apple','--method','ppo','--track','varano-short-1','--text-scale','1.1','--soak-seconds','4']),
  ('apple-settings','check_game_settings_ui.py',['--theme','apple','--palette','night','--text-scale','1.1']),
  ('apple-dossier','check_game_dossier_ui.py',['--theme','apple']),
  ('apple-memory','check_game_memory_ui.py',['--theme','apple']),
  ('base-race','check_game_records_ui.py',['--theme','base','--track','oval-1']),
  ('functional-race','check_game_records_ui.py',['--theme','functional','--track','technical-1']),
  ('apple-race','check_game_records_ui.py',['--theme','apple','--track','varano-short-1']),
  ('complete-races','check_game_academy_race_ui.py',[])]
 for label,script,args in cases:
  print('Native start: '+label,flush=True)
  with (P/(label+'.txt')).open('w') as out:
   subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(SOURCE/script),*args,'--capture-dir',str(P/label)],cwd=PROJECT,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=400)
  report=json.loads((P/label/'report.json').read_text());assert report['status']=='passed' and not report['qmlWarnings']
  if label=='complete-races':
   assert report['complete']
   assert all(row['telemetryVersion']==1 and len(row['lapTimes'])==3 and row['bestLap']>0 and row['maxSpeed']>0 for race in report['races'] for row in race['results'])
  reports.append(dict(label=label,**report));print('Native passed: '+label,flush=True)
 (P/'native-qualification.json').write_text(json.dumps(dict(status='passed',profiles=reports),indent=2)+'\n')
 assert normalized(snapshot())==normalized(stable)
 stage=TARGET.with_name('dashboard-rc12-stage');stage.mkdir()
 for name,digest in manifest['sha256'].items():
  dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE/name,dest)
  assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
 shutil.copy2(SOURCE/'release-manifest.json',stage/'release-manifest.json');os.sync()
 old=TARGET.with_name('dashboard-rc11-before-driving-memory');assert not old.exists()
 TARGET.rename(old);stage.rename(TARGET);os.sync()
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 deadline=time.monotonic()+90
 while True:
  time.sleep(3);after=health('installed');gui=after.get('guiHeartbeat') or {}
  if after['service']['ActiveState']=='active' and gui.get('ready') and gui.get('ageSeconds',999)<5 and not gui.get('pending'):break
  assert time.monotonic()<deadline,'GUI not ready'
 assert after['version']==manifest['version'] and not after['manifestMismatches']
 assert before['allPreferenceHashes']==after['allPreferenceHashes'] and before['activeTheme']==after['activeTheme']
 assert after['service']['NRestarts']=='0' and before['bootId']==after['bootId']
 assert normalized(snapshot())==normalized(stable)
 receipt=dict(status='passed',version=after['version'],files=len(manifest['sha256']),backup=str(backup),runtimeRollback=str(old),
  allDriverFieldsPreserved=True,allArtifactsPreserved=True,artifactCount=len(stable['artifacts']),
  allTablesPreservedExceptPausedSessionClosure=True,newTablesEmptyUntilStart=True,closedPausedSessions=len(paused),
  preferencesPreserved=True,activeTheme=after['activeTheme'],sameBoot=True,newOSReboot=False,
  manifestMismatches=after['manifestMismatches'],service=after['service'],guiHeartbeat=after['guiHeartbeat'])
 (P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
 old=TARGET.with_name('dashboard-rc11-before-driving-memory')
 if old.exists():
  subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
  TARGET.rename(TARGET.with_name('dashboard-rc12-failed'));old.rename(TARGET)
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 raise
finally:
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
