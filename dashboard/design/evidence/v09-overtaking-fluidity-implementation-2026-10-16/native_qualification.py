"""Private prolonged workloads; always restore the installed Dashboard."""
from pathlib import Path
import subprocess,json,time,hashlib,os
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-overtake-proof';PROJECT=H/'smartpc-overtake-project';S=PROJECT/'dashboard';PY=H/'game-runtime/bin/python'
manifest=json.loads((S/'release-manifest.json').read_text());assert manifest['version']=='0.9.0-rc.22'
assert all(hashlib.sha256((S/k).read_bytes()).hexdigest()==v for k,v in manifest['sha256'].items())
assert not any('spawn_main' in x or 'multiprocessing.spawn' in x for x in subprocess.check_output(['ps','-eo','args='],text=True).splitlines()),'Training active'
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','SMARTPC_GAME_PRESENTER=timer','SMARTPC_GAME_TRACE=1','SMARTPC_MATURE_PPO='+str(H/'overtake-private/crono.json')]
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
def run(label,script,args,timeout):
 report_path=P/label/'report.json'
 if report_path.exists() and json.loads(report_path.read_text()).get('status')=='passed':
  print('Already complete '+label,flush=True);return
 print('Begin '+label,flush=True)
 with (P/(label+'.txt')).open('w') as out:
  subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(S/script),*args,'--output',str(P/label)],cwd=PROJECT,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=timeout)
 result=json.loads((P/label/'report.json').read_text());assert result['status']=='passed' and not result['qmlWarnings'];print('Complete '+label,flush=True)
try:
 run('functional-flows','check_game_residual_ui.py',['--theme','base','--race-seconds','5'],400)
 for theme in ('base','functional','apple'):
  run('timing-'+theme,'check_game_timing_ui.py',['--theme',theme,'--sample','8'],350)
 for label,theme,load,seconds,segments,mature in [
  ('long-race-base','base','race',120,5,False),
  ('long-qualifying-functional','functional','qualification',120,5,False),
  ('long-race-apple','apple','race',120,5,False),
  ('long-mature-ppo','apple','ppo',600,1,True),
  ('long-mature-sac','apple','sac',600,1,True),
  ('long-mature-tactic-td3','apple','tactic',600,1,True)]:
  args=['--theme',theme,'--load',load,'--seconds',str(seconds),'--segments',str(segments),'--trace']
  if mature:args+=['--mature']
  run(label,'check_game_fluidity_ui.py',args,1000)
 # Same scene without tracing estimates observer cost, separately from gates.
 run('trace-off-apple','check_game_fluidity_ui.py',['--theme','apple','--load','race','--seconds','120'],350)
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
