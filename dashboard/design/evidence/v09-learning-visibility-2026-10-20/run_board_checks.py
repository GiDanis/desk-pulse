from pathlib import Path
import subprocess,json,hashlib
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-learning-proof';S=H/'smartpc-learning-project/dashboard';PY=H/'game-runtime/bin/python'
m=json.loads((S/'release-manifest.json').read_text())
assert all(hashlib.sha256((S/n).read_bytes()).hexdigest()==v for n,v in m['sha256'].items())
assert not any('spawn_main' in x or 'multiprocessing.spawn' in x for x in subprocess.check_output(['ps','-eo','args='],text=True).splitlines()),'Active training'
base=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 with (P/'arm-tests.txt').open('w') as out:
  subprocess.run(['runuser','-u','smartpc','--','env',*base,'QT_QPA_PLATFORM=offscreen','PYTHONPATH='+str(S),str(PY),'-m','unittest','check_game_timing',
   'check_game_residual.ResidualTests.test_visible_candidate_is_frozen_until_finish_and_resumes_exactly',
   'check_game_residual.ResidualTests.test_legacy_preview_upgrade_keeps_learning_and_exposes_real_counters',
   'check_game_residual.ResidualTests.test_trainer_json_resume',
   'check_game_residual.ResidualTests.test_mode_change_preserves_learner_not_old_episode','-v'],cwd=S,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=300)
 print('ARM tests passed',flush=True)
 env=base+['QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl']
 for theme,seconds in (('base',54),('functional',45),('apple',45)):
  with (P/(theme+'.txt')).open('w') as out:
   subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(S/'check_game_learning_visibility_ui.py'),'--theme',theme,'--checkpoint',str(P/'private/crono.json'),'--seconds',str(seconds),'--output',str(P/theme)],cwd=S.parent,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=230)
  r=json.loads((P/theme/'report.json').read_text());assert r['status']=='passed' and not r['qmlWarnings']
  assert all(m['sha256'][n]==v for n,v in r['sourceHashes'].items())
  print('Native '+theme+' passed',flush=True)
 (P/'source-checks.json').write_text(json.dumps(dict(status='passed',manifestSha256=hashlib.sha256((S/'release-manifest.json').read_bytes()).hexdigest(),sourceHashes=m['sha256'],nativeCases=['base','functional','apple']),indent=2)+'\n')
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
