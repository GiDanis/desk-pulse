"""Private real races: coherent camera/sensors and every body inside the arena."""
import argparse,json,os,statistics,sys,time
from pathlib import Path
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--theme',default='base');p.add_argument('--track',default='oval-1');p.add_argument('--output',type=Path,required=True);p.add_argument('--motion',default='normal');a=p.parse_args();sys.path.insert(0,str(a.project/'dashboard'))
 from theme_fixture_support import isolate_process,LegacyHarness
 from theme_bundle import BundleManager,validate_project
 from PySide6.QtCore import qVersion
 private,base=isolate_process()
 if a.theme=='apple':
  bundle=a.project/'theme-projects/apple-calm/bundle';cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text());assert cache['digest']==validate_project(bundle)['digest'] and cache['result']['qt']==qVersion()
  BundleManager(base,app_root=a.project/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
 h=LegacyHarness(base,dict(theme=a.theme if a.theme!='apple' else 'base',variant='night',motion=a.motion,game=True))
 def items(item):
  yield item
  for c in item.childItems():yield from items(c)
 def wait(check):
  end=time.monotonic()+30
  while not check() and time.monotonic()<end:h.pump(10)
  assert check(),h.game.snapshot
 def distribution(v):
  v=sorted(v);return dict(frames=len(v)+1,medianMs=statistics.median(v)*1000,p95Ms=v[int(.95*(len(v)-1))]*1000,p99Ms=v[int(.99*(len(v)-1))]*1000,maxMs=max(v)*1000,stallsOver100ms=sum(x>.1 for x in v))
 try:
  if a.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
  assert h.game.setTrack(a.track);s=h.game._store;ids=[s.create_driver('Reference '+str(i),'pure_pursuit') for i in range(4)]
  for d in ids:s.activate_academy(d)
  h.game._refresh();h.expression('familyId="game"');h.wait_ready();reports=[]
  for count in (2,4):
   for d in list(h.game.snapshot['participants']):h.game.toggleParticipant(d)
   for d in ids[:count]:h.game.toggleParticipant(d)
   assert h.game.setMode('gara');assert h.game.start()
   wait(lambda:h.game.snapshot['runState']=='running' and len(h.game.scene['cars'])==count)
   while h.game.snapshot['camera']!='sensori':h.game.displayStep(1)
   wait(lambda:h.game.scene.get('meta',{}).get('time',0)>.5)
   frames=[]
   def frame():frames.append(time.monotonic())
   h.window.frameSwapped.connect(frame);started=time.monotonic();checks=0
   arena=next(i for i in items(h.window.contentItem()) if i.objectName()=='gameArena');cars=[i for i in items(arena) if i.objectName().startswith('gameCar')]
   assert len(cars)==count
   if a.motion!='normal':assert arena.parentItem().property('presentationDelay')==0
   while time.monotonic()-started<10:
    h.pump(10)
    for c in cars:
     assert c.property('visible')
     radius=(c.width()**2+c.height()**2)**.5/2;x=c.x()+c.width()/2;y=c.y()+c.height()/2
     assert radius<=x<=arena.width()-radius and radius<=y<=arena.height()-radius,(c.objectName(),x,y,radius)
    checks+=1
   h.window.frameSwapped.disconnect(frame)
   report=dict(cars=count,seconds=time.monotonic()-started,frameGaps=distribution([b-a for a,b in zip(frames,frames[1:])]),everyCarContainedChecks=checks)
   reports.append(report);a.output.parent.mkdir(parents=True,exist_ok=True);assert h.window.grabWindow().save(str(a.output.with_name(a.output.stem+'-'+str(count)+'.png')))
   assert h.game.pause();wait(lambda:not h.game.captured);h.game.stop()
  assert not h.messages,h.messages
  result=dict(status='passed',motion=a.motion,theme=a.theme,track=a.track,window=[h.window.width(),h.window.height()],scope='Qt submitted frames, private actual races 2/4 and every rendered car bounds; not optical FPS',races=reports,qmlWarnings=h.messages)
  a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
 finally:h.close();private.cleanup()
