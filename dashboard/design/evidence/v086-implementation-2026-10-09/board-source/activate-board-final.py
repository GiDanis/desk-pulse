"""Backed-up theme upgrade using the production Main activation handshake."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
import time
P=Path('/var/lib/smartpc-dashboard/v086-source-proof');H=Path('/var/lib/smartpc-dashboard')
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard']
egl=['QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl']
def run(args,log,graphics=[]):
 with (P/log).open('w') as out:subprocess.run(['runuser','-u','smartpc','--','env',*env,*graphics,'python3',*map(str,args)],stdout=out,stderr=subprocess.STDOUT,check=True,timeout=90)
run([P/'board-health.py','--output',P/'activation-baseline.json'],'activation-baseline.txt')
before=json.loads((P/'activation-baseline.json').read_text());assert before['service']['ActiveState']=='active' and not before['manifestMismatches']
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');backup=Path('/var/backups')/('smartpc-before-v086-apple-activation-'+stamp);backup.mkdir(mode=0o700)
started=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
backed=False
try:
 for name in ('.config','.local'):shutil.copytree(H/name,backup/name)
 backed=True
 run([P/'import-production.py'],'theme-import-before-activation.txt')
 base=[P/'activate-theme.py','--dashboard','/opt/smartpc/dashboard','--manifest',P/'activation-target.json']
 run([*base,'--output',P/'activation','--apply'],'activation.txt',egl)
 run([*base,'--output',P/'cold-verify'],'cold-verify.txt',egl)
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 deadline=time.monotonic()+45
 while True:
  run([P/'board-health.py','--output',P/'activation-health.json'],'activation-health.txt')
  after=json.loads((P/'activation-health.json').read_text());hb=after['guiHeartbeat']
  if hb and hb['ready'] and 0<=hb['ageSeconds']<15:break
  assert time.monotonic()<deadline,'Fresh GUI readiness missing'
  time.sleep(2)
 target=json.loads((P/'activation-target.json').read_text());identity={'id':'studio.applecalm','version':target['themeVersion'],'digest':target['bundleDigest']}
 assert after['activeTheme']==identity and hb['selection']==identity and hb['pending'] is None
 assert before['preferenceHashes']==after['preferenceHashes']
 assert not after['manifestMismatches'] and after['service']['NRestarts']=='0'
 journal=subprocess.check_output(['journalctl','-u','smartpc-dashboard','--since',started,'--no-pager'],text=True)
 warnings=[line for line in journal.splitlines() if any(x in line for x in ('ReferenceError','TypeError','Binding loop','QQmlApplicationEngine failed','Traceback','Segmentation fault'))]
 assert not warnings,warnings
 (P/'activation-journal.txt').write_text(journal)
 report={'status':'passed','backup':str(backup),'themeBefore':before['activeTheme'],'activeTheme':identity,'appearanceCustomizationsPreserved':True,'nonAppearancePreferencesPreserved':True,'coldStartVerified':True,'guiHeartbeat':hb,'qmlWarnings':warnings,'verifiedAt':time.time()}
 (P/'activation-receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
except BaseException:
 subprocess.run(['systemctl','stop','smartpc-dashboard'],check=False)
 if backed:
  budgets={p.name:p.read_bytes() for p in (H/'.local/state/smartpc/casa').glob('*-budget.json')}
  for name in ('.config','.local'):
   shutil.rmtree(H/name);shutil.copytree(backup/name,H/name)
   subprocess.run(['chown','-R','smartpc:smartpc',str(H/name)],check=True)
  for name,content in budgets.items():
   dest=H/'.local/state/smartpc/casa'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(content);subprocess.run(['chown','smartpc:smartpc',str(dest)],check=True)
 raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
