"""Manifest-checked exchange from the tested ARM candidate, automatic recovery."""
from pathlib import Path
import hashlib,json,os,shutil,sqlite3,subprocess,sys,time
H=Path('/var/lib/smartpc-dashboard');P=H/'aquarium-proof-20261025'
R=H/'aquarium-frozen-delivery/dashboard';T=Path('/opt/smartpc/dashboard')
D=H/'.local/share/SmartPC/SmartPC';G=D/'game';PY=H/'game-runtime/bin/python'
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen','QT_QUICK_BACKEND=software','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
def health(label):
 target=P/(label+'.json')
 subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(P/'board-health.py'),'--output',str(target)],check=True,stdout=subprocess.DEVNULL)
 return json.loads(target.read_text())
def preserved():
 with sqlite3.connect((G/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
  rows={n:db.execute('SELECT * FROM "'+n+'" ORDER BY rowid').fetchall() for n in tables}
 return {'database':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),'artifacts':{str(p.relative_to(G)):hashlib.sha256(p.read_bytes()).hexdigest() for p in G.rglob('*') if p.is_file() and not p.name.startswith('game.sqlite')}}
manifest=json.loads((R/'release-manifest.json').read_text());native=json.loads((P/'qualification-receipt.json').read_text())
assert manifest['version']=='0.10.0-rc.1'
assert all(hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in manifest['sha256'].items())
assert native['preferencesPreserved'] and native['serviceRestarted'] and native['sameSourceForAllCases']
assert all(native['sourceHashes'].get(n)==h for n,h in manifest['sha256'].items()),'Distributed bytes differ from tested source'
reports=native['results'];assert len(reports)==15,len(reports)
assert all(r['status']=='passed' and not r.get('warnings') and not r.get('networkAttempts') for r in reports)
# Every nominal replica and the duration test must meet the frozen software gate.
by_case={r['caseId']:r for r in reports}
assert all(by_case[n]['near60SoftwareGate'] for n in ('nominal-1','nominal-2','nominal-3','soak30'))
assert by_case['soak30']['seconds']>=1800
deadline=time.monotonic()+60
while True:
 before=health('before-install')
 if before.get('guiHeartbeat') and before['guiHeartbeat']['ready'] and before['guiHeartbeat']['ageSeconds']<5:break
 assert time.monotonic()<deadline,'Baseline GUI not ready'
 time.sleep(2)
assert before['version']=='0.9.4-rc.3' and not before['manifestMismatches']
assert before['guiHeartbeat']['ready'] and before['activeTheme']['version']=='1.6.4'
old_manifest=json.loads((T/'release-manifest.json').read_text());scope=json.loads((P/'runtime-scope.json').read_text())
allowed=set(scope['selectedOverlay']);delta=[n for n in set(old_manifest['sha256'])|set(manifest['sha256']) if manifest['sha256'].get(n)!=old_manifest['sha256'].get(n)]
assert set(delta)<=allowed,(set(delta)-allowed)
stamp=time.strftime('%Y%m%d-%H%M%S');stage=T.with_name('dashboard-aquarium-stage-'+stamp);old=T.with_name('dashboard-before-aquarium-'+stamp);backup=H/'aquarium-backups'/stamp
backup.mkdir(parents=True,mode=0o700);shutil.copytree(R,stage)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True);switched=False
try:
 original=preserved();shutil.copytree(G,backup/'game');shutil.copytree(H/'.config/SmartPC',backup/'config')
 controls=backup/'theme-control';controls.mkdir()
 for p in D.glob('theme-*.json'):shutil.copy2(p,controls/p.name)
 os.sync();T.rename(old);stage.rename(T);switched=True
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 deadline=time.monotonic()+90
 while True:
  time.sleep(2);after=health('installed');beat=after.get('guiHeartbeat') or {}
  if after['service']['ActiveState']=='active' and beat.get('ready') and beat.get('ageSeconds',999)<5 and beat.get('pid')==after['runtimePid'] and after['runtimePid']!=before['runtimePid'] and not beat.get('pending'):break
  assert time.monotonic()<deadline,'Installed GUI not ready'
 assert after['version']==manifest['version'] and not after['manifestMismatches']
 assert after['service']['NRestarts']=='0' and before['bootId']==after['bootId']
 assert before['allPreferenceHashes']==after['allPreferenceHashes'],'Preference change'
 assert after['activeTheme']==before['activeTheme']==beat['selection'],'Apple identity changed'
 current=preserved();assert original==current,'Game data/artifacts changed'
 receipt={'status':'passed','version':after['version'],'files':len(manifest['sha256']),'activeTheme':after['activeTheme'],'service':after['service'],'guiHeartbeat':beat,'manifestMismatches':after['manifestMismatches'],'runtimeRollback':str(old),'backup':str(backup),'gameDatabasePreserved':True,'policyArtifactsPreserved':True,'policyArtifactCount':len(original['artifacts']),'allPreferencesPreserved':True,'sameBoot':True,'newOSReboot':False,'physicalFramesQualified':False,'runtimeDelta':sorted(delta),'manifestSha256':hashlib.sha256((T/'release-manifest.json').read_bytes()).hexdigest()}
 (P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
 subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
 if switched:T.rename(T.with_name('dashboard-aquarium-failed-'+stamp));old.rename(T)
 if switched and (backup/'game').exists():
  # Preserve the failed runtime's state too, then restore the quiescent backup.
  G.rename(G.with_name('game-after-failed-aquarium-'+stamp))
  shutil.copytree(backup/'game',G)
  subprocess.run(['chown','-R','smartpc:smartpc',str(G)],check=True)
 if (backup/'config').exists():
  shutil.copytree(backup/'config',H/'.config/SmartPC',dirs_exist_ok=True)
  for p in (backup/'theme-control').glob('*'):shutil.copy2(p,D/p.name)
  subprocess.run(['chown','-R','smartpc:smartpc',str(H/'.config/SmartPC')],check=True)
  for p in D.glob('theme-*.json'):subprocess.run(['chown','smartpc:smartpc',str(p)],check=True)
 raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
