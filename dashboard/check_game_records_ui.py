"""Real private races plus a labelled spread fixture: every car remains in view."""
import argparse,copy,json,os,time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')


def main():
 from theme_fixture_support import isolate_process,LegacyHarness
 from theme_bundle import BundleManager,validate_project
 from PySide6.QtCore import qVersion
 from game_geometry import get_track
 p=argparse.ArgumentParser();p.add_argument('--theme',choices=('base','functional','apple'),default='base');p.add_argument('--track',default='varano-short-1');p.add_argument('--capture-dir',type=Path);p.add_argument('--soak-seconds',type=float,default=4);a=p.parse_args()
 private,base=isolate_process();project=Path(__file__).resolve().parents[1]
 if a.theme=='apple':
  bundle=project/'theme-projects/apple-calm/bundle';cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
  assert validate_project(bundle)['digest']==cache['digest'] and cache['result']['qt']==qVersion()
  BundleManager(base,app_root=project/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
 h=LegacyHarness(base,dict(theme=a.theme if a.theme!='apple' else 'base',variant='night',motion='normal',game=True))
 def wait(test,timeout=30):
  end=time.monotonic()+timeout
  while not test() and time.monotonic()<end:h.pump(10);assert h.game.snapshot['runState']!='error',h.game.snapshot
  assert test(),h.game.snapshot
 def items(item):
  yield item
  for child in item.childItems():yield from items(child)
 def visible_cars(count,contained=True):
  all_items=list(items(h.window.contentItem()));arena=next(i for i in all_items if i.objectName()=='gameArena')
  cars=[i for i in all_items if i.objectName().startswith('gameCar') and i.property('visible')]
  assert len(cars)==count,(len(cars),h.game.snapshot,h.game.scene)
  assert not next(i for i in all_items if i.objectName()=='gameMinimap').property('visible')
  if contained:
   for car in cars:
    # A circumscribed body circle also bounds rotated cars.
    radius=(car.width()**2+car.height()**2)**.5/2
    x=car.x()+car.width()/2;y=car.y()+car.height()/2
    assert radius<=x<=arena.width()-radius,(x,radius,arena.width())
    assert radius<=y<=arena.height()-radius,(y,radius,arena.height())
 def capture(name):
  if a.capture_dir:
   a.capture_dir.mkdir(parents=True,exist_ok=True);h.pump(80);assert h.window.grabWindow().save(str(a.capture_dir/(name+'.png')))
 try:
  if a.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
  assert h.service.setToken('typography.textScale',1.1);h.wait_ready()
  assert h.game.setTrack(a.track);s=h.game._store
  ids=[s.create_driver('Riferimento '+str(i+1),'pure_pursuit') for i in range(4)]
  for identity in ids:s.activate_academy(identity)
  h.game._refresh();h.expression('familyId="game"');h.wait_ready()
  for identity in list(h.game.snapshot['participants']):assert h.game.toggleParticipant(identity)
  for identity in ids:assert h.game.toggleParticipant(identity)
  assert h.game.setMode('gara');assert h.game.start();wait(lambda:len(h.game.scene['cars'])==4)
  while h.game.snapshot['camera']!='sensori':h.game.displayStep(1)
  wait(lambda:h.game.snapshot['runState']=='running');h.pump(150);visible_cars(4);capture('race-four-sensors')
  started=time.monotonic()
  while time.monotonic()-started<a.soak_seconds:h.pump(10);visible_cars(4)
  assert h.game.pause();wait(lambda:not h.game.captured)
  # Fixture uses actual circuit coordinates; tests camera framing, not learned quality.
  scene=copy.deepcopy(h.game.scene);geometry=get_track(a.track)
  for i,car in enumerate(scene['cars']):
   x,y,yaw=geometry.pose(geometry.length*i/4);car.update(x=float(x),y=float(y),yaw=float(yaw))
  if a.track=='oval-1':scene['cars'][0].update(x=0.,y=-41.,yaw=0.)
  h.game._scene=scene;h.game.sceneChanged.emit();h.pump(150);visible_cars(4);capture('race-group-spread-fixture')
  # Persist the exact measured frame, verify records reach the actual Main DTO and Classifica.
  run,payload=s.begin_session('gara',{'participants':[dict(id=identity,name='Riferimento '+str(i+1),policy=s.driver(identity)['policy'],profile=s.driver(identity)['profile']) for i,identity in enumerate(ids)],'profile':s.driver(ids[0])['profile']})
  payload['results']=[dict(id=identity,position=i+1,status='arrivato',finishTime=180+i,lap=3,telemetryVersion=1,
   maxSpeed=20+i,lapTimes=[dict(lap=2,time=60+i,clean=True,standingStart=False)]) for i,identity in enumerate(ids)]
  s.finish_session(run,'complete',payload);h.game._refresh();assert h.game.snapshot['leaderboard']['raceRecords']['bestLap']['value']==60
  h.expression('activateKey(8)');h.wait_ready();assert h.value('activeContentId')=='game.leaderboard';capture('track-records-fixture')
  text=next(i for i in items(h.window.contentItem()) if i.objectName()=='gameTrackRecords').property('text')
  assert '60.00' in text and '83 km/h' in text,text
  assert not h.messages,h.messages;assert not h.transport
  result=dict(status='passed',theme=a.theme,track=a.track,platform=os.environ['QT_QPA_PLATFORM'],window=[h.window.width(),h.window.height()],allCarsVisibleInSensors=True,groupCameraFitsSeparatedCars=True,recordsReachMain=True,qmlWarnings=h.messages,
   fixtures='Deterministic references for real race; spread and record fixtures labelled, no trained-pilot quality claim')
  if a.capture_dir:(a.capture_dir/'report.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps(result))
 finally:h.close();private.cleanup()


if __name__=='__main__':main()
