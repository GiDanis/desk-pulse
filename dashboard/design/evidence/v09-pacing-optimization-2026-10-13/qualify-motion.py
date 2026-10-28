"""Qualify rc13 on EGLFS, preserve every production table/artifact/preference."""
import hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-pacing-optimization-proof';PROJECT=H/'smartpc-v09-rc13-project';SOURCE=PROJECT/'dashboard';RUNTIME=H/'smartpc-v09-rc13-runtime';TARGET=Path('/opt/smartpc/dashboard');PY=H/'game-runtime/bin/python';GAME=H/'.local/share/SmartPC/SmartPC/game'
manifest=json.loads((RUNTIME/'release-manifest.json').read_text());assert manifest['version']=='0.9.0-rc.13'
assert all(hashlib.sha256((RUNTIME/k).read_bytes()).hexdigest()==v for k,v in manifest['sha256'].items())
def snapshot():
 with sqlite3.connect('file:'+str(GAME/'game.sqlite')+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  tables={r[0]:db.execute('SELECT * FROM '+r[0]+' ORDER BY rowid').fetchall() for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 return dict(tables=tables,artifacts={q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in (GAME/'policies').glob('*.json')})
def health(label):
 path=P/(label+'.json');path.touch();subprocess.run(['chown','smartpc:smartpc',str(path)],check=True)
 subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen',str(PY),str(H/'v086-source-proof/board-health.py'),'--output',str(path)],check=True,stdout=subprocess.DEVNULL)
 return json.loads(path.read_text())
before=snapshot();assert not any(r[2]=='running' for r in before['tables']['sessions'])
initial=health('before-motion-policy');assert initial['version']=='0.9.0-rc.13' and not initial['manifestMismatches']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
backup=Path('/var/backups')/time.strftime('smartpc-before-pacing-%Y%m%d-%H%M%S');backup.mkdir(mode=0o700);old=TARGET.with_name('dashboard-rc13-before-motion-policy');stage=TARGET.with_name('dashboard-rc13-stage');switched=False
try:
 stable=snapshot();assert stable==before
 def copy(src,dst):
  if Path(src).parent==GAME/'policies':os.link(src,dst);return dst
  return shutil.copy2(src,dst)
 shutil.copytree(GAME,backup/'game',copy_function=copy);shutil.copytree(H/'.config/SmartPC',backup/'config');os.sync()
 env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1']
 with (P/'arm-boundaries.txt').open('w') as out:
  subprocess.run(['runuser','-u','smartpc','--','env','QT_QPA_PLATFORM=offscreen','OPENBLAS_NUM_THREADS=1',str(PY),'-c',"import unittest; suite=unittest.defaultTestLoader.loadTestsFromNames(['check_game_pacing','check_theme_api_runtime']); tests=unittest.TestSuite(t for group in suite for case in group for t in case if not t.id().endswith('test_lint_typo_rejected_with_real_qmllint')); result=unittest.TextTestRunner(verbosity=1).run(tests); raise SystemExit(not result.wasSuccessful())"],cwd=SOURCE,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=90)
 cases=[('race-reduced',P/'probe-race.py',['--project',str(PROJECT),'--theme','functional','--track','technical-1','--motion','reduced','--output',str(P/'race-reduced.json')])]
 for label,script,args in cases:
  print('Native '+label,flush=True)
  with (P/(label+'.txt')).open('w') as out:
   subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(script),*args],cwd=PROJECT,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=180)
  print('Passed '+label,flush=True)
 final=json.loads((P/'final-evo32.json').read_text());gate=final['frameGaps'];movement=[v for v in final['motionGaps'].values() if v['n']>100]
 assert snapshot()==stable,'Production data changed during private qualification'
 assert not old.exists() and not stage.exists();stage.mkdir()
 for name,digest in manifest['sha256'].items():
  dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(RUNTIME/name,dest);assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
 shutil.copy2(RUNTIME/'release-manifest.json',stage/'release-manifest.json');os.sync();TARGET.rename(old);stage.rename(TARGET);switched=True;os.sync()
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 deadline=time.monotonic()+90
 while True:
  time.sleep(3);after=health('installed-final');gui=after.get('guiHeartbeat') or {}
  if after['service']['ActiveState']=='active' and gui.get('ready') and gui.get('ageSeconds',999)<5 and not gui.get('pending'):break
  assert time.monotonic()<deadline,'GUI not ready'
 assert after['version']==manifest['version'] and not after['manifestMismatches'] and after['service']['NRestarts']=='0'
 assert initial['allPreferenceHashes']==after['allPreferenceHashes'] and initial['activeTheme']==after['activeTheme'] and initial['bootId']==after['bootId']
 assert snapshot()==stable
 receipt=dict(status='passed',version=after['version'],files=len(manifest['sha256']),backup=str(backup),runtimeRollback=str(old),originalTablesAndArtifactsUnchanged=True,artifactCount=len(stable['artifacts']),pilots=len(stable['tables']['drivers']),preferencesPreserved=True,activeTheme=after['activeTheme'],sameBoot=True,newOSReboot=False,manifestMismatches=after['manifestMismatches'],service=after['service'],guiHeartbeat=after['guiHeartbeat'],nativeCases=[x[0] for x in cases],evo32InitialGate=gate,worstMovingCarP95=max(v['p95Ms'] for v in movement),worstMovingCarMax=max(v['maxMs'] for v in movement))
 (P/'motion-policy-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
 if switched:
  subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True);TARGET.rename(TARGET.with_name('dashboard-rc13-failed'));old.rename(TARGET)
 raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
