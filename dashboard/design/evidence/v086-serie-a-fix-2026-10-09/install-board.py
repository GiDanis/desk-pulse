"""Qualify targeted Serie A routes natively, then install with rollback."""
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v086-seriea-proof';STAGE=H/'smartpc-v086-seriea-staging';PROJECT=STAGE/'project';SOURCE=STAGE/'runtime';RUNTIME=Path('/opt/smartpc/dashboard')
P.mkdir(exist_ok=True);subprocess.run(['chown','-R','smartpc:smartpc',str(P)],check=True)
manifest=json.loads((SOURCE/'release-manifest.json').read_text());old=json.loads((RUNTIME/'release-manifest.json').read_text())
assert manifest['version']=='0.8.6-rc.2' and old['version']=='0.8.6-rc.1'
for name,digest in manifest['sha256'].items():
 assert hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()==digest,name
 assert hashlib.sha256((PROJECT/'dashboard'/name).read_bytes()).hexdigest()==digest,name
changed=sorted(k for k in manifest['sha256'] if manifest['sha256'][k]!=old['sha256'].get(k))
assert changed==['Main.qml','check_dashboard_summary.py','check_sport_ui.py','check_ux_consolidation_ui.py','check_view_organization_ui.py','dashboard_summary.py','state.py','version.py'],changed
(P/'delta-scope.json').write_text(json.dumps({'changedFiles':changed,'themeAndProviderFilesUnchanged':True},indent=2)+'\n')
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard']
egl=['QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl']
software=['QT_QPA_PLATFORM=offscreen','QT_QUICK_BACKEND=software']
def run(arguments,log,graphics=software,timeout=180):
 with (P/log).open('w') as stream:subprocess.run(['runuser','-u','smartpc','--','env',*env,*graphics,'python3',*map(str,arguments)],stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=timeout)
health=H/'v086-source-proof/board-health.py'
run([health,'--output',P/'baseline.json'],'baseline.txt');before=json.loads((P/'baseline.json').read_text());assert not before['manifestMismatches'] and before['service']['ActiveState']=='active'
assert before['activeTheme']['id']=='studio.applecalm' and before['activeTheme']['version']=='1.6.0'
backup=Path('/var/backups')/('smartpc-before-v086-seriea-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'));backup.mkdir(mode=0o700)
started=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True);installed=False;backed=False
try:
 shutil.copytree(RUNTIME,backup/'dashboard')
 for src,label in ((H/'.config','config'),(H/'.local','local'),(Path('/var/cache/smartpc-dashboard'),'cache')):shutil.copytree(src,backup/label)
 backed=True
 run([PROJECT/'dashboard/check_dashboard_summary.py'],'summary.txt')
 run([PROJECT/'dashboard/check_sport_ui.py'],'sport-ui.txt')
 run([PROJECT/'dashboard/check_sport_team_ui.py'],'team-ui.txt')
 run([PROJECT/'dashboard/check_ux_consolidation_ui.py'],'ux.txt')
 profiles=[]
 for theme,palette in [('base','day'),('functional','night'),('apple','day'),('apple','night')]:
  name=theme+'-'+palette
  print('Native dashboard profile: '+name,flush=True)
  run([PROJECT/'dashboard/check_view_organization_ui.py','--theme',theme,'--palette',palette,'--capture-dir',P/name],name+'.txt',egl,240)
  report=json.loads((P/name/'report.json').read_text());assert report['status']=='passed' and report['platform']=='eglfs' and report['serieAAllTenGamesAccessible'] and report['favouriteRouteSeparated'] and not report['qmlWarnings']
  profiles.append(name)
 (P/'qualification.json').write_text(json.dumps({'status':'passed','profiles':profiles,'manifestSha256':hashlib.sha256((SOURCE/'release-manifest.json').read_bytes()).hexdigest(),'bundleAndApiUnchanged':True,'providerLiveQualification':'not claimed'},indent=2)+'\n')
 new=RUNTIME.with_name('dashboard-seriea.new');assert not new.exists();shutil.copytree(SOURCE,new)
 RUNTIME.rename(backup/'replaced-runtime')
 try:new.rename(RUNTIME)
 except BaseException:(backup/'replaced-runtime').rename(RUNTIME);raise
 installed=True
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 deadline=time.monotonic()+45
 while True:
  run([health,'--output',P/'installed-health.json'],'installed-health.txt')
  after=json.loads((P/'installed-health.json').read_text());hb=after['guiHeartbeat']
  if hb and hb['ready'] and 0<=hb['ageSeconds']<15:break
  assert time.monotonic()<deadline,'Fresh GUI heartbeat absent'
  time.sleep(2)
 assert after['version']==manifest['version'] and not after['manifestMismatches']
 assert after['activeTheme']==before['activeTheme'] and hb['selection']==after['activeTheme'] and hb['pending'] is None
 assert before['allPreferenceHashes']==after['allPreferenceHashes']
 assert after['service']['ActiveState']=='active' and after['service']['NRestarts']=='0'
 journal=subprocess.check_output(['journalctl','-u','smartpc-dashboard','--since',started,'--no-pager'],text=True)
 warnings=[l for l in journal.splitlines() if any(x in l for x in ('ReferenceError','TypeError','Binding loop','QQmlApplicationEngine failed','Traceback','Segmentation fault'))];assert not warnings,warnings
 (P/'installed-journal.txt').write_text(journal)
 report={'status':'passed','version':manifest['version'],'files':len(manifest['sha256']),'backup':str(backup),'allPreferencesPreserved':True,'activeTheme':after['activeTheme'],'guiHeartbeat':hb,'profiles':profiles,'qmlWarnings':warnings,'bootIdBefore':before['bootId'],'verifiedAt':time.time(),'restartScope':'service restart; reboot proof separate'}
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
