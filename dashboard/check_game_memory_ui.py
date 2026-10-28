"""Native Main memory flow with a labelled analytic neural fixture, private state."""
import argparse,json,os,time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')


def main():
 from theme_fixture_support import isolate_process,LegacyHarness
 from theme_bundle import BundleManager,validate_project
 from PySide6.QtCore import qVersion
 from game_academy_trainer import AcademyTrainer
 from game_driving_memory import Review
 import numpy as np
 p=argparse.ArgumentParser();p.add_argument('--theme',choices=('base','functional','apple'),default='base');p.add_argument('--capture-dir',type=Path);a=p.parse_args()
 private,base=isolate_process();project=Path(__file__).resolve().parents[1]
 if a.theme=='apple':
  bundle=project/'theme-projects/apple-calm/bundle';cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
  assert validate_project(bundle)['digest']==cache['digest'] and cache['result']['qt']==qVersion()
  BundleManager(base,app_root=project/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
 h=LegacyHarness(base,dict(theme=a.theme if a.theme!='apple' else 'base',variant='night',motion='normal',game=True))
 def wait(test,timeout=30):
  end=time.monotonic()+timeout
  while not test() and time.monotonic()<end:h.pump(10)
  assert test(),h.game.snapshot
 def capture(name):
  if a.capture_dir:
   a.capture_dir.mkdir(parents=True,exist_ok=True);h.pump(40);assert h.window.grabWindow().save(str(a.capture_dir/(name+'.png')))
 try:
  if a.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
  s=h.game._store;identity=s.create_driver('Fixture memoria','evolution');s.activate_academy(identity);s.prepare_driving(identity);d=s.driver(identity)
  t=AcademyTrainer(d['profile'],'oval-1',s.load(d['checkpoint']));t.learner.best[:]=0;t.learner.best[-1]=2
  policy=t.learner.policy();t.review=Review(policy,None,[dict(track='oval-1',phase='launch')],0)
  while t.review:t.tick();h.pump(1)
  s.save_training(identity,t.checkpoint(0),policy,t.steps,0,curriculum=t.state);h.game._refresh();assert h.game.selectDriver(identity)
  base_record=s.memory_record(identity);assert base_record['base']['status']=='provisional'
  original=s.driver(identity);h.expression('familyId="game"');h.wait_ready()
  h.expression('openPilotDetails('+json.dumps(identity)+')');h.wait_ready();capture('personal-base')
  h.expression('popOverlay()');h.wait_ready();assert h.game.setTrack('technical-1')
  assert h.game.start();wait(lambda:h.game.snapshot['runState']=='running' and bool(h.game.scene['cars']))
  capture('automatic-reuse')
  assert h.game.pause();wait(lambda:h.game.snapshot['saveState']=='saved' and not h.game.captured)
  target=s.driver(identity);saved=s.load(target['checkpoint']);assert saved['memory']['baseHash']==base_record['base']['policyHash']
  learner=saved['learner'];np.testing.assert_array_equal(learner['best'],policy['weights'])
  assert s.driver(identity,'oval-1')['checkpoint']==original['checkpoint']
  h.expression('openPilotDetails('+json.dumps(identity)+')');h.wait_ready();capture('context-experience')
  h.expression('pilotSection("reset");pilotAction("reset.all")');h.pump(50);capture('whole-reset-confirmation')
  h.expression('pilotAction("reset.cancel")');assert s.driver(identity)['checkpoint']==target['checkpoint']
  assert h.game.resetAllDriver(identity)
  assert s.memory_record(identity)['reset'] and not s.memory_record(identity)['base']
  assert not s.driver(identity,'oval-1')['checkpoint'] and not s.driver(identity,'technical-1')['checkpoint']
  assert not h.messages,h.messages;assert not h.transport
  result=dict(status='passed',theme=a.theme,platform=os.environ['QT_QPA_PLATFORM'],window=[h.window.width(),h.window.height()],
    automaticPersonalReuse=True,sourcePreserved=True,localCheckpoint=True,wholeReset=True,cancelPreserves=True,qmlWarnings=h.messages,
    fixture='Analytic dense straight-driving policy; only UI/storage gates, no trained-pilot quality claim')
  if a.capture_dir:(a.capture_dir/'report.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps(result))
 finally:h.close();private.cleanup()


if __name__=='__main__':main()
