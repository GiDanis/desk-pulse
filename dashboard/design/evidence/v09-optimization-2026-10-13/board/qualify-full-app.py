"""Installed app native capture, followed by a fresh service and data receipt."""
import hashlib,json,sqlite3,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-optimization-proof';PY=H/'game-runtime/bin/python'
assert json.loads((P/'final-receipt.json').read_text())['status']=='passed'
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 (P/'full-startup.json').unlink(missing_ok=True)
 with (P/'full-startup.txt').open('w') as output:
  subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(P/'capture-full-app.py')],cwd='/opt/smartpc/dashboard',stdout=output,stderr=subprocess.STDOUT,check=True,timeout=90)
 assert json.loads((P/'full-startup.json').read_text())['status']=='passed'
 assert json.loads((P/'full-startup.json').read_text())['currentPIDVerified']
 assert 'Traceback' not in (P/'full-startup.txt').read_text()
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
path=P/'final-health.json';path.touch();subprocess.run(['chown','smartpc:smartpc',str(path)],check=True)
for _ in range(40):
 time.sleep(3)
 subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen',str(PY),str(H/'v086-source-proof/board-health.py'),'--output',str(path)],check=True,stdout=subprocess.DEVNULL)
 after=json.loads(path.read_text());gui=after.get('guiHeartbeat') or {}
 if gui.get('ready') and gui.get('ageSeconds',999)<5 and not gui.get('pending'):break
else:raise AssertionError('Heartbeat GUI non pronto')
before=json.loads((P/'before-install.json').read_text());expected=json.loads((P/'before-game.json').read_text())
assert after['version']=='0.9.0-rc.10' and not after['manifestMismatches'] and after['service']['ActiveState']=='active' and after['service']['NRestarts']=='0'
assert before['allPreferenceHashes']==after['allPreferenceHashes'] and before['activeTheme']==after['activeTheme'] and before['bootId']==after['bootId']
game=H/'.local/share/SmartPC/SmartPC/game'
with sqlite3.connect('file:'+str(game/'game.sqlite')+'?mode=ro',uri=True) as db:
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert list(db.iterdump())==expected['baselineDump']
assert {q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in (game/'policies').glob('*.json')}==expected['artifacts']
receipt=json.loads((P/'final-receipt.json').read_text());receipt.update(fullInstalledAppVerified=True,noImplicitGameStart=True,guiHeartbeat=gui,service=after['service'],finalTime=after['time'])
(P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2),flush=True)
