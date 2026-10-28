"""Install only manifest files; preserve the recovered original game archive."""
import hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-academy-proof';SOURCE=H/'smartpc-v09-rc9-project/dashboard';TARGET=Path('/opt/smartpc/dashboard')
PY=H/'game-runtime/bin/python';HEALTH=H/'v086-source-proof/board-health.py';GAME=H/'.local/share/SmartPC/SmartPC/game'
manifest=json.loads((SOURCE/'release-manifest.json').read_text());assert manifest['version']=='0.9.0-rc.9'
assert json.loads((P/'native-qualification.json').read_text())['status']=='passed'
assert json.loads((P/'production-checkpoints-copy.json').read_text())['status']=='passed'
assert all(hashlib.sha256((SOURCE/k).read_bytes()).hexdigest()==v for k,v in manifest['sha256'].items())
expected=json.loads((P/'before-game.json').read_text());backup=json.loads((P/'backup.json').read_text())
def game():
 with sqlite3.connect('file:'+str(GAME/'game.sqlite')+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  dump=list(db.iterdump());drivers=db.execute('SELECT name FROM drivers ORDER BY number').fetchall()
 return dump,{q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in (GAME/'policies').glob('*.json')},[r[0] for r in drivers]
def health(label):
 path=P/(label+'.json');path.touch();subprocess.run(['chown','smartpc:smartpc',str(path)],check=True)
 subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen',str(PY),str(HEALTH),'--output',str(path)],check=True,stdout=subprocess.DEVNULL)
 return json.loads(path.read_text())
prior=game();assert prior[:2]==(expected['baselineDump'],expected['artifacts'])
before=health('before-install');assert before['version']=='0.9.0-rc.8' and before['service']['ActiveState']=='active' and not before['manifestMismatches']
staging=TARGET.with_name('dashboard-rc9-stage');staging.mkdir()
for name,digest in manifest['sha256'].items():
 dest=staging/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE/name,dest)
 assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
shutil.copy2(SOURCE/'release-manifest.json',staging/'release-manifest.json')
os.sync()
previous=TARGET.with_name('dashboard-rc8-before-academy');assert not previous.exists()
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 TARGET.rename(previous);staging.rename(TARGET);os.sync()
 subprocess.run(['systemctl','reset-failed','smartpc-dashboard'],check=True)
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 deadline=time.monotonic()+120
 while True:
  time.sleep(3);after=health('installed');gui=after.get('guiHeartbeat') or {}
  if after['service']['ActiveState']=='active' and gui.get('ready') and gui.get('ageSeconds',999)<5 and not gui.get('pending'):break
  assert time.monotonic()<deadline,'GUI non pronta entro 120 s'
 assert after['version']==manifest['version'] and not after['manifestMismatches']
 assert before['allPreferenceHashes']==after['allPreferenceHashes']
 assert before['activeTheme']==after['activeTheme'] and after['service']['NRestarts']=='0'
 assert before['bootId']==after['bootId'];assert game()==prior
 receipt=dict(status='passed',version=after['version'],files=len(manifest['sha256']),backup=backup['path'],runtimeRollback=str(previous),
  allGameTablesPreservedAfterRecovery=True,allDriverColumnsPreserved=True,drivers=prior[2],artifactCount=len(prior[1]),allArtifactsPreserved=True,
  orphanJournalRecovered=expected['orphanJournalRecovered'],stalePausedSessionsInterrupted=expected['stalePausedSessionsInterrupted'],
  preferencesPreserved=True,themePreserved=True,activeTheme=after['activeTheme'],sameBoot=True,newOSReboot=False,
  manifestMismatches=after['manifestMismatches'],service=after['service'],guiHeartbeat=after['guiHeartbeat'])
 (P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2),flush=True)
except BaseException:
 subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
 if previous.exists():
  TARGET.rename(TARGET.with_name('dashboard-rc9-failed'));previous.rename(TARGET)
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True);raise
