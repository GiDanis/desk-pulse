import hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-session-modes-proof';PROJECT=H/'smartpc-v09-rc14-project';SOURCE=PROJECT/'dashboard';RUNTIME=H/'smartpc-v09-rc14-runtime';TARGET=Path('/opt/smartpc/dashboard');PY=H/'game-runtime/bin/python';GAME=H/'.local/share/SmartPC/SmartPC/game'
manifest=json.loads((RUNTIME/'release-manifest.json').read_text());assert manifest['version']=='0.9.0-rc.14'
assert all(hashlib.sha256((RUNTIME/k).read_bytes()).hexdigest()==v for k,v in manifest['sha256'].items())
def snapshot():
 with sqlite3.connect('file:'+str(GAME/'game.sqlite')+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  tables={r[0]:db.execute('SELECT * FROM '+r[0]+' ORDER BY rowid').fetchall() for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 return dict(tables=tables,artifacts={q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in (GAME/'policies').glob('*.json')})
def health(label):
 path=P/(label+'.json');path.touch();subprocess.run(['chown','smartpc:smartpc',str(path)],check=True)
 subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen',str(PY),str(H/'v086-source-proof/board-health.py'),'--output',str(path)],check=True,stdout=subprocess.DEVNULL)
 return json.loads(path.read_text())
before=snapshot();assert not any(r[2]=='running' for r in before['tables']['sessions'])
initial=health('before-navigation');assert initial['version']=='0.9.0-rc.14' and not initial['manifestMismatches']
with (P/'arm-windows-final.txt').open('w') as out:
 subprocess.run(['runuser','-u','smartpc','--','env','OPENBLAS_NUM_THREADS=1',str(PY),str(SOURCE/'check_game_sessions.py')],cwd=SOURCE,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=120)
print('ARM window boundaries passed',flush=True)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
old=TARGET.with_name('dashboard-rc14-before-windows');stage=TARGET.with_name('dashboard-rc14-window-stage');switched=False
try:
 assert snapshot()==before
 env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1']
 with (P/'window-native.txt').open('w') as out:
  subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(SOURCE/'check_game_sessions_ui.py'),'--theme','functional','--seconds','3','--output',str(P/'window-native')],cwd=PROJECT,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=90)
 assert snapshot()==before
 assert not old.exists() and not stage.exists();stage.mkdir()
 for name,digest in manifest['sha256'].items():
  dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(RUNTIME/name,dest);assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
 shutil.copy2(RUNTIME/'release-manifest.json',stage/'release-manifest.json');os.sync();TARGET.rename(old);stage.rename(TARGET);switched=True;os.sync()
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 deadline=time.monotonic()+90
 while True:
  time.sleep(3);after=health('installed-final');gui=after.get('guiHeartbeat') or {}
  if after['service']['ActiveState']=='active' and gui.get('ready') and gui.get('ageSeconds',999)<5 and not gui.get('pending'):break
  assert time.monotonic()<deadline
 time.sleep(3);after=health('installed-final');assert after['guiHeartbeat']['ready'] and after['guiHeartbeat']['ageSeconds']<5
 assert not after['manifestMismatches'] and after['service']['NRestarts']=='0'
 assert initial['allPreferenceHashes']==after['allPreferenceHashes'] and initial['activeTheme']==after['activeTheme'] and initial['bootId']==after['bootId']
 assert snapshot()==before
 receipt=json.loads((P/'navigation-receipt.json').read_text());receipt.update(service=after['service'],guiHeartbeat=after['guiHeartbeat'],windowBoundariesNative=True,windowRollback=str(old),finalManifestVerified=True,files=len(manifest['sha256']))
 (P/'window-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
 if switched:
  subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True);TARGET.rename(TARGET.with_name('dashboard-rc14-window-failed'));old.rename(TARGET)
 raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
