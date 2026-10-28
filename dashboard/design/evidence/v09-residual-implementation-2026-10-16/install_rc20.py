"""Authorized rc20 delivery: private EGLFS checks, atomic clean roster, rollback."""
from pathlib import Path
from contextlib import closing
import hashlib,json,os,shutil,sqlite3,subprocess,sys,time
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-residual-proof';P.mkdir(exist_ok=True)
PROJECT=H/'smartpc-residual-delivery-project';SOURCE=PROJECT/'dashboard'
RUNTIME=H/'smartpc-residual-runtime-final';TARGET=Path('/opt/smartpc/dashboard')
PY=H/'game-runtime/bin/python';GAME=H/'.local/share/SmartPC/SmartPC/game'
sys.path.insert(0,str(SOURCE))
from game_residual_migration import prepare,install,inventory,exchange
from game_store import GameStore
from check_game_residual_ui import qualify_roster
manifest=json.loads((RUNTIME/'release-manifest.json').read_text())
assert manifest['version']=='0.9.0-rc.20'
assert all(hashlib.sha256((RUNTIME/k).read_bytes()).hexdigest()==v for k,v in manifest['sha256'].items())

def snapshot():
 with closing(sqlite3.connect((GAME/'game.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
  db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  return {r[0]:db.execute('SELECT * FROM '+r[0]+' ORDER BY rowid').fetchall() for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}

def health(label):
 path=P/(label+'.json');path.touch();subprocess.run(['chown','smartpc:smartpc',str(path)],check=True)
 subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),
  'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen',
  str(PY),str(H/'v086-source-proof/board-health.py'),'--output',str(path)],check=True,stdout=subprocess.DEVNULL)
 return json.loads(path.read_text())

before=snapshot();assert not any(r[2]=='running' for r in before['sessions']),'Training still running'
assert not any('multiprocessing.spawn' in p or 'spawn_main' in p for p in subprocess.check_output(['ps','-eo','args='],text=True).splitlines()),'A worker is active'
initial=health('before-install');assert initial['version']=='0.9.0-rc.19' and not initial['manifestMismatches']
subprocess.run(['chown','smartpc:smartpc',str(P)],check=True)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
old=TARGET.with_name('dashboard-rc19-before-residual');stage=TARGET.with_name('dashboard-rc20-residual-stage')
backup=H/'game-backups'/time.strftime('before-residual-%Y%m%d-%H%M%S')
switched=migrated=False
try:
 stable=snapshot();assert stable==before,'Game changed before stop'
 original=inventory(GAME);(P/'old-game-inventory.json').write_text(json.dumps(original,indent=2)+'\n')
 shutil.copytree(H/'.config/SmartPC',P/('config-before-'+time.strftime('%Y%m%d-%H%M%S')));os.sync()
 env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),
  'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms',
  'QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl',
  'OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
 cases=[]
 for theme in ('base','functional','apple'):
  label=theme+'-native';args=['--theme',theme,'--output',str(P/label),'--race-seconds','12']
  if theme=='apple':args+=['--qualification']
  print('EGLFS '+label,flush=True)
  with (P/(label+'.txt')).open('w') as f:
   subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(SOURCE/'check_game_residual_ui.py'),*args],cwd=PROJECT,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=360)
  report=json.loads((P/label/'report.json').read_text());assert report['status']=='passed' and not report['qmlWarnings'] and report['fiveCarsVisible']
  cases.append(report);print('Passed '+label,flush=True)
 assert snapshot()==stable and inventory(GAME)==original,'Private tests modified original data'
 fresh=prepare(GAME);fresh_store=GameStore(fresh)
 print('Actual initial qualifying, five independent policies',flush=True)
 timed=qualify_roster(fresh_store)
 with fresh_store.connect() as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
  assert db.execute('SELECT count(*) FROM timed_qualifications').fetchone()[0]==5
 subprocess.run(['chown','-R','smartpc:smartpc',str(fresh)],check=True)
 assert not old.exists() and not stage.exists();stage.mkdir()
 for name,digest in manifest['sha256'].items():
  dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(RUNTIME/name,dest)
  assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
 shutil.copy2(RUNTIME/'release-manifest.json',stage/'release-manifest.json');os.sync()
 migration=install(GAME,fresh,backup);migrated=True
 TARGET.rename(old);stage.rename(TARGET);switched=True;os.sync()
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 deadline=time.monotonic()+90
 while True:
  time.sleep(3);after=health('installed');gui=after.get('guiHeartbeat') or {}
  if after['service']['ActiveState']=='active' and gui.get('ready') and gui.get('ageSeconds',999)<5 and not gui.get('pending'):break
  assert time.monotonic()<deadline,'GUI not ready'
 assert after['version']==manifest['version'] and not after['manifestMismatches'] and after['service']['NRestarts']=='0'
 assert initial['allPreferenceHashes']==after['allPreferenceHashes'] and initial['activeTheme']==after['activeTheme'] and initial['bootId']==after['bootId']
 final=snapshot();names=[r[1] for r in final['drivers']];assert names==['Maestro','Crono','Memoria','Linea','Tattico'],names
 assert len(final['timed_qualifications'])==5 and not final['objective_paths']
 assert inventory(backup)==original
 receipt=dict(status='passed',version=after['version'],files=len(manifest['sha256']),migration=migration,
  runtimeRollback=str(old),preferencesPreserved=True,activeTheme=after['activeTheme'],newOSReboot=False,
  service=after['service'],guiHeartbeat=after['guiHeartbeat'],manifestMismatches=after['manifestMismatches'],
  nativeCases=[r['theme'] for r in cases],newPilots=names,initialQualifyingTimes=timed,
  oldRosterAbsentFromActiveStore=True,foreignKeysValid=True,initialNeuralCorrections='neutral; no study weights imported',
  finalManifestSha256=hashlib.sha256((TARGET/'release-manifest.json').read_bytes()).hexdigest())
 (P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
 if switched or migrated:subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
 if switched:
  TARGET.rename(TARGET.with_name('dashboard-rc20-failed-residual'));old.rename(TARGET)
 if migrated:exchange(GAME,backup)
 raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
