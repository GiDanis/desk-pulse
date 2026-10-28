"""Final source checks after long measured segments, without concurrent workload."""
from pathlib import Path
import subprocess,json,hashlib
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-overtake-proof';S=H/'smartpc-overtake-project/dashboard';PY=H/'game-runtime/bin/python'
for name in ('long-race-base','long-qualifying-functional','long-race-apple','long-mature-ppo','long-mature-sac','long-mature-tactic-td3','trace-off-apple'):
 d=json.loads((P/name/'report.json').read_text());assert d['status']=='passed' and not d['qmlWarnings']
m=json.loads((S/'release-manifest.json').read_text());assert all(hashlib.sha256((S/n).read_bytes()).hexdigest()==v for n,v in m['sha256'].items())
assert not any('spawn_main' in x or 'multiprocessing.spawn' in x for x in subprocess.check_output(['ps','-eo','args='],text=True).splitlines()),'Production training active'
base=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 with (P/'arm-tests-retained-final.txt').open('w') as out:
  subprocess.run(['runuser','-u','smartpc','--','env',*base,'QT_QPA_PLATFORM=offscreen','PYTHONPATH='+str(S),str(PY),'-m','unittest','check_game_overtaking','check_game_residual.ResidualTests.test_trainer_json_resume','check_game_residual.ResidualTests.test_mode_change_preserves_learner_not_old_episode','-q'],cwd=S,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=350)
 print('Final ARM tests passed',flush=True)
 env=base+['QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','SMARTPC_GAME_PRESENTER=timer']
 with (P/'functional-retained-final.txt').open('w') as out:
  subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(S/'check_game_residual_ui.py'),'--theme','base','--race-seconds','5','--output',str(P/'functional-retained-final')],cwd=S.parent,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=500)
 d=json.loads((P/'functional-retained-final/report.json').read_text());assert d['status']=='passed' and not d['qmlWarnings']
 with (P/'mature-ppo-final-supplement.txt').open('w') as out:
  subprocess.run(['runuser','-u','smartpc','--','env',*env,'SMARTPC_GAME_TRACE=1','SMARTPC_MATURE_PPO='+str(H/'overtake-private/crono.json'),str(PY),str(S/'check_game_fluidity_ui.py'),'--theme','apple','--load','ppo','--mature','--trace','--seconds','120','--output',str(P/'mature-ppo-final-supplement')],cwd=S.parent,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=350)
 print('Final mature PPO supplement passed',flush=True)
 (P/'final-source-checks.json').write_text(json.dumps(dict(status='passed',sourceManifestSha256=hashlib.sha256((S/'release-manifest.json').read_bytes()).hexdigest(),sourceHashes={n:m['sha256'][n] for n in ('game.py','game_dossier.py','game_worker.py','game_academy.py','game_rewards.py','game_residual.py','game_residual_trainer.py','game_checkpoint_writer.py')},armTests=13,functionalReport='functional-retained-final/report.json',productionRecipe='race-residual-2',noProductionTraining=True),indent=2)+'\n')
 print('Final native flows passed',flush=True)
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
