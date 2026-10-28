"""Native isolated candidates; always return to the installed kiosk."""
import hashlib,json,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');PROJECT=H/'smartpc-v09-rc8-project';P=H/'v09-real-circuits-proof';PY=H/'game-runtime/bin/python'
manifest=json.loads((PROJECT/'dashboard/release-manifest.json').read_text())
assert manifest['version']=='0.9.0-rc.8'
assert all(hashlib.sha256((PROJECT/'dashboard'/k).read_bytes()).hexdigest()==v for k,v in manifest['sha256'].items())
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1']
commands=[('base-settings',['check_game_settings_ui.py','--theme','base'],90),
 ('functional-settings',['check_game_settings_ui.py','--theme','functional','--palette','night'],90),
 ('apple-settings',['check_game_settings_ui.py','--theme','apple','--palette','night'],90),
 ('varano-ppo',['check_game_ui.py','--theme','apple','--track','varano-short-1','--method','ppo_smooth','--text-scale','1.1','--soak-seconds','30'],120),
 ('varano-reference',['check_game_reference_ui.py','--seconds','30'],120),
 ('race',['check_game_race_ui.py','--evidence',str(H/'smartpc-v09-rc7-project/dashboard/design/evidence/v09-settings-circuits-2026-10-11')],420)]
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 reports=[]
 for label,args,timeout in commands:
  print('Native start: '+label,flush=True)
  with (P/(label+'.txt')).open('w') as output:
   subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(PROJECT/'dashboard'/args[0]),*args[1:],'--capture-dir',str(P/label)],cwd=PROJECT,stdout=output,stderr=subprocess.STDOUT,check=True,timeout=timeout)
  report=json.loads((P/label/'report.json').read_text());assert report['status']=='passed' and not report['qmlWarnings']
  reports.append(report);print('Native passed: '+label,flush=True)
 (P/'native-qualification.json').write_text(json.dumps({'status':'passed','version':manifest['version'],'profiles':reports},indent=2)+'\n')
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
