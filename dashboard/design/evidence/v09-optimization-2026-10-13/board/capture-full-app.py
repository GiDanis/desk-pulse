"""Capture installed Main only after its current PID has a coherent heartbeat."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'/opt/smartpc/dashboard')
import app
from PySide6.QtCore import QTimer
from PySide6.QtQuick import QQuickWindow
from PySide6.QtGui import QGuiApplication
P=Path('/var/lib/smartpc-dashboard/v09-optimization-proof');original_exec=QGuiApplication.exec
services=[];states=[];original_game=app.GameService;original_state=app.DashboardState
START=time.time()
def game(*args,**kwargs):
 result=original_game(*args,**kwargs);services.append(result);return result
app.GameService=game
def state(*args,**kwargs):
 result=original_state(*args,**kwargs);states.append(result);return result
app.DashboardState=state

def capture_exec(self):
 def capture():
  service=states[0].appearance
  path=service.lifecycle.health_path
  data=json.loads(path.read_text()) if path.exists() else {}
  if data.get('pid')!=os.getpid() or not data.get('ready') or data.get('pending') or data.get('time',0)<START:
   print('Waiting current coherent frame '+json.dumps({'pid':data.get('pid'),'ready':data.get('ready'),'age':time.time()-data.get('time',0),'themeError':service.lastError}),flush=True)
   QTimer.singleShot(1000,capture);return
  windows=[w for w in self.allWindows() if isinstance(w,QQuickWindow) and w.isVisible()]
  assert len(windows)==1 and windows[0].grabWindow().save(str(P/'full-startup-screen.png'))
  assert services and all(not s._process for s in services),'Gioco partito senza Start'
  (P/'full-startup.json').write_text(json.dumps({'status':'passed','noImplicitGameStart':True,'nativeResolution':[windows[0].width(),windows[0].height()],
      'currentPIDVerified':True,'health':data,'scope':'Timed installed full app under maintenance; actual services and private data'},indent=2)+'\n')
  self.quit()
 QTimer.singleShot(1000,capture);QTimer.singleShot(65000,self.quit)
 return original_exec()
QGuiApplication.exec=capture_exec
sys.exit(app.main())
