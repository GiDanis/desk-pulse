"""Follow-up against the identical captured Evo stream; never install prototype."""
import json,sqlite3,subprocess
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-evo-pacing-proof';BASE=H/'smartpc-v09-rc12-project';PY=H/'game-runtime/bin/python';GAME=H/'.local/share/SmartPC/SmartPC/game'
def snapshot():
 with sqlite3.connect('file:'+str(GAME/'game.sqlite')+'?mode=ro',uri=True) as db:return list(db.iterdump())
before=snapshot();assert not any("'running'" in x and 'INSERT INTO "sessions"' in x for x in before)
subprocess.run([str(PY),str(P/'prototype_qml30.py'),str(BASE/'dashboard/presentations/GameVisual.qml'),str(P/'prototype-project/dashboard/presentations/GameVisual.qml')],check=True)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 stable=snapshot()
 env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1']
 with (P/'qml30.txt').open('w') as out:
  subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(P/'probe-native-pacing.py'),'--project',str(P/'prototype-project'),'--output',str(P),'--mode','qml30','--seconds','35'],stdout=out,stderr=subprocess.STDOUT,check=True,timeout=100)
 assert snapshot()==stable
 (P/'qml30-receipt.json').write_text(json.dumps(dict(status='passed',installedFilesUnchanged=True,originalTablesUnchanged=True,prototypeNotInstalled=True),indent=2)+'\n')
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
