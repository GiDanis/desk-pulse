from pathlib import Path
import subprocess,json,hashlib,sqlite3,shutil,time
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-direct-proof';S=H/'smartpc-direct-project/dashboard';PY=H/'game-runtime/bin/python';G=H/'.local/share/SmartPC/SmartPC/game'
m=json.loads((S/'release-manifest.json').read_text());assert m['version']=='0.9.0-rc.25'
assert all(hashlib.sha256((S/n).read_bytes()).hexdigest()==v for n,v in m['sha256'].items())
base=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
def artifacts():return {str(p.relative_to(G)):hashlib.sha256(p.read_bytes()).hexdigest() for p in G.rglob('*') if p.is_file() and not p.name.startswith('game.sqlite')}
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
before=artifacts();raw=H/'game-backups'/time.strftime('before-direct-native-%Y%m%d-%H%M%S');shutil.copytree(G,raw);raw.chmod(0o700)
try:
 with (P/'arm-tests.txt').open('w') as out:
  subprocess.run(['runuser','-u','smartpc','--','env',*base,'QT_QPA_PLATFORM=offscreen','PYTHONPATH='+str(S),str(PY),'-m','unittest','check_game_direct','check_game_incentives','check_game_overtaking.OvertakingChecks.test_detached_replay_and_bounded_durable_writer','-v'],cwd=S,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=500)
 print('ARM numeric and direct control tests passed',flush=True)
 env=base+['QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl']
 for theme in ('base','functional','apple'):
  args=[str(PY),str(S/'check_game_residual_ui.py'),'--theme',theme,'--race-seconds','150' if theme=='apple' else '8','--output',str(P/theme)]
  if theme=='apple':args+=['--full-race','--qualification']
  with (P/(theme+'.txt')).open('w') as out:
   subprocess.run(['runuser','-u','smartpc','--','env',*env,*args],cwd=S.parent,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=650)
  report=json.loads((P/theme/'report.json').read_text());assert report['status']=='passed' and not report['qmlWarnings'] and report['fiveCarsVisible']
  assert all(x['control']=='direct' and x['policyKind']=='direct' for x in report['learners'])
  if theme=='apple':assert report['completedRace'] and report['actualGuiQualification']
  print('Native '+theme+' passed',flush=True)
 (P/'source-checks.json').write_text(json.dumps(dict(status='passed',sourceHashes=m['sha256'],nativeCases=['base','functional','apple'],originalArtifactCount=len(before),fullRace='apple'),indent=2)+'\n')
finally:
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 assert all(artifacts().get(n)==h for n,h in before.items()),'Original policy artifact changed'
 (P/'original-preservation.json').write_text(json.dumps(dict(status='passed',artifactsPreserved=True,artifactCount=len(before),rawBackup=str(raw),scope='Private test stores only; original service restarted'),indent=2)+'\n')
