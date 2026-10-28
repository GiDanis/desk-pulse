"""Paired actual-Main 2D/3D component benchmark with isolated providers/state."""
import argparse,json,math,os,sys,time,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--overlay',type=Path);p.add_argument('--mode',choices=['2d','3d'],required=True);p.add_argument('--quality',choices=['low','high'],default='low');p.add_argument('--population',type=int,default=6);p.add_argument('--aa',type=int,default=0,choices=[0,4]);p.add_argument('--resolution',type=float,default=1);p.add_argument('--warmup',type=float,default=60);p.add_argument('--seconds',type=float,default=120);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(a.source.resolve()))
from theme_fixture_support import isolate_process,LegacyHarness
private,base=isolate_process()
if a.mode=='3d':
 if a.overlay:
  import PySide6
  PySide6.__path__.append(str(a.overlay/'usr/lib/python3/dist-packages/PySide6'))
 import geometry
 geometry.register(a.quality)
from theme_bundle import validate_project,BundleManager
from PySide6.QtCore import qVersion,QObject,Qt
from PySide6.QtGui import QOpenGLContext
import ctypes
from theme_test_support import wait_save
checked=validate_project(a.bundle,app_root=a.source.resolve());cache=json.loads((a.bundle.parent/'evidence/preflight-cache.json').read_text());assert cache['digest']==checked['digest'] and cache['result']['status']=='passed' and cache['result']['qt']==qVersion()
BundleManager(base,app_root=a.source.resolve()).import_bundle(a.bundle,preflight=lambda *_:cache['result'],require_preflight=True)
construction=time.monotonic();h=LegacyHarness(base,{'theme':'base','variant':'day','motion':'normal'})
context_info={}
gles=ctypes.CDLL('libGLESv2.so.2');gles.glGetString.argtypes=[ctypes.c_uint];gles.glGetString.restype=ctypes.c_char_p
def probe_gl():
 if context_info:return
 current=QOpenGLContext.currentContext()
 if current is None:return
 data={name:(gles.glGetString(code) or b'').decode(errors='replace') for name,code in [('vendor',0x1f00),('renderer',0x1f01),('version',0x1f02)]}
 data.update(openGLES=current.isOpenGLES(),formatMajor=current.format().majorVersion(),formatMinor=current.format().minorVersion());context_info.update(data)
h.window.beforeRenderPassRecording.connect(probe_gl,Qt.DirectConnection)
def value(expr):return h.expression('aquariumPage.currentItem.'+expr)
def wait(test,seconds=20):
 end=time.monotonic()+seconds
 while not test() and time.monotonic()<end:h.pump(5)
 assert test(),(h.messages,h.expression('aquariumPage.lastError'))
frames=[];samples=[];last_cpu=None;last_time=None
try:
 assert h.service.selectDraft('studio.applecalm');h.wait_ready();wait(lambda:h.service.readyToApply)
 assert h.service.apply(),h.service.lastError;wait_save(h.app,h.service,timeout=15);h.wait_ready()
 h.expression('familyId="aquarium"');wait(lambda:h.aquarium.snapshot['effectivePlayback']=='running')
 h.expression('aquariumPage.currentItem.benchmarkPopulation='+str(a.population))
 if a.mode=='3d':
  h.expression('aquariumPage.currentItem.benchmarkAA='+str(a.aa));h.expression('aquariumPage.currentItem.benchmarkResolution='+str(a.resolution))
 wait(lambda:value('assetsReady') and value('actors.length')==a.population);wait(lambda:value('tickCount')>3)
 opening=time.monotonic()-construction
 # Both renderers must respect the real controller, rather than redraw a static scene.
 ticks=value('tickCount');assert h.aquarium.pause();h.pump(150);frozen=value('tickCount');h.pump(150);assert value('tickCount')==frozen
 assert h.aquarium.resume();wait(lambda:value('tickCount')>frozen)
 h.root.findChild(QObject,'clockTimer').setProperty('running',True)
 h.pump(round(a.warmup*1000));h.window.beforeRenderPassRecording.disconnect(probe_gl)
 def frame():frames.append(time.monotonic_ns())
 def resource(elapsed):
  global last_cpu,last_time
  t=time.monotonic();stat=Path('/proc/self/stat').read_text().split(') ',1)[1].split();cpu=(int(stat[11])+int(stat[12]))/os.sysconf('SC_CLK_TCK');status=dict(l.split(':',1) for l in Path('/proc/self/status').read_text().splitlines() if ':' in l)
  samples.append({'elapsed':elapsed,'rssKiB':int(status['VmRSS'].split()[0]),'threads':int(status['Threads']),'fds':len(list(Path('/proc/self/fd').iterdir())),'cpuPercent':(cpu-last_cpu)/(t-last_time)*100 if last_cpu is not None else None,'temperaturesC':{f.parent.name:int(f.read_text())/1000 for f in Path('/sys/class/thermal').glob('thermal_zone*/temp')}});last_cpu,last_time=cpu,t
 start_ticks=value('tickCount');discarded=value('discardedFrames');h.window.frameSwapped.connect(frame);start=time.monotonic();resource(0);next_sample=start+10
 while time.monotonic()-start<a.seconds:
  h.pump(10);now=time.monotonic()
  if now>=next_sample:resource(now-start);next_sample=now+10
 end=time.monotonic();h.window.frameSwapped.disconnect(frame);resource(end-start)
 ticks=value('tickCount')-start_ticks;dt=[(b-c)/1e6 for c,b in zip(frames,frames[1:])];ordered=sorted(dt)
 def percentile(q):return ordered[max(0,math.ceil(len(ordered)*q)-1)]
 missed=sum(max(0,round(t/(1000/60))-1) for t in dt);slots=len(dt)+missed;rate=len(frames)/(end-start)
 report={'status':'passed','mode':a.mode,'population':a.population,'geometryQuality':a.quality if a.mode=='3d' else None,'msaaSamples':a.aa,'resolutionScale':a.resolution,'window':[960,640],'qtRhiBackend':str(h.window.rendererInterface().graphicsApi()),'actualGlContext':context_info,'qt':qVersion(),'platform':os.environ.get('QT_QPA_PLATFORM'),'seconds':end-start,'warmupSeconds':a.warmup,'callbacks':len(frames),'callbacksPerSecond':rate,'poseTicks':ticks,'poseTicksPerSecond':ticks/(end-start),'p50Ms':percentile(.5),'p95Ms':percentile(.95),'p99Ms':percentile(.99),'maxMs':max(dt),'stallsOver50Ms':sum(t>50 for t in dt),'estimatedMissedSlots':missed,'estimatedMissedSlotRatio':missed/max(1,slots),'discardedLongDeltas':value('discardedFrames')-discarded,'openingToMovingSeconds':opening,'rawIntervalsMs':dt,'resourceSamples':samples,'themeIdentity':{k:checked[k] for k in ('id','version','digest')},'assetRevision':h.aquarium.snapshot['assetRevision'],'sourceManifestSha256':hashlib.sha256((a.source/'release-manifest.json').read_bytes()).hexdigest(),'checks':['privateProvidersAndState','savedAppleTheme','populationReady','actualPoseTicks','pauseStopsClock','resumeRestartsClock','realHeaderClock'],'physicalFramesQualified':False,'scope':'Actual Main isolated fixtures; 3D procedural solid meshes with part-transform rig, two lights, no textures on fish/shadows/postprocessing/skinning'}
 report['near60SoftwareGate']=bool(rate>=59 and percentile(.95)<=18.5 and missed/max(1,slots)<=.01 and report['stallsOver50Ms']<2 and report['poseTicksPerSecond']>=58)
 if a.mode=='3d':
  # Collect intrusive render counters only AFTER the measurement window.
  h.expression('aquariumPage.currentItem.sceneStats.extendedDataCollectionEnabled=true');h.pump(1500)
  fields=['graphicsApiName','drawCallCount','drawVertexCount','renderPassCount','meshDataSize','imageDataSize','pipelineCount','renderTime','renderPrepareTime','syncTime','lastCompletedGpuTime','vmemUsedBytes']
  report['postMeasurement3dStats']={k:value('sceneStats.'+k) for k in fields};report['meshes']=geometry.INVENTORY
  size=h.root.findChild(QObject,'aquariumView3D').property('effectiveTextureSize')
  report['renderTarget']={'width':size.width(),'height':size.height()}
  report['gpuTimingStatus']='Uncollected; a zero is not a measured GPU duration'
  assert report['postMeasurement3dStats']['drawCallCount']>0,'No3D draw calls'
  h.expression('aquariumPage.currentItem.sceneStats.extendedDataCollectionEnabled=false')
 h.pump(30);assert h.window.grabWindow().save(str(a.output/'capture.png'))
 expected='Particles not supported due to missing RGBA32F and RGBA16F texture format support'
 capability_warnings=[message for message in h.messages if a.mode=='3d' and message==expected]
 h.messages[:]=[message for message in h.messages if message not in capability_warnings]
 assert not h.messages and not h.transport,(h.messages,h.transport)
 report.update(qmlWarnings=h.messages,capabilityWarnings=capability_warnings,networkAttempts=h.transport)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('rawIntervalsMs','resourceSamples')}),flush=True)
finally:h.close();private.cleanup()
