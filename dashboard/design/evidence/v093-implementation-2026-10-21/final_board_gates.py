"""Final ARM regression gates for the exact qualified artifact."""
from pathlib import Path
import hashlib,json,os,pwd,subprocess,time
STATE=Path('/var/lib/smartpc-dashboard');PROOF=STATE/'v093-proof'
SOURCE=STATE/'v093-stage/dashboard';RUNTIME=STATE/'v093-runtime/dashboard'
OUT=PROOF/'arm-final';OUT.mkdir(exist_ok=True)
user=pwd.getpwnam('smartpc');os.chown(OUT,user.pw_uid,user.pw_gid)
native=json.loads((PROOF/'native-wire-final/receipt.json').read_text());assert native['status']=='passed'
manifest=json.loads((SOURCE/'release-manifest.json').read_text())
assert manifest==native['sourceManifest']
for root in (SOURCE,RUNTIME):
 m=json.loads((root/'release-manifest.json').read_text())
 assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==v and native['sourceManifest']['sha256'].get(n)==v for n,v in m['sha256'].items())
env=dict(os.environ,HOME=str(STATE),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
PY=STATE/'game-runtime/bin/python';rows=[]
def drop():
 os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
for test in ('check_system_performance','check_state_availability','check_app_lifecycle','check_notifications','check_notification_updates','check_notification_consultation_ui','check_network','check_network_metrics','check_casa','check_dashboard_summary','check_dashboard_optimization_ui','check_sport_ui','check_theme_api_contract','check_theme_optimization'):
 started=time.monotonic()
 with (OUT/(test+'.txt')).open('w') as log:r=subprocess.run([str(PY),str(SOURCE/(test+'.py'))],env=env,preexec_fn=drop,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 rows.append(dict(test=test,exitCode=r.returncode,seconds=time.monotonic()-started));print(json.dumps(rows[-1]),flush=True)
 assert r.returncode==0,test
(OUT/'receipt.json').write_text(json.dumps(dict(status='passed',rows=rows,sourceManifest=manifest),indent=2)+'\n')
