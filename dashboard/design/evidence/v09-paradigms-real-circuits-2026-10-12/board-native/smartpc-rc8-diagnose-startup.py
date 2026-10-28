"""Timed full application startup with original services and private data."""
import faulthandler,json,sys,time
from pathlib import Path
START=time.monotonic();ROOT=Path('/var/lib/smartpc-dashboard/smartpc-v09-rc8-project/dashboard');P=Path('/var/lib/smartpc-dashboard/v09-real-circuits-proof')
faulthandler.dump_traceback_later(10,repeat=True)
sys.path.insert(0,str(ROOT))
import app
import os
original_fsync=os.fsync
def logged_fsync(fd):
 start=time.monotonic();print('FSYNC START '+str(fd)+' '+str(start-START),flush=True)
 try:return original_fsync(fd)
 finally:print('FSYNC END '+str(fd)+' '+str(time.monotonic()-start),flush=True)
os.fsync=logged_fsync
for name in ('SystemInfo','Keypad','WeatherService','AccountService','CasaService','NetworkService','GameService','EventService','SportService','MotorsportService','DashboardState'):
 original=getattr(app,name)
 def timed(*args,_name=name,_original=original,**kwargs):
  print('START '+_name+' '+str(time.monotonic()-START),flush=True)
  result=_original(*args,**kwargs)
  print('END '+_name+' '+str(time.monotonic()-START),flush=True)
  if _name=='DashboardState':
   print('THEME '+str(result.appearance)+' ERROR '+result.themeRecoveryError,flush=True)
   if result.appearance: print('HEALTH PATH '+str(result.appearance.lifecycle.health_path),flush=True)
  return result
 setattr(app,name,timed)
from PySide6.QtCore import QTimer
from PySide6.QtQuick import QQuickWindow
from PySide6.QtGui import QGuiApplication
original_exec=QGuiApplication.exec

def timed_exec(self):
 print('EVENT LOOP '+str(time.monotonic()-START),flush=True)
 def capture():
  for window in self.allWindows():
   if isinstance(window,QQuickWindow):window.grabWindow().save(str(P/'full-startup-screen.png'))
  from theme_lifecycle import LifecycleManager
  path=LifecycleManager(Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC')).health_path
  data=json.loads(path.read_text()) if path.exists() else {'ready':'missing'}
  print('HEALTH '+json.dumps({k:data.get(k) for k in ('ready','pid','time','pending','selection')}),flush=True)
 QTimer.singleShot(7000,capture);QTimer.singleShot(24000,self.quit)
 return original_exec()
QGuiApplication.exec=timed_exec
try:sys.exit(app.main())
finally:faulthandler.cancel_dump_traceback_later()
