"""Private Main walkthrough: progressive Evo, 32 attempts and weight-preserving restart."""
import argparse,json,os,time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')


def main():
 from theme_fixture_support import isolate_process,LegacyHarness
 from theme_bundle import BundleManager,validate_project
 from PySide6.QtCore import qVersion
 p=argparse.ArgumentParser();p.add_argument('--theme',choices=('base','functional','apple'),default='base');p.add_argument('--output',type=Path,required=True);p.add_argument('--source-checkpoint',type=Path);p.add_argument('--seconds',type=float,default=15);a=p.parse_args()
 private,base=isolate_process();root=Path(__file__).resolve().parents[1]
 if a.theme=='apple':
  bundle=root/'theme-projects/apple-calm/bundle';valid=validate_project(bundle);cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
  assert cache['digest']==valid['digest'] and cache['result']['qt']==qVersion()
  BundleManager(base,app_root=root/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
 h=LegacyHarness(base,dict(theme='functional' if a.theme=='functional' else 'base',variant='day',motion='normal',game=True))
 def wait(f,seconds=25):
  end=time.monotonic()+seconds
  while not f() and time.monotonic()<end:h.pump(5)
  assert f(),h.game.snapshot['message']
 def capture(label):
  a.output.mkdir(parents=True,exist_ok=True);h.pump(60);assert h.window.grabWindow().save(str(a.output/(label+'.png')))
 try:
  if a.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
  assert h.service.setToken('typography.textScale',1.1);h.wait_ready()
  assert h.game.createDriverPreset('evolution');identity=h.game._selected
  if a.source_checkpoint:
   source=json.loads(a.source_checkpoint.read_text());checkpoint=source['checkpoint'];profile=source['profile']
   h.game._store.set_profile(identity,profile,allow_reconfigure=True)
   from game_learning import Evolution
   policy=Evolution(profile,checkpoint['learner']).candidate_policy()
   h.game._store.save_training(identity,checkpoint,policy,checkpoint['steps'],checkpoint['seconds'],curriculum=checkpoint['curriculum']);h.game._refresh()
  h.game._training_view='attempts';h.game._refresh()
  h.expression('familyId="game"');h.wait_ready()
  assert h.game.start();wait(lambda:h.game.snapshot['runState']=='running' and len(h.game.scene.get('cars',[]))==32 and h.game.scene['meta'].get('evoTraining'))
  assert not h.game.restartDriverCurriculum(identity)
  times=[];h.window.frameSwapped.connect(lambda:times.append(time.monotonic()))
  begin=time.monotonic();seen=set();max_count=0
  while time.monotonic()-begin<a.seconds:
   h.pump(5);scene=h.game.scene;max_count=max(max_count,len(scene.get('cars',[])))
   if scene.get('meta',{}).get('evoTraining'):seen.add(scene['meta']['evoTraining']['scenario'])
  assert max_count==32;capture('population')
  assert h.game.pause();wait(lambda:h.game.snapshot['runState']=='paused' and h.game.snapshot['saveState']=='saved');h.game.stop()
  saved=h.game._store.driver(identity);c=h.game._store.load(saved['checkpoint']);assert c['rewardSpec']['version']=='balanced-driving-2'
  h.expression('openPilotDetails('+json.dumps(identity)+')');h.wait_ready();capture('epoch-summary')
  summary=h.game.snapshot['dossier']['summary'];assert any(r['title']=='Passi del protocollo' for r in summary)
  h.expression('pilotSection("reset");pilotAction("reset.curriculum")');h.pump(80);capture('restart-confirmation')
  assert h.value('gameResetCurriculum');h.expression('pilotAction("reset.cancel")');assert h.game._store.driver(identity)['checkpoint']==saved['checkpoint']
  h.expression('pilotAction("reset.curriculum");pilotAction("reset.confirm")');h.pump(100)
  after=h.game._store.driver(identity);new=h.game._store.load(after['checkpoint'])
  assert new['learner']['population']==c['learner']['population'];assert new['learner']['rng']==c['learner']['rng']
  assert after['steps']==saved['steps'] and after['seconds']==saved['seconds'];assert new['episodes'] is None
  assert not new['curriculum'].get('evoTraining');assert h.game._process is None
  capture('restart-complete');assert not h.messages,h.messages
  intervals=sorted((b-a)*1000 for a,b in zip(times,times[1:]))
  report=dict(status='passed',theme=a.theme,platform=os.environ['QT_QPA_PLATFORM'],window=[960,640],textScale=1.1,
      actualAttempts=max_count,scenariosSeen=sorted(seen),steps=saved['steps'],epoch=c['curriculum']['epochStats'],
      weightsRngCountersPreserved=True,restartWithoutAutoStart=True,qmlWarnings=h.messages,
      frameP95Ms=intervals[int(.95*(len(intervals)-1))] if intervals else None,
      frameP99Ms=intervals[int(.99*(len(intervals)-1))] if intervals else None,
      scope='Qt frameSwapped through screenshot and pause; not optical FPS or a steady-state performance gate')
  (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
 finally:h.close();private.cleanup()

if __name__=='__main__':main()
