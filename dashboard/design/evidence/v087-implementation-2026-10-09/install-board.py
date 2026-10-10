"""Backed-up 0.8.7 installation and real Main activation, with rollback on failure."""
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v087-performance-proof';S=H/'smartpc-v087-performance-staging';SOURCE=S/'runtime';RUNTIME=Path('/opt/smartpc/dashboard')
manifest=json.loads((SOURCE/'release-manifest.json').read_text());qualification=json.loads((P/'qualification.json').read_text())
manifest_hash=hashlib.sha256((SOURCE/'release-manifest.json').read_bytes()).hexdigest()
assert qualification['status']=='passed' and qualification['manifestSha256']==manifest_hash
assert manifest['version']=='0.8.7-rc.1'
for name,digest in manifest['sha256'].items():assert hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()==digest,name
old=json.loads((RUNTIME/'release-manifest.json').read_text());assert old['version']=='0.8.6-rc.2'
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard']
egl=['QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl']
def run(args,name,graphics=[]):
 with (P/(name+'.txt')).open('w') as out:subprocess.run(['runuser','-u','smartpc','--','env',*env,*graphics,'python3',*map(str,args)],stdout=out,stderr=subprocess.STDOUT,check=True,timeout=120)
health=H/'v086-source-proof/board-health.py'
run([health,'--output',P/'baseline-health.json'],'baseline-health')
before=json.loads((P/'baseline-health.json').read_text());assert before['service']['ActiveState']=='active' and not before['manifestMismatches'] and before['activeTheme']['version']=='1.6.0'
backup=Path('/var/backups')/('smartpc-before-v087-performance-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'));backup.mkdir(mode=0o700)
started=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True);installed=False;backed=False
try:
 shutil.copytree(RUNTIME,backup/'dashboard')
 for src,label in ((H/'.config','config'),(H/'.local','local'),(Path('/var/cache/smartpc-dashboard'),'cache')):shutil.copytree(src,backup/label)
 backed=True
 new=RUNTIME.with_name('dashboard-v087.new');assert not new.exists();shutil.copytree(SOURCE,new)
 RUNTIME.rename(backup/'replaced-runtime')
 try:new.rename(RUNTIME)
 except BaseException:(backup/'replaced-runtime').rename(RUNTIME);raise
 installed=True
 run([P/'import-production.py'],'theme-import')
 target={'themeVersion':'1.6.1','bundleDigest':json.loads((P/'native-theme-preflight.json').read_text())['digest']}
 (P/'activation-target.json').write_text(json.dumps(target,indent=2)+'\n')
 base=[P/'activate-theme.py','--dashboard',RUNTIME,'--manifest',P/'activation-target.json']
 run([*base,'--output',P/'activation','--apply'],'activation',egl)
 run([*base,'--output',P/'cold-verify'],'cold-verify',egl)
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 deadline=time.monotonic()+45
 while True:
  run([health,'--output',P/'installed-health.json'],'installed-health')
  after=json.loads((P/'installed-health.json').read_text());hb=after['guiHeartbeat']
  if hb and hb['ready'] and 0<=hb['ageSeconds']<15:break
  assert time.monotonic()<deadline,'Fresh GUI heartbeat absent'
  time.sleep(2)
 identity={'id':'studio.applecalm','version':target['themeVersion'],'digest':target['bundleDigest']}
 assert after['version']==manifest['version'] and not after['manifestMismatches']
 assert after['activeTheme']==hb['selection']==identity and hb['pending'] is None
 assert before['preferenceHashes']==after['preferenceHashes']
 assert after['service']['ActiveState']=='active' and after['service']['NRestarts']=='0'
 journal=subprocess.check_output(['journalctl','-u','smartpc-dashboard','--since',started,'--no-pager'],text=True)
 warnings=[l for l in journal.splitlines() if any(x in l for x in ('ReferenceError','TypeError','Binding loop','QQmlApplicationEngine failed','Traceback','Segmentation fault'))];assert not warnings,warnings
 (P/'installed-journal.txt').write_text(journal)
 report={'status':'passed','version':manifest['version'],'files':len(manifest['sha256']),'manifestSha256':manifest_hash,'backup':str(backup),'nonAppearancePreferencesPreserved':True,'nonAppearancePreferenceCount':after['nonAppearancePreferenceCount'],'appearanceCustomizationsPreserved':True,'activeTheme':identity,'guiHeartbeat':hb,'qmlWarnings':warnings,'bootIdBefore':before['bootId'],'verifiedAt':time.time(),'restartScope':'service restart; reboot proof separate'}
 (P/'install-receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
except BaseException:
 subprocess.run(['systemctl','stop','smartpc-dashboard'],check=False)
 if installed:shutil.rmtree(RUNTIME);shutil.copytree(backup/'dashboard',RUNTIME)
 if backed:
  budgets={p.name:p.read_bytes() for p in (H/'.local/state/smartpc/casa').glob('*-budget.json')}
  for label,target in (('config',H/'.config'),('local',H/'.local'),('cache',Path('/var/cache/smartpc-dashboard'))):
   shutil.rmtree(target);shutil.copytree(backup/label,target);subprocess.run(['chown','-R','smartpc:smartpc',str(target)],check=True)
  for name,content in budgets.items():
   dest=H/'.local/state/smartpc/casa'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(content);subprocess.run(['chown','smartpc:smartpc',str(dest)],check=True)
 raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
