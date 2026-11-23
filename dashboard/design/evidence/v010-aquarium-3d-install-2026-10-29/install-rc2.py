"""Install only the qualified Aquarium delta; rollback automatically on failure."""
from pathlib import Path
import hashlib,json,os,shutil,sqlite3,subprocess,time
H=Path('/var/lib/smartpc-dashboard');W=H/'maintenance-work';R=Path('/opt/smartpc/dashboard');C=W/'runtime';PY=H/'game-runtime/bin/python';DATA=H/'.local/share/SmartPC/SmartPC';G=DATA/'game'
def hashes(path):return {str(f.relative_to(path)):hashlib.sha256(f.read_bytes()).hexdigest() for f in path.rglob('*') if f.is_file()}
def game():
 with sqlite3.connect((G/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
  logical=hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest()
 return {'logicalSha256':logical,'artifacts':{str(f.relative_to(G)):hashlib.sha256(f.read_bytes()).hexdigest() for f in G.rglob('*') if f.is_file() and not f.name.startswith('game.sqlite')}}
def ready(label):
 deadline=time.monotonic()+90
 while True:
  f=W/(label+'.json');cmd=['runuser','-u','smartpc','--','env','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen','QT_QUICK_BACKEND=software',str(PY),str(W/'board-health.py'),'--output',str(f)]
  subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL);r=json.loads(f.read_text());b=r.get('guiHeartbeat') or {}
  if r['service']['ActiveState']=='active' and b.get('ready') and b.get('ageSeconds',999)<5 and b.get('pid')==r['runtimePid'] and not b.get('pending'):return r
  assert time.monotonic()<deadline,'GUI readiness deadline';time.sleep(2)
prior=json.loads((R/'release-manifest.json').read_text());new=json.loads((C/'release-manifest.json').read_text());qualification=json.loads((W/'qualification-rc2-receipt.json').read_text());backup=json.loads((W/'backup-receipt.json').read_text());B=Path(backup['backup'])
assert prior['version']=='0.10.2-rc.1' and new['version']=='0.10.2-rc.2' and backup['status']==qualification['status']=='passed'
assert qualification['runtimeManifestSha256']==hashlib.sha256((C/'release-manifest.json').read_bytes()).hexdigest() and len(qualification['cases'])==1
assert new['sourceBaseline']['manifestSha256']==hashlib.sha256((B/'runtime/release-manifest.json').read_bytes()).hexdigest()
for root,m in [(R,prior),(C,new)]:assert all(hashlib.sha256((root/f).read_bytes()).hexdigest()==v for f,v in m['sha256'].items())
assert all(new['sha256'][f]==v for f,v in prior['sha256'].items() if f.startswith('game') or f=='libsmartpc_game_native.so')
before=ready('before-switch-health');switched=False;stage=W/'install-ready';shutil.copytree(C,stage)
subprocess.run(['chown','-R','root:root',str(stage)],check=True)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 original=game();config=hashes(H/'.config');boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
 assert original==json.loads((B/'preservation.json').read_text())['game'],'Game changed since verified backup'
 for source,dest in [(H/'.config',W/'preinstall-rc2-config'),(DATA/'theme-activation.json',W/'preinstall-rc2-theme-activation.json')]:subprocess.run(['cp','-a',str(source),str(dest)],check=True)
 R.rename(W/'previous-rc1-runtime');stage.rename(R);switched=True;os.sync()
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True);after=ready('installed-health')
 assert after['version']==new['version'] and not after['manifestMismatches'] and after['service']['NRestarts']=='0'
 assert before['activeTheme']==after['activeTheme']==after['guiHeartbeat']['selection']
 assert before['allPreferenceHashes']==after['allPreferenceHashes'] and hashes(H/'.config')==config
 assert game()==original and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
 report={'status':'passed','version':new['version'],'runtimeFiles':len(new['sha256']),'runtimeManifestSha256':hashlib.sha256((R/'release-manifest.json').read_bytes()).hexdigest(),'backup':str(B),'service':after['service'],'guiHeartbeat':after['guiHeartbeat'],'theme':after['activeTheme'],'preferencesPreserved':True,'configurationBytesPreserved':True,'gameDatabasePreserved':True,'gameArtifactsPreserved':len(original['artifacts']),'gameCodeAndNativeLibraryUnchanged':True,'sameBoot':True,'newOSReboot':False,'newThemeApi':'2.14','surfaces':71,'physicalFramesQualified':False,'qualificationReceiptSha256':hashlib.sha256((W/'qualification-rc2-receipt.json').read_bytes()).hexdigest()}
 (W/'installation-rc2-receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
except BaseException:
 subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
 if switched:
  R.rename(W/'failed-runtime');(W/'previous-rc1-runtime').rename(R)
  subprocess.run(['cp','-a',str(W/'preinstall-rc2-theme-activation.json'),str(DATA/'theme-activation.json')],check=True)
  if hashes(H/'.config')!=config:
   (H/'.config').rename(W/'config-after-failure');subprocess.run(['cp','-a',str(W/'preinstall-rc2-config'),str(H/'.config')],check=True)
 raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
