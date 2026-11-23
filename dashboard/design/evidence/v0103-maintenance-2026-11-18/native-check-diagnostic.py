#!/usr/bin/env python3
"""Bounded real-Main graphics check, normal Qt loop and private providers/data."""
import argparse,json,math,os,sys,time,traceback
import faulthandler,signal
faulthandler.register(signal.SIGUSR1,all_threads=True)
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=float,default=5);p.add_argument('--warmup',type=float,default=1)
p.add_argument('--qt3d-overlay',type=Path);p.add_argument('--theme',default='base');p.add_argument('--theme-data',type=Path)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
if os.environ.get('QT_QPA_PLATFORM')=='eglfs':
 os.environ['QSG_INFO']='1'
 os.environ['QT_MESSAGE_PATTERN']='SMARTPC-QT|%{type}|%{category}|%{message}'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dashboard'))
from theme_fixture_support import isolate_process,LegacyHarness
private,base=isolate_process()
if a.qt3d_overlay:
 import PySide6
 PySide6.__path__.append(str(a.qt3d_overlay/'usr/lib/python3/dist-packages/PySide6'))
if a.theme_data:
 import shutil
 active=json.loads((a.theme_data/'theme-activation.json').read_text())['active']
 assert a.theme==active['id']
 relative=Path('theme-bundles')/active['id']/(active['version']+'-'+active['digest'])
 shutil.copytree(a.theme_data/relative,base/relative)
from PySide6.QtCore import QTimer,Qt
from PySide6.QtGui import QSurfaceFormat
if os.environ.get('QT_QPA_PLATFORM')=='eglfs':
 # Capture initialization too. The shared harness normally installs a Python
 # message callback; suppress that callback only for this native diagnostic.
 # Otherwise early RHI info is lost and logging can enter Python on the render thread.
 from unittest.mock import patch
 from PySide6.QtCore import qInstallMessageHandler
 qInstallMessageHandler(None)
 native_log=open(a.output/'qt-native.log','w',buffering=1)
 os.dup2(native_log.fileno(),2)
 with patch('PySide6.QtCore.qInstallMessageHandler',return_value=None):
  h=LegacyHarness(base,{'theme':'base','variant':'day','motion':'normal'})
else:h=LegacyHarness(base,{'theme':'base','variant':'day','motion':'normal'})
if a.theme!='base':assert h.service.selectDraft(a.theme),h.service.lastError
state={'step':-2,'checks':[],'frames':[],'started':None,'error':None,'resources':[]};started=time.monotonic();gl={}
def expr(s):return h.expression(s)
def page(s):return expr('aquariumPage.currentItem ? aquariumPage.currentItem.'+s+':null')
def check(name,value):
 if not value:raise AssertionError(name)
 state['checks'].append(name)
def frame():
 if state['started'] is not None:state['frames'].append(time.monotonic_ns())
# Python direct callbacks on the render thread can deadlock with GUI-side
# QML incubation/GIL. Only queued frame callbacks are used by this harness.
h.window.frameSwapped.connect(frame,Qt.QueuedConnection)
def sample(elapsed):
 stat=Path('/proc/self/stat').read_text().split(') ',1)[1].split();cpu=(int(stat[11])+int(stat[12]))/os.sysconf('SC_CLK_TCK');now=time.monotonic()
 status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
 previous=state['resources'][-1] if state['resources'] else None
 state['resources'].append({'aquariumSnapshot':h.aquarium.snapshot,'moving':page('moving'),'presented':page('presented'),'assetsReady':page('assetsReady'),'sceneError':page('context.scene.errorText'),'lifecycle':page('context.lifecycle.state'),'suspended':page('context.motionPolicy.suspended'),'elapsed':elapsed,'monotonic':now,'cpuSeconds':cpu,'cpuPercentOneCore':(cpu-previous['cpuSeconds'])/(now-previous['monotonic'])*100 if previous else None,'rssKiB':int(status['VmRSS'].split()[0]),'temperaturesC':{t.parent.name:int(t.read_text())/1000 for t in Path('/sys/class/thermal').glob('thermal_zone*/temp')},'cpuFrequencyKHz':{t.parent.name:t.read_text().strip() for t in Path('/sys/devices/system/cpu/cpufreq').glob('policy*/scaling_cur_freq')}})
captures={}
def capture(name):
 if name in captures:return captures[name]['done']
 result=h.window.contentItem().grabToImage()
 record={'done':False,'result':result};captures[name]=record
 def done():
  record['done']=result.saveToFile(str(a.output/name))
  result.ready.disconnect(done);record['result']=None
 result.ready.connect(done,Qt.QueuedConnection)
 return False

def advance():
 try:
  if time.monotonic()-started>max(90,a.seconds+a.warmup+75):raise TimeoutError('3D UI watchdog: step '+str(state['step'])+' / '+str(expr('activeContentId'))+' / '+str(page('ready'))+' / '+h.service.lastError)
  if time.monotonic()-started>10 and not state.get('debug'):
   state['debug']=True
   print('DEBUG',json.dumps({'step':state['step'],'hostReady':expr('aquariumPage.readiness'),'pageReady':page('ready'),'assetsReady':page('assetsReady'),'ticks':page('tickCount'),'sceneStatus':h.aquarium.scene3d['status']}),flush=True)
  step=state['step']
  if step!=state.get('lastStep'):
   print('STAGE',step,flush=True);state['lastStep']=step
  if step==-2 and h.service.readyToApply:
   check('savedThemeForNavigation',h.service.apply());state['step']=-1
  elif step==-1 and not h.service.editing:
   check('expectedTheme',h.service.activeThemeId==a.theme);state['step']=0
  elif step==0:
   check('native3dAvailable',h.aquarium.supports3d);expr('familyId="aquarium"');state['step']=1
  elif step==1 and page('assetsReady') and page('tickCount')>30:
   if not capture('aquarium-3d.png'):return
   check('sixRealActors',len(h.aquarium.population.state['active'])==6);state['ids']=[r['id'] for r in h.aquarium.population.state['active']]
   check('pauseAccepted',h.aquarium.pause());state['pauseTime']=time.monotonic();state['ticks']=None;state['step']=2
  elif step==2 and state['ticks'] is None and time.monotonic()-state['pauseTime']>.12:state['ticks']=page('tickCount')
  elif step==2 and state['ticks'] is not None and time.monotonic()-state['pauseTime']>.4:
   check('pauseStopsPoses',page('tickCount')==state['ticks']);check('resumeAccepted',h.aquarium.resume());expr('openAquariumManagement()');state['manageStart']=time.monotonic();state['step']=3
  elif step==3 and expr('presentedPageContentId==="aquarium.manage" && aquariumManagePage.currentReady') and time.monotonic()-state['manageStart']>.35 and not h.aquarium.population.busy:
   if not capture('aquarium-management.png'):return
   check('managementIsPresented',expr('aquariumManagePage.visible && aquariumManagePage.currentItem.visible'));check('managementRows',len(h.aquarium.management['rows'])==7)
   for key in (5,8,8,6,8,8,5):expr('activateKey('+str(key)+')')
   state['step']=4
  elif step==4 and not h.aquarium.population.busy:
   check('durationSaved',h.aquarium.population.state['active'][0]['days']==1)
   expr('activateKey(7)');expr('activateKey(7)');state['step']=5
  elif step==5 and not h.aquarium.population.busy and expr('activeContentId==="aquarium.3d"') and page('moving'):
   check('sameFishAfterManagement',state['ids']==[r['id'] for r in h.aquarium.population.state['active']]);check('replacementQueued',h.aquarium.population.act('replace',state['ids'][0],{'species':'clown'}));state['step']=6
  elif step==6 and not h.aquarium.population.busy and h.aquarium.population.state['active'][0]['id']!=state['ids'][0]:
   check('otherFishIdentitiesPreserved',[r['id'] for r in h.aquarium.population.state['active']][1:]==state['ids'][1:]);check('historyPreserved',len(h.aquarium.population.state['history'])==7)
   state['warmupStart']=time.monotonic();state['step']=9
  elif step==9 and time.monotonic()-state['warmupStart']>=a.warmup:
   h.root.findChild(__import__('PySide6.QtCore',fromlist=['QObject']).QObject,'clockTimer').setProperty('running',True)
   state['ticks']=page('tickCount');state['started']=time.monotonic();sample(0);state['nextSample']=10;state['step']=7
  elif step==7:
   elapsed=time.monotonic()-state['started']
   if elapsed>=state['nextSample']:sample(elapsed);state['nextSample']+=10
   if elapsed>=a.seconds:
    state['duration']=elapsed;state['poseTicks']=page('tickCount')-state['ticks'];sample(elapsed);state['started']=None
    expr('aquariumPage.currentItem.sceneStats.extendedDataCollectionEnabled=true');state['statsStart']=time.monotonic();state['step']=8
  elif step==8 and time.monotonic()-state['statsStart']>1:
   if not capture('aquarium-after-replacement.png'):return
   state['drawCalls']=page('sceneStats.drawCallCount');check('sixMeshDrawCalls',state['drawCalls']==6)
   h.events.set_demo_scenario('urgente');state['settle']=time.monotonic();state['ticks']=None;state['step']=10
  elif step==10 and time.monotonic()-state['settle']>.2 and state['ticks'] is None:state['ticks']=page('tickCount')
  elif step==10 and time.monotonic()-state['settle']>.45:
   check('urgentOwnsInputAndStopsPoses',bool(expr('urgentEvent.id')) and h.aquarium.snapshot['requestedPlayback']=='paused' and page('tickCount')==state['ticks'])
   h.events.set_demo_scenario('nessuno');state['settle']=time.monotonic();state['step']=11
  elif step==11 and time.monotonic()-state['settle']>.2:
   check('urgentNeedsExplicitResume',h.aquarium.snapshot['requestedPlayback']=='paused');h.aquarium.resume()
   h.service.beginEdit();check('reducedRequested',h.service.setSection('motionMode','reduced'));state['settle']=time.monotonic();state['ticks']=None;state['step']=12
  elif step==12 and time.monotonic()-state['settle']>.3 and state['ticks'] is None:state['ticks']=page('tickCount')
  elif step==12 and time.monotonic()-state['settle']>.6:
   check('reducedIsStatic3d',h.aquarium.snapshot['effectivePlayback']=='static' and page('tickCount')==state['ticks'])
   check('offRequested',h.service.setSection('motionMode','off'));state['settle']=time.monotonic();state['ticks']=None;state['step']=13
  elif step==13 and time.monotonic()-state['settle']>.3 and state['ticks'] is None:state['ticks']=page('tickCount')
  elif step==13 and time.monotonic()-state['settle']>.6:
   check('offIsStatic3d',h.aquarium.snapshot['effectivePlayback']=='static' and page('tickCount')==state['ticks']);timer.stop();h.app.quit()
 except Exception:
  state['error']=traceback.format_exc();timer.stop();h.app.quit()
timer=QTimer();timer.setInterval(30);timer.timeout.connect(advance);timer.start();h.app.exec()
known='Particles not supported due to missing RGBA32F and RGBA16F texture format support'
if os.environ.get('QT_QPA_PLATFORM')=='eglfs':
 native_log.flush()
 from aquarium_graphics_diagnostics import parse_qt_messages,read_native_context
 renderer_messages=parse_qt_messages((a.output/'qt-native.log').read_text())
 h.messages.extend(m['message'] for m in renderer_messages if m['severity'] not in ('debug','info'))
 (a.output/'renderer-info.json').write_text(json.dumps(renderer_messages,indent=2)+'\n')
capabilities=[m for m in h.messages if m==known];h.messages[:]=[m for m in h.messages if m!=known]
if os.environ.get('QT_QPA_PLATFORM')=='eglfs':
 try:
  gl=read_native_context(os.environ.get('SMARTPC_GL_PROBE_FILE'),os.getpid(),renderer_messages)
 except (OSError,ValueError) as error:
  state['error']=(state['error'] or '')+'\nNative GL diagnostics failed: '+str(error)
else:gl={'collection':'not-requested','scope':'Native EGL probe mandatory on EGLFS; non-EGLFS check has no native context proof'}
state['started']=None
frames=state.pop('frames');raw=[(b-c)/1e6 for c,b in zip(frames,frames[1:])];ordered=sorted(raw)
percentile=lambda q:ordered[max(0,math.ceil(len(ordered)*q)-1)] if ordered else None
result={'status':'failed' if state['error'] or h.messages or h.transport else 'passed','theme':a.theme,'glContext':gl,'requestedSurfaceVersion':[QSurfaceFormat.defaultFormat().majorVersion(),QSurfaceFormat.defaultFormat().minorVersion()],'rhiBackend':str(h.window.rendererInterface().graphicsApi()),'mappedGraphicsLibraries':sorted({Path(line.split()[-1]).name for line in Path('/proc/self/maps').read_text().splitlines() if any(k in line.lower() for k in ('powervr','libpvr','libgles','libegl','llvmpipe'))}),'checks':state['checks'],'error':state['error'],'qmlWarnings':h.messages[:],'capabilityWarnings':capabilities,'networkAttempts':h.transport[:],'seconds':state.get('duration'),'warmup':a.warmup,'callbacks':len(frames),'callbacksPerSecond':len(frames)/state['duration'] if state.get('duration') else None,'poseTicks':state.get('poseTicks'),'p95Ms':percentile(.95),'p99Ms':percentile(.99),'maxMs':max(raw,default=None),'stallsOver50Ms':sum(x>50 for x in raw),'rawIntervalsMs':raw,'resourceSamples':state['resources'],'drawCalls':state.get('drawCalls'),'scope':'Private real Main, normal Qt event loop, saved theme and header clock. Software callbacks/poses, not optical FPS. Original procedural skinned meshes; no MSAA/shadows. Existing immutable theme validation reused only for copied bundle, new surfaces tested here; not a new full theme matrix.'}
(a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('rawIntervalsMs','resourceSamples','qmlWarnings')}),flush=True)
# Diagnostics were persisted above; let teardown report any fresh messages.
h.messages.clear()
try:h.close()
finally:private.cleanup()
sys.exit(0 if result['status']=='passed' else 1)
