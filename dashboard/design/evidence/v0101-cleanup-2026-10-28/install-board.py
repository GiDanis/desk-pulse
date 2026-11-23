"""Install the bounded maintenance runtime with a complete quiescent rollback."""
import hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');W=H/'maintenance-work';R=W/'runtime';T=Path('/opt/smartpc/dashboard');D=H/'.local/share/SmartPC/SmartPC';G=D/'game';PY=H/'game-runtime/bin/python'
manifest=json.loads((R/'release-manifest.json').read_text());prior=json.loads((T/'release-manifest.json').read_text());native=json.loads((W/'native-receipt.json').read_text())
assert manifest['version']=='0.10.1-rc.1' and prior['version']=='0.10.0-rc.2'
assert native['status']=='passed' and len(native['cases'])==6
assert native['version']==manifest['version'] and native['platform']=='EGLFS/KMS'
assert native['diagnosticManifestSha256']==hashlib.sha256((W/'source/dashboard/release-manifest.json').read_bytes()).hexdigest()
for root,m in ((R,manifest),(T,prior)):
 assert all((root/n).is_file() and hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
assert manifest['sha256']['libsmartpc_game_native.so']==prior['sha256']['libsmartpc_game_native.so']
assert all(manifest['sha256'][n]==json.loads((W/'source/dashboard/release-manifest.json').read_text())['sha256'][n] for n in manifest['sha256'])
allowed={'game_direct_bootstrap.py','game_residual_learning.py','game_batch.py','game_residual_trainer.py','game_neat.py','game_residual_migration.py','game_timing.py','version.py'}
assert {n for n in manifest['sha256'] if manifest['sha256'][n]!=prior['sha256'][n]}==allowed
assert all(Path(n).name.startswith(('check_','verify_')) for n in set(prior['sha256'])-set(manifest['sha256']))
def hashes(root):
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
def game():
 with sqlite3.connect((G/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  assert not db.execute('PRAGMA foreign_key_check').fetchall()
  names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
  tables={n:db.execute('SELECT * FROM "'+n+'" ORDER BY rowid').fetchall() for n in names}
 return {'logicalDatabaseSha256':hashlib.sha256(json.dumps(tables,sort_keys=True,default=str).encode()).hexdigest(),'tableCounts':{n:len(v) for n,v in tables.items()},'artifacts':{str(p.relative_to(G)):hashlib.sha256(p.read_bytes()).hexdigest() for p in G.rglob('*') if p.is_file() and not p.name.startswith('game.sqlite')}}
def health(label):
 out=W/(label+'.json');env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen','QT_QUICK_BACKEND=software']
 subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(W/'board-health.py'),'--output',str(out)],check=True,stdout=subprocess.DEVNULL)
 return json.loads(out.read_text())
def ready(label):
 deadline=time.monotonic()+90
 while True:
  result=health(label);beat=result.get('guiHeartbeat') or {}
  if result['service']['ActiveState']=='active' and beat.get('ready') and beat.get('ageSeconds',999)<5 and beat.get('pid')==result['runtimePid'] and not beat.get('pending'):return result
  assert time.monotonic()<deadline,'GUI readiness deadline';time.sleep(2)
before=ready('before-install-health');stamp=time.strftime('%Y%m%d-%H%M%S');B=Path('/var/backups/smartpc-maintenance')/('rollback-0.10.0-rc.2-'+stamp);B.mkdir(parents=True,mode=0o700);B.parent.chmod(0o700);stage=T.with_name('dashboard-maintenance-stage-'+stamp);shutil.copytree(R,stage);switched=False
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 original=game();configuration=hashes(H/'.config');(B/'state').mkdir()
 for name in ('.config','.local','game-runtime'):
  subprocess.run(['cp','-a','--reflink=auto',str(H/name),str(B/'state'/name)],check=True)
 for path in H.iterdir():
  if path.is_file() and (path.suffix in ('.json','.sqlite3') or path.name.startswith('events.sqlite3-')):
   subprocess.run(['cp','-a',str(path),str(B/'state'/path.name)],check=True)
 assert hashes(B/'state/.config')==configuration
 backup_game=B/'state/.local/share/SmartPC/SmartPC/game'
 assert {str(p.relative_to(backup_game)):hashlib.sha256(p.read_bytes()).hexdigest() for p in backup_game.rglob('*') if p.is_file() and not p.name.startswith('game.sqlite')}==original['artifacts']
 with sqlite3.connect((backup_game/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
 (B/'system').mkdir()
 for path in (Path('/etc/systemd/system/smartpc-dashboard.service'),Path('/etc/systemd/system/smartpc-dashboard.service.d'),Path('/etc/smartpc')):
  subprocess.run(['cp','-a',str(path),str(B/'system'/path.name)],check=True)
 (B/'preservation.json').write_text(json.dumps({'game':original,'configurationHashes':configuration,'beforeHealth':before},indent=2)+'\n')
 os.sync();T.rename(B/'runtime');stage.rename(T);switched=True
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True);after=ready('installed-health')
 assert after['version']==manifest['version'] and not after['manifestMismatches'] and after['service']['NRestarts']=='0'
 assert before['activeTheme']==after['activeTheme']==after['guiHeartbeat']['selection']
 assert before['bootId']==after['bootId'] and before['allPreferenceHashes']==after['allPreferenceHashes']
 assert hashes(H/'.config')==configuration,'Configuration bytes changed'
 assert game()==original,'Game data changed'
 (B/'backup-manifest.json').write_text(json.dumps({'version':'0.10.0-rc.2','sourceManifestSha256':hashlib.sha256((B/'runtime/release-manifest.json').read_bytes()).hexdigest(),'files':hashes(B)},indent=2)+'\n')
 receipt={'status':'passed','version':after['version'],'runtimeFiles':len(manifest['sha256']),'runtimeManifestSha256':hashlib.sha256((T/'release-manifest.json').read_bytes()).hexdigest(),'backup':str(B),'service':after['service'],'guiHeartbeat':after['guiHeartbeat'],'theme':after['activeTheme'],'sameBoot':True,'newOSReboot':False,'preferencesPreserved':True,'configurationBytesPreserved':True,'gameDatabasePreserved':True,'gameTableCounts':original['tableCounts'],'policyArtifactsPreserved':True,'policyArtifactCount':len(original['artifacts']),'nativeLibraryPreserved':True,'changedRuntimeFiles':sorted(allowed),'diagnosticScriptsRemoved':len(set(prior['sha256'])-set(manifest['sha256'])),'researchCodeDeployed':False,'physicalFramesQualified':False}
 (W/'installation-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
 subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
 if switched:
  T.rename(W/'failed-runtime');(B/'runtime').rename(T)
  if game()!=original:
   G.rename(W/'game-after-failure');subprocess.run(['cp','-a',str(backup_game),str(G)],check=True)
  if hashes(H/'.config')!=configuration:
   (H/'.config').rename(W/'config-after-failure');subprocess.run(['cp','-a',str(B/'state/.config'),str(H/'.config')],check=True)
 raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
