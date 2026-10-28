"""Authorized additive rc21 delivery. Native private tests, preserved pilot data."""
from pathlib import Path
from contextlib import closing
import hashlib,json,os,shutil,sqlite3,subprocess,sys,time
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-timing-proof';PROJECT=H/'smartpc-timing-project';SOURCE=PROJECT/'dashboard'
RUNTIME=H/'smartpc-timing-runtime';TARGET=Path('/opt/smartpc/dashboard');PY=H/'game-runtime/bin/python';GAME=H/'.local/share/SmartPC/SmartPC/game'
sys.path.insert(0,str(SOURCE))
manifest=json.loads((RUNTIME/'release-manifest.json').read_text());assert manifest['version']=='0.9.0-rc.21'
assert all(hashlib.sha256((RUNTIME/k).read_bytes()).hexdigest()==v for k,v in manifest['sha256'].items())
def snapshot():
 with closing(sqlite3.connect((GAME/'game.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
  db.execute('PRAGMA query_only=ON');db.execute('BEGIN');assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  return {r[0]:db.execute('SELECT * FROM '+r[0]+' ORDER BY rowid').fetchall() for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
def artifacts():return {str(p.relative_to(GAME)):hashlib.sha256(p.read_bytes()).hexdigest() for p in GAME.rglob('*') if p.is_file() and not p.name.startswith('game.sqlite')}
def health(label):
 path=P/(label+'.json');path.touch();subprocess.run(['chown','smartpc:smartpc',str(path)],check=True)
 subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen',str(PY),str(H/'v086-source-proof/board-health.py'),'--output',str(path)],check=True,stdout=subprocess.DEVNULL)
 return json.loads(path.read_text())
before=snapshot();assert not any(r[2]=='running' for r in before['sessions']),'Session still running'
assert not any('multiprocessing.spawn' in p or 'spawn_main' in p for p in subprocess.check_output(['ps','-eo','args='],text=True).splitlines()),'A worker is active'
initial=health('before-install');assert initial['version']=='0.9.0-rc.20' and not initial['manifestMismatches']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
old=TARGET.with_name('dashboard-rc20-before-timing');stage=TARGET.with_name('dashboard-rc21-timing-stage')
backup=H/'game-backups'/time.strftime('before-timing-%Y%m%d-%H%M%S');switched=False
try:
 stable=snapshot();assert stable==before,'Game changed before stop';original=artifacts()
 shutil.copytree(GAME,backup);shutil.copytree(H/'.config/SmartPC',backup.with_name(backup.name+'-config'));os.sync()
 subprocess.run(['chown','-R','smartpc:smartpc',str(PROJECT),str(P)],check=True)
 env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
 cases=[]
 for theme,seconds in (('base',12),('functional',12),('apple',120)):
  label=theme+'-native';print('EGLFS '+label+' ABBA '+str(seconds)+'s each',flush=True)
  with (P/(label+'.txt')).open('w') as f:
   subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(SOURCE/'check_game_timing_ui.py'),'--theme',theme,'--output',str(P/label),'--sample',str(seconds)],cwd=PROJECT,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=780)
  report=json.loads((P/label/'report.json').read_text());assert report['status']=='passed' and not report['qmlWarnings'] and report['fiveCarsVisible']
  if theme=='apple':
   on=[s['p95'] for s in report['frameSamples'] if s['hud']];off=[s['p95'] for s in report['frameSamples'] if not s['hud']]
   on=sum(on)/len(on);off=sum(off)/len(off);assert on-off<=max(.002,.05*off),(on,off)
  cases.append(report);print('Passed '+label,flush=True)
 assert snapshot()==stable and artifacts()==original,'Private tests changed original game'
 assert not old.exists() and not stage.exists();stage.mkdir()
 for name,digest in manifest['sha256'].items():
  dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(RUNTIME/name,dest);assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
 shutil.copy2(RUNTIME/'release-manifest.json',stage/'release-manifest.json');os.sync()
 TARGET.rename(old);stage.rename(TARGET);switched=True;os.sync();subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 deadline=time.monotonic()+90
 while True:
  time.sleep(3);after=health('installed');gui=after.get('guiHeartbeat') or {}
  if after['service']['ActiveState']=='active' and gui.get('ready') and gui.get('ageSeconds',999)<5 and not gui.get('pending'):break
  assert time.monotonic()<deadline,'GUI not ready'
 assert after['version']==manifest['version'] and not after['manifestMismatches'] and after['service']['NRestarts']=='0'
 assert initial['allPreferenceHashes']==after['allPreferenceHashes'] and initial['activeTheme']==after['activeTheme'] and initial['bootId']==after['bootId']
 final=snapshot()
 expected=dict(stable);expected['sessions']=[tuple('interrupted' if i==2 and x=='paused' else x for i,x in enumerate(row)) for row in stable['sessions']]
 assert all(final[k]==v for k,v in expected.items()),'Existing game rows changed';assert final.get('timing_laps',[])==[]
 assert artifacts()==original
 receipt=dict(status='passed',version=after['version'],files=len(manifest['sha256']),runtimeRollback=str(old),dataBackup=str(backup),preferencesPreserved=True,activeTheme=after['activeTheme'],newOSReboot=False,service=after['service'],guiHeartbeat=after['guiHeartbeat'],manifestMismatches=after['manifestMismatches'],nativeCases=[r['theme'] for r in cases],pilotsPreserved=True,oldTablesPreservedExceptPausedStatus=True,pausedSessionsClosed=sum(r[2]=='paused' for r in stable['sessions']),artifactCount=len(original),artifactsPreserved=True,newTable='timing_laps',finalManifestSha256=hashlib.sha256((TARGET/'release-manifest.json').read_bytes()).hexdigest())
 (P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
 if switched:
  subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True);TARGET.rename(TARGET.with_name('dashboard-rc21-failed-timing'));old.rename(TARGET)
 raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
