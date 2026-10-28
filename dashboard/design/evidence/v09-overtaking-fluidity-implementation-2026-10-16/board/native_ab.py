"""Authorized private display use; restore Dashboard even on diagnostic failure."""
from pathlib import Path
import subprocess,os,json,time
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-overtake-proof';PY=H/'game-runtime/bin/python'
assert not any('spawn_main' in x or 'multiprocessing.spawn' in x for x in subprocess.check_output(['ps','-eo','args='],text=True).splitlines()),'Training active'
# Full baseline snapshot made by installation script later; no data changes here.
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
cases=[('old-timer-a','baseline','timer'),('new-timer-a','project','timer'),('new-frame-a','project','frame'),('new-frame-b','project','frame'),('new-timer-b','project','timer'),('old-timer-b','baseline','timer')]
try:
 for label,project,presenter in cases:
  root=H/('smartpc-overtake-'+project)
  print('Begin '+label,flush=True)
  with (P/(label+'.txt')).open('w') as stream:
   subprocess.run(['runuser','-u','smartpc','--','env',*env,'SMARTPC_GAME_PRESENTER='+presenter,str(PY),str(root/'dashboard/check_game_fluidity_ui.py'),'--theme','apple','--load','race','--seconds','120','--trace','--output',str(P/label)],cwd=root,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=300)
  print('Complete '+label,flush=True)
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
