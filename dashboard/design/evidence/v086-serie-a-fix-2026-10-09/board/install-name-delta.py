"""Final normalized standing-name alias; 18 native projection cases, same GUI."""
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v086-seriea-proof';D=H/'smartpc-v086-seriea-name-delta';R=Path('/opt/smartpc/dashboard');health=H/'v086-source-proof/board-health.py'
first=json.loads((P/'install-receipt.json').read_text());assert first['status']=='passed'
manifest=json.loads((D/'release-manifest.json').read_text());old=json.loads((R/'release-manifest.json').read_text());changed={k for k in manifest['sha256'] if manifest['sha256'][k]!=old['sha256'].get(k)}
assert changed=={'dashboard_summary.py','check_dashboard_summary.py'},changed
for name in changed:assert hashlib.sha256((D/name).read_bytes()).hexdigest()==manifest['sha256'][name]
env=['PYTHONPATH=/opt/smartpc/dashboard','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen','QT_QUICK_BACKEND=software']
def run(args,log):
 with (P/log).open('w') as out:subprocess.run(['runuser','-u','smartpc','--','env',*env,'python3',*map(str,args)],stdout=out,stderr=subprocess.STDOUT,check=True,timeout=60)
run([health,'--output',P/'name-baseline.json'],'name-baseline.txt');before=json.loads((P/'name-baseline.json').read_text());assert not before['manifestMismatches']
run([D/'check_dashboard_summary.py'],'name-summary.txt')
backup=Path('/var/backups')/('smartpc-before-v086-seriea-name-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'));backup.mkdir(mode=0o700)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True);installed=False
try:
 shutil.copytree(R,backup/'dashboard');candidate=R.with_name('dashboard-seriea-name.new');assert not candidate.exists();shutil.copytree(R,candidate)
 for name in changed:shutil.copyfile(D/name,candidate/name)
 shutil.copyfile(D/'release-manifest.json',candidate/'release-manifest.json')
 for name,digest in manifest['sha256'].items():assert hashlib.sha256((candidate/name).read_bytes()).hexdigest()==digest,name
 R.rename(backup/'replaced-runtime')
 try:candidate.rename(R)
 except BaseException:(backup/'replaced-runtime').rename(R);raise
 installed=True
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 deadline=time.monotonic()+45
 while True:
  run([health,'--output',P/'final-health.json'],'final-health.txt');after=json.loads((P/'final-health.json').read_text());hb=after['guiHeartbeat']
  if hb and hb['ready'] and 0<=hb['ageSeconds']<15:break
  assert time.monotonic()<deadline
  time.sleep(2)
 assert not after['manifestMismatches'] and before['allPreferenceHashes']==after['allPreferenceHashes'] and before['activeTheme']==after['activeTheme']
 assert hb['selection']==after['activeTheme'] and hb['pending'] is None and after['service']['NRestarts']=='0'
 report={'status':'passed','changedFiles':sorted(changed),'scope':'Standing name accepts normalized team as well as legacy teamName; layout, navigation, providers, bundle and public contract unchanged','nativeProjectionTests':18,'manifestSha256':hashlib.sha256((D/'release-manifest.json').read_bytes()).hexdigest(),'backup':str(backup),'allPreferencesPreserved':True,'activeTheme':after['activeTheme'],'guiHeartbeat':hb,'fullNativeQualification':'qualification.json','verifiedAt':time.time()}
 (P/'name-delta-receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
except BaseException:
 if installed:
  subprocess.run(['systemctl','stop','smartpc-dashboard'],check=False);shutil.rmtree(R);shutil.copytree(backup/'dashboard',R)
 raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
