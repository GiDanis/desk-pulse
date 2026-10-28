from pathlib import Path
import hashlib,json,os,subprocess,time
ROOT=Path('/home/giuseppe/Documenti/Workspace/SmartPC')
OUT=Path(__file__).resolve().parent
PY='/home/giuseppe/.cache/smartpc-population-py312/bin/python'
env=dict(os.environ,QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
rows=[]
def run(name,args):
 started=time.monotonic()
 with (OUT/(name+'.txt')).open('w') as log:r=subprocess.run([PY,*map(str,args)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=360)
 rows.append(dict(name=name,exitCode=r.returncode,seconds=time.monotonic()-started))
 (OUT/'pc-final-progress.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(json.dumps(rows[-1]),flush=True)
 assert r.returncode==0,name
for test in ('check_system_performance','check_state_availability','check_app_lifecycle','check_notifications','check_notification_updates','check_notification_consultation_ui','check_network','check_network_metrics','check_casa','check_dashboard_summary','check_dashboard_optimization_ui','check_sport_ui','check_theme_api_contract','check_theme_optimization'):
 run(test+'-qualified',[ROOT/'dashboard'/(test+'.py')])
probe=ROOT/'dashboard/design/evidence/v093-systemwide-analysis-2026-10-21/probe_all_surfaces.py'
for theme,variant in [('apple','day'),('apple','night'),('base','day'),('functional','day')]:
 name=theme+'-'+variant+'-qualified-surfaces'
 args=[probe,'--source',ROOT/'dashboard','--theme',theme,'--variant',variant,'--output',OUT/(name+'.json')]
 if (theme,variant)!=('apple','day'):args+=['--unique-surfaces']
 run(name,args)
manifest=json.loads(Path('/tmp/smartpc-v093-selected-runtime/release-manifest.json').read_text())
assert all(hashlib.sha256((ROOT/'dashboard'/n).read_bytes()).hexdigest()==v for n,v in manifest['sha256'].items() if n!='libsmartpc_game_native.so')
receipt=dict(status='passed',rows=rows,productSourceHashes=manifest['sha256'],diagnosticSourceHashes={n:v for n,v in manifest['sha256'].items() if n.startswith('check_')})
(OUT/'final-pc-gates.json').write_text(json.dumps(receipt,indent=2)+'\n')
