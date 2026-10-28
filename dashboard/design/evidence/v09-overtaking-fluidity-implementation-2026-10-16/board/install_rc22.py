"""Additive delivery after private qualification; original game remains intact."""
from pathlib import Path
from contextlib import closing
import hashlib,json,os,shutil,sqlite3,subprocess,time
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-overtake-proof';RUNTIME=H/'smartpc-overtake-runtime';TARGET=Path('/opt/smartpc/dashboard');PY=H/'game-runtime/bin/python';GAME=H/'.local/share/SmartPC/SmartPC/game'
manifest=json.loads((RUNTIME/'release-manifest.json').read_text());assert manifest['version']=='0.9.0-rc.22'
assert all(hashlib.sha256((RUNTIME/k).read_bytes()).hexdigest()==v for k,v in manifest['sha256'].items())
required=['functional-flows','timing-base','timing-functional','timing-apple','long-race-base','long-qualifying-functional','long-race-apple','long-mature-ppo','long-mature-sac','long-mature-tactic-td3','trace-off-apple','functional-retained-final','mature-ppo-final-supplement']
for label in required:
 report=json.loads((P/label/'report.json').read_text());assert report['status']=='passed' and not report['qmlWarnings'],label
 if label.startswith('long-'):assert sum(x['elapsed'] for x in report['runs'])>=599.9,label

final_checks=json.loads((P/'final-source-checks.json').read_text());assert final_checks['status']=='passed'
assert all(manifest['sha256'].get(n)==v for n,v in final_checks['sourceHashes'].items()),'Final checks refer to different source'
performance=json.loads((P/'performance-summary.json').read_text());assert len(performance['cases'])>=6 and not performance['opticalFPSCertified']

def snapshot():
 with closing(sqlite3.connect((GAME/'game.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
  db.execute('PRAGMA query_only=ON');db.execute('BEGIN');assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  return {r[0]:db.execute('SELECT * FROM '+r[0]+' ORDER BY rowid').fetchall() for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}

def artifacts():return {str(p.relative_to(GAME)):hashlib.sha256(p.read_bytes()).hexdigest() for p in GAME.rglob('*') if p.is_file() and not p.name.startswith('game.sqlite')}

def health(label):
 path=P/(label+'.json');path.touch();subprocess.run(['chown','smartpc:smartpc',str(path)],check=True)
 subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen',str(PY),str(H/'v086-source-proof/board-health.py'),'--output',str(path)],check=True,stdout=subprocess.DEVNULL)
 return json.loads(path.read_text())

before=snapshot();assert not any(r[2]=='running' for r in before['sessions'])
assert not any('multiprocessing.spawn' in x or 'spawn_main' in x for x in subprocess.check_output(['ps','-eo','args='],text=True).splitlines()),'Worker active'
initial=health('before-install');assert initial['version']=='0.9.0-rc.21' and not initial['manifestMismatches']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
old=TARGET.with_name('dashboard-rc21-before-overtake');stage=TARGET.with_name('dashboard-rc22-overtake-stage');backup=H/'game-backups'/time.strftime('before-overtake-%Y%m%d-%H%M%S');switched=False
try:
 stable=snapshot();assert stable==before;original=artifacts()
 shutil.copytree(GAME,backup);shutil.copytree(H/'.config/SmartPC',backup.with_name(backup.name+'-config'));os.sync()
 assert not old.exists() and not stage.exists();stage.mkdir()
 for name,digest in manifest['sha256'].items():
  dest=stage/name;assert dest.resolve().is_relative_to(stage.resolve())
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(RUNTIME/name,dest);assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
 shutil.copy2(RUNTIME/'release-manifest.json',stage/'release-manifest.json');os.sync()
 TARGET.rename(old);stage.rename(TARGET);switched=True;os.sync();subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 deadline=time.monotonic()+90
 while True:
  time.sleep(3);after=health('installed');gui=after.get('guiHeartbeat') or {}
  if after['service']['ActiveState']=='active' and gui.get('ready') and gui.get('ageSeconds',999)<5 and not gui.get('pending') and gui.get('pid')==after['runtimePid'] and after['runtimePid']!=initial['runtimePid']:break
  assert time.monotonic()<deadline,'GUI not ready'
 assert after['version']==manifest['version'] and not after['manifestMismatches'] and after['service']['NRestarts']=='0'
 assert initial['allPreferenceHashes']==after['allPreferenceHashes'] and initial['activeTheme']==after['activeTheme'] and initial['bootId']==after['bootId']
 final=snapshot();expected=dict(stable)
 expected['sessions']=[tuple('interrupted' if i==2 and x=='paused' else x for i,x in enumerate(row)) for row in stable['sessions']]
 assert final==expected,'Existing game rows changed'
 remaining=artifacts();assert all(remaining.get(k)==v for k,v in original.items()),'An original model changed'
 receipt=dict(status='passed',version=after['version'],files=len(manifest['sha256']),runtimeRollback=str(old),dataBackup=str(backup),
  preferencesPreserved=True,liveGuiPidVerified=True,activeTheme=after['activeTheme'],newOSReboot=False,service=after['service'],guiHeartbeat=after['guiHeartbeat'],manifestMismatches=after['manifestMismatches'],
  nativeCases=required,pilotsPreserved=True,oldTablesPreservedExceptPausedStatus=True,pausedSessionsClosed=sum(r[2]=='paused' for r in stable['sessions']),artifactCountBefore=len(original),artifactCountAfter=len(remaining),originalArtifactsPreserved=True,
  finalManifestSha256=hashlib.sha256((TARGET/'release-manifest.json').read_bytes()).hexdigest(),recipeMigration='none; race-residual-2 retained, replay/optimizers/actors preserved; study recipe 3 rejected',performanceGate='see performance-summary.json; no optical-FPS certification')
 (P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
 if switched:
  subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True);TARGET.rename(TARGET.with_name('dashboard-rc22-failed-overtake'));old.rename(TARGET)
 raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
