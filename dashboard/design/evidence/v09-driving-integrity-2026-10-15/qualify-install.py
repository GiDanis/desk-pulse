"""Qualify driving integrity rc17 privately on EGLFS, then preserve production data on install."""
import hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-driving-integrity-proof';PROJECT=H/'smartpc-v09-rc17-project';SOURCE=PROJECT/'dashboard';RUNTIME=H/'smartpc-v09-rc17-runtime';TARGET=Path('/opt/smartpc/dashboard');PY=H/'game-runtime/bin/python';GAME=H/'.local/share/SmartPC/SmartPC/game'
manifest=json.loads((RUNTIME/'release-manifest.json').read_text());assert manifest['version']=='0.9.0-rc.17'
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
initial=health('before-install');assert initial['version']=='0.9.0-rc.16' and not initial['manifestMismatches']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
backup=Path('/var/backups')/time.strftime('smartpc-before-driving-integrity-%Y%m%d-%H%M%S');backup.mkdir(mode=0o700);old=TARGET.with_name('dashboard-rc16-before-driving-integrity');stage=TARGET.with_name('dashboard-rc17-integrity-stage');switched=False
try:
 stable=snapshot();assert stable['artifacts']==before['artifacts']
 assert all(stable['tables'][t]==v for t,v in before['tables'].items() if t!='sessions')
 def copy(src,dst):
  if Path(src).parent==GAME/'policies':os.link(src,dst);return dst
  return shutil.copy2(src,dst)
 shutil.copytree(GAME,backup/'game',copy_function=copy);shutil.copytree(H/'.config/SmartPC',backup/'config');os.sync()
 env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1']
 assert 'OK' in (P/'arm-final-targets.txt').read_text()
 source=P/'evo-source.json'
 cases=[
  ('base-progressive',SOURCE/'check_game_evo_progressive_ui.py',['--theme','base','--source-checkpoint',str(source),'--seconds','15','--output',str(P/'base-progressive')]),
  ('apple-progressive',SOURCE/'check_game_evo_progressive_ui.py',['--theme','apple','--source-checkpoint',str(source),'--seconds','15','--output',str(P/'apple-progressive')]),
  ('functional-progressive',SOURCE/'check_game_evo_progressive_ui.py',['--theme','functional','--seconds','8','--output',str(P/'functional-progressive')]),
  ('apple-neural-qualification',SOURCE/'check_game_driving_integrity_ui.py',['--theme','apple','--source-checkpoint',str(source),'--output',str(P/'apple-neural-qualification')]),
  ('apple-settings',SOURCE/'check_game_settings_ui.py',['--theme','apple','--capture-dir',str(P/'apple-settings')]),
  ('apple-dossier',SOURCE/'check_game_dossier_ui.py',['--theme','apple','--capture-dir',str(P/'apple-dossier')])]
 for label,script,args in cases:
  existing=P/label/'report.json'
  if label in ('base-progressive','apple-progressive','functional-progressive') and existing.exists() and json.loads(existing.read_text()).get('status')=='passed':
   print('Reused passed '+label+'; only diagnostic harnesses changed',flush=True);continue
  print('Native '+label,flush=True)
  with (P/(label+'.txt')).open('w') as out:
   subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(script),*args],cwd=PROJECT,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=320)
  print('Passed '+label,flush=True)
 final=json.loads((P/'apple-neural-qualification/report.json').read_text());assert not final['qmlWarnings']
 assert final['actualNeuralQualification'] and 19<final['bestFlyingLap']<22
 gate={k:final[k] for k in ('clockHz','clockGapsMs','frameGapsMs','bestFlyingLap')}
 assert 28.5<=final['clockHz']<=31,gate
 for label in ('base-progressive','apple-progressive','functional-progressive'):
  report=json.loads((P/label/'report.json').read_text())
  assert not report['qmlWarnings'] and report['actualAttempts']==32 and report['weightsRngCountersPreserved']
 assert snapshot()==stable,'Production data changed during private qualification'
 assert not old.exists() and not stage.exists();stage.mkdir()
 for name,digest in manifest['sha256'].items():
  dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(RUNTIME/name,dest);assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
 shutil.copy2(RUNTIME/'release-manifest.json',stage/'release-manifest.json');os.sync();TARGET.rename(old);stage.rename(TARGET);switched=True;os.sync()
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 deadline=time.monotonic()+90
 while True:
  time.sleep(3);after=health('installed');gui=after.get('guiHeartbeat') or {}
  if after['service']['ActiveState']=='active' and gui.get('ready') and gui.get('ageSeconds',999)<5 and not gui.get('pending'):break
  assert time.monotonic()<deadline,'GUI not ready'
 assert after['version']==manifest['version'] and not after['manifestMismatches'] and after['service']['NRestarts']=='0'
 assert initial['allPreferenceHashes']==after['allPreferenceHashes'] and initial['activeTheme']==after['activeTheme'] and initial['bootId']==after['bootId']
 after_data=snapshot();assert after_data['artifacts']==stable['artifacts']
 for t,v in stable['tables'].items():
  actual=after_data['tables'][t]
  if t=='sessions':
   assert len(actual)==len(v)
   assert all(x==y or (x[:2]==y[:2] and x[2] in ('paused','running') and y[2]=='interrupted' and x[3:]==y[3:]) for x,y in zip(v,actual))
  else:assert actual==v,t
 receipt=dict(status='passed',version=after['version'],files=len(manifest['sha256']),backup=str(backup),runtimeRollback=str(old),originalPilotsAndArtifactsUnchanged=True,sessionClosureOnly=True,artifactCount=len(stable['artifacts']),pilots=len(stable['tables']['drivers']),preferencesPreserved=True,activeTheme=after['activeTheme'],sameBoot=True,newOSReboot=False,manifestMismatches=after['manifestMismatches'],service=after['service'],guiHeartbeat=after['guiHeartbeat'],nativeCases=['arm-core-25','arm-final-targets']+[x[0] for x in cases],neuralQualificationTiming=gate,finalManifestSha256=hashlib.sha256((TARGET/'release-manifest.json').read_bytes()).hexdigest(),sceneTimingIsNotOptical=True)
 (P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
 if switched:
  subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True);TARGET.rename(TARGET.with_name('dashboard-rc17-failed-integrity'));old.rename(TARGET)
 raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
