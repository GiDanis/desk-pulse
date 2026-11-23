"""Private Main: actual legacy Evo qualification and bounded presentation trace."""
import argparse,json,os,time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')

def main():
 from theme_fixture_support import isolate_process,LegacyHarness
 from theme_bundle import BundleManager,validate_project
 from PySide6.QtCore import QObject,qVersion
 p=argparse.ArgumentParser();p.add_argument('--theme',choices=('base','functional','apple'),default='base');p.add_argument('--output',type=Path,required=True);p.add_argument('--source-checkpoint',type=Path,required=True);a=p.parse_args()
 private,base=isolate_process();root=Path(__file__).resolve().parents[1]
 if a.theme=='apple':
  bundle=root/'theme-projects/apple-calm/bundle';valid=validate_project(bundle);cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text());assert cache['digest']==valid['digest'] and cache['result']['qt']==qVersion()
  BundleManager(base,app_root=root/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
 h=LegacyHarness(base,dict(theme='functional' if a.theme=='functional' else 'base',variant='day',motion='normal',game=True))
 def wait(f,seconds=110):
  end=time.monotonic()+seconds
  while not f() and time.monotonic()<end:h.pump(5)
  assert f(),h.game.snapshot['message']
 try:
  if a.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
  assert h.game.createDriverPreset('evolution');identity=h.game._selected
  source=json.loads(a.source_checkpoint.read_text());c=source['checkpoint'];profile=source['profile']
  from game_transfer import candidate
  # Import an unlabelled historical policy to exercise the worker's export path.
  policy=candidate(c,profile);policy.pop('inputContract',None)
  h.game._store.set_profile(identity,profile,allow_reconfigure=True)
  h.game._store.save_training(identity,c,policy,c['steps'],c['seconds'],curriculum=c['curriculum']);h.game._refresh()
  assert h.game.setMode('qualifica');h.expression('familyId="game"');h.wait_ready();assert h.game.start()
  wait(lambda:h.game.snapshot['runState']=='running' and bool(h.game.scene.get('cars')))
  h.pump(300)
  times=[];h.window.frameSwapped.connect(lambda:times.append(time.monotonic()))
  from game_presentation import GamePresentationClock
  clocks=[x for x in h.window.findChildren(GamePresentationClock) if x.running];clock=[]
  for c in clocks:c.tick.connect(lambda stamp:clock.append(stamp/1000))
  assert clocks,'Presentation clock missing after view activation'
  start=time.monotonic();wait(lambda:any(d['id']==identity and d['timedQualifications'] for d in h.game._drivers))
  elapsed=time.monotonic()-start;cert=h.game._store.driver(identity)['timedQualifications'][0]
  exported=h.game._store.load(cert['policy']);assert exported['inputContract']['constantCue']==2/9
  assert 19<cert['bestLap']<22;assert h.game.scene['cars'][0]['trackLimits']==0
  a.output.mkdir(parents=True,exist_ok=True);h.window.grabWindow().save(str(a.output/'qualification.png'))
  traces=[]
  for x in h.window.findChildren(QObject):
   if x.metaObject().indexOfProperty('presentationTrace')<0:continue
   trace=x.property('presentationTrace');trace=trace.toVariant() if hasattr(trace,'toVariant') else trace
   if trace:traces.extend(trace)
  assert traces and len(traces)<=120
  assert traces[-1]['policy']==cert['policy'],traces[-1]
  gaps=sorted((b-a)*1000 for a,b in zip(times,times[1:]));clock_gaps=sorted((b-a)*1000 for a,b in zip(clock,clock[1:]))
  def dist(rows):return dict(n=len(rows),p95=rows[int(.95*(len(rows)-1))],p99=rows[int(.99*(len(rows)-1))],maximum=max(rows)) if rows else None
  assert h.game.pause();wait(lambda:h.game.snapshot['runState']=='paused');h.game.stop()
  assert not h.messages,h.messages
  report=dict(status='passed',theme=a.theme,platform=os.environ['QT_QPA_PLATFORM'],window=[960,640],
   qualificationWaitUsesCachedDriver=True,bestFlyingLap=cert['bestLap'],actualNeuralQualification=True,inputContract=exported['inputContract'],
   newPolicyHash=cert['policy'],certificateOnlyForMeasuredHash=True,frameGapsMs=dist(gaps),clockGapsMs=dist(clock_gaps),
   clockHz=len(clock)/elapsed,presentationTrace=traces,qmlWarnings=h.messages,
   scope='Qt software timing and actual frozen neural qualification; not optical FPS')
  (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='presentationTrace'}),flush=True)
 finally:h.close();private.cleanup()
if __name__=='__main__':main()
