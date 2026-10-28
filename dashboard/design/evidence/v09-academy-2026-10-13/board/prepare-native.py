"""Backup first, recover orphan rollback journal, test isolated native UI."""
import hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-academy-proof';PROJECT=H/'smartpc-v09-rc9-project';PY=H/'game-runtime/bin/python'
SOURCE=H/'.local/share/SmartPC/SmartPC/game';P.mkdir(exist_ok=True)
manifest=json.loads((PROJECT/'dashboard/release-manifest.json').read_text())
assert manifest['version']=='0.9.0-rc.9'
assert all(hashlib.sha256((PROJECT/'dashboard'/k).read_bytes()).hexdigest()==v for k,v in manifest['sha256'].items())
backup=Path('/var/backups')/time.strftime('smartpc-before-academy-%Y%m%d-%H%M%S');backup.mkdir(mode=0o700)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 shutil.copytree('/opt/smartpc/dashboard',backup/'runtime')
 for label,path in [('config',H/'.config/SmartPC'),('data',H/'.local/share/SmartPC')]:
  if path.exists():shutil.copytree(path,backup/label)
 journal=SOURCE/'game.sqlite-journal';rawJournal=journal.exists()
 db=sqlite3.connect(SOURCE/'game.sqlite')
 try:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  recovered=list(db.iterdump())
  stale=db.execute("SELECT id,status FROM sessions WHERE status IN ('running','paused')").fetchall()
  assert all(status=='paused' for _,status in stale),'Sessione attiva da conservare'
  db.execute("UPDATE sessions SET status='interrupted' WHERE status='paused'");db.commit()
  current=list(db.iterdump())
 finally:db.close()
 subprocess.run(['chown','smartpc:smartpc',str(SOURCE/'game.sqlite')],check=True)
 (P/'before-game.json').write_text(json.dumps({'recoveredDump':recovered,'baselineDump':current,
     'orphanJournalRecovered':rawJournal,'stalePausedSessionsInterrupted':[i for i,_ in stale],
     'artifacts':{q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in (SOURCE/'policies').glob('*.json')}},indent=2)+'\n')
 (P/'backup.json').write_text(json.dumps({'path':str(backup),'version':'0.9.0-rc.8','rawJournalPreserved':rawJournal},indent=2)+'\n')
 os.sync()
 env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard',
  'QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json',
  'QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1']
 commands=[('base-neat',['check_game_ui.py','--theme','base','--method','neat','--soak-seconds','8'],120),
  ('functional-clone',['check_game_ui.py','--theme','functional','--method','imitation'],120),
  ('apple-ppo',['check_game_ui.py','--theme','apple','--method','ppo_smooth','--track','varano-short-1','--soak-seconds','15','--text-scale','1.1'],150),
  ('apple-settings',['check_game_settings_ui.py','--theme','apple','--palette','night'],150),
  ('apple-dossier',['check_game_dossier_ui.py','--theme','apple'],150),
  ('varano-reference',['check_game_reference_ui.py','--seconds','12'],120),
  ('new-races',['check_game_academy_race_ui.py'],420)]
 reports=[]
 for label,args,timeout in commands:
  print('Native start: '+label,flush=True)
  with (P/(label+'.txt')).open('w') as out:
   subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(PROJECT/'dashboard'/args[0]),*args[1:],'--capture-dir',str(P/label)],cwd=PROJECT,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=timeout)
  report=json.loads((P/label/'report.json').read_text());assert report['status']=='passed' and not report['qmlWarnings']
  assert 'Traceback' not in (P/(label+'.txt')).read_text()
  reports.append({'label':label,**report});print('Native passed: '+label,flush=True)
 (P/'native-qualification.json').write_text(json.dumps({'status':'passed','version':manifest['version'],'profiles':reports},indent=2)+'\n')
finally:
 os.sync();subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
