"""Deliver rc.2 plus Apple1.6.5 with quiescent backup and automatic recovery."""
from pathlib import Path
import hashlib,json,os,shutil,sqlite3,subprocess,time
H=Path('/var/lib/smartpc-dashboard');P=H/'aquarium-completion-20261026';R=P/'runtime/dashboard';T=Path('/opt/smartpc/dashboard');D=H/'.local/share/SmartPC/SmartPC';G=D/'game';PY=H/'game-runtime/bin/python'
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen','QT_QUICK_BACKEND=software','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
def health(label):
 out=P/(label+'.json');subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(H/'aquarium-proof-20261025/board-health.py'),'--output',str(out)],check=True,stdout=subprocess.DEVNULL);return json.loads(out.read_text())
def game(root=G):
 with sqlite3.connect((root/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
  data={n:db.execute('SELECT * FROM "'+n+'" ORDER BY rowid').fetchall() for n in tables}
 return {'database':hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),'artifacts':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and not p.name.startswith('game.sqlite')}}
native=json.loads((P/'native-receipt.json').read_text());manifest=json.loads((R/'release-manifest.json').read_text());prior=json.loads((T/'release-manifest.json').read_text())
assert native['status']=='passed' and native['preferencesPreserved'] and len(native['cases'])==4
assert native['runtimeManifestSha256']==hashlib.sha256((R/'release-manifest.json').read_bytes()).hexdigest()
assert manifest['version']=='0.10.0-rc.2' and prior['version']=='0.10.0-rc.1'
assert all(hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in manifest['sha256'].items())
assert all(hashlib.sha256((T/n).read_bytes()).hexdigest()==h for n,h in prior['sha256'].items())
delta=[n for n in set(prior['sha256'])|set(manifest['sha256']) if prior['sha256'].get(n)!=manifest['sha256'].get(n)]
assert set(delta)=={'check_aquarium_ui.py','version.py'}
identity=native['theme'];assert identity['version']=='1.6.5'
deadline=time.monotonic()+75
while True:
 before=health('before-install');beat=before.get('guiHeartbeat') or {}
 if beat.get('ready') and beat.get('ageSeconds',999)<5 and beat.get('pid')==before['runtimePid'] and not beat.get('pending'):break
 assert time.monotonic()<deadline,'Baseline GUI readiness deadline'
 time.sleep(2)
assert before['activeTheme']['version']=='1.6.4' and not before['manifestMismatches']
stamp=time.strftime('%Y%m%d-%H%M%S');backup=H/'aquarium-backups'/('completion-'+stamp);backup.mkdir(parents=True,mode=0o700);stage=T.with_name('dashboard-completion-stage-'+stamp);old=T.with_name('dashboard-before-completion-'+stamp);shutil.copytree(R,stage)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True);switched=False
try:
 original=game();shutil.copytree(G,backup/'game');shutil.copytree(H/'.config/SmartPC',backup/'config')
 theme_backup=backup/'themes';theme_backup.mkdir()
 for p in D.glob('theme-*'):
  if p.is_dir():shutil.copytree(p,theme_backup/p.name)
  elif p.is_file():shutil.copy2(p,theme_backup/p.name)
 os.sync();T.rename(old);stage.rename(T);switched=True
 with (P/'activation.log').open('w') as log:subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(P/'activate-theme.py'),'--stage',str(P)],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=120)
 activation=json.loads((P/'activation.json').read_text());assert activation['after']==identity and activation['appearanceOptionsPreserved'] and activation['otherThemeProfilesPreserved']
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True);deadline=time.monotonic()+90
 while True:
  time.sleep(2);after=health('installed');beat=after.get('guiHeartbeat') or {}
  if after['service']['ActiveState']=='active' and beat.get('ready') and beat.get('ageSeconds',999)<5 and beat.get('pid')==after['runtimePid'] and after['runtimePid']!=before['runtimePid'] and not beat.get('pending'):break
  assert time.monotonic()<deadline,'GUI readiness deadline'
 assert after['version']=='0.10.0-rc.2' and not after['manifestMismatches'] and after['service']['NRestarts']=='0'
 assert after['activeTheme']==beat['selection']==identity and before['bootId']==after['bootId']
 keys=set(before['allPreferenceHashes'])|set(after['allPreferenceHashes']);changed=[k for k in keys if before['allPreferenceHashes'].get(k)!=after['allPreferenceHashes'].get(k)]
 assert set(changed)<={'appearance/config','appearance/themeOverrides'},changed
 assert game()==original,'Game data changed'
 receipt={'status':'passed','version':after['version'],'files':len(manifest['sha256']),'themeBefore':before['activeTheme'],'activeTheme':identity,'service':after['service'],'guiHeartbeat':beat,'manifestMismatches':after['manifestMismatches'],'backup':str(backup),'runtimeRollback':str(old),'gameDatabasePreserved':True,'policyArtifactsPreserved':True,'policyArtifactCount':len(original['artifacts']),'allOtherPreferencesPreserved':True,'appearanceOptionsPreserved':True,'otherThemeProfilesPreserved':True,'changedPreferenceKeys':sorted(changed),'sameBoot':True,'newOSReboot':False,'physicalFramesQualified':False,'runtimeDelta':sorted(delta),'runtimeManifestSha256':hashlib.sha256((T/'release-manifest.json').read_bytes()).hexdigest()}
 (P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
 subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
 if switched:
  T.rename(T.with_name('dashboard-completion-failed-'+stamp));old.rename(T)
  try:game_changed=game()!=original
  except Exception:game_changed=True
  if game_changed:
   G.rename(G.with_name('game-after-failed-completion-'+stamp));shutil.copytree(backup/'game',G);subprocess.run(['chown','-R','smartpc:smartpc',str(G)],check=True)
 if (backup/'config').exists():
  shutil.copytree(backup/'config',H/'.config/SmartPC',dirs_exist_ok=True)
  failed=backup/'failed-theme-state';failed.mkdir()
  for p in D.glob('theme-*'):shutil.move(str(p),failed/p.name)
  for p in theme_backup.iterdir():
   if p.is_dir():shutil.copytree(p,D/p.name)
   else:shutil.copy2(p,D/p.name)
  subprocess.run(['chown','-R','smartpc:smartpc',str(H/'.config/SmartPC')],check=True)
  for p in D.glob('theme-*'):subprocess.run(['chown','-R','smartpc:smartpc',str(p)],check=True)
 raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
