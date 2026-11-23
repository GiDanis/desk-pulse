"""Actual Main navigation and Game Start/Pause/Save in private fixture stores."""
import argparse,json,sys,time
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--dashboard',type=Path,required=True);p.add_argument('--theme',choices=('base','functional','apple'),required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.dashboard=a.dashboard.resolve();a.output.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(a.dashboard))
 from theme_fixture_support import isolate_process,LegacyHarness
 from theme_test_support import wait_save
 private,base=isolate_process()
 if a.theme=='apple':
  import shutil
  data=Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC')
  active=json.loads((data/'theme-activation.json').read_text())['active']
  relative=Path('theme-bundles')/active['id']/(active['version']+'-'+active['digest'])
  shutil.copytree(data/relative,base/relative)
 h=LegacyHarness(base,dict(theme='base' if a.theme=='apple' else a.theme,variant='day',motion='normal',game=True))
 from PySide6.QtCore import qInstallMessageHandler,Qt
 import os
 qInstallMessageHandler(None)
 log=open(a.output/'qt-native.log','w',buffering=1);os.dup2(log.fileno(),2)
 def wait(condition,limit=45):
  end=time.monotonic()+limit
  while not condition() and time.monotonic()<end:
   h.pump(10);assert not h.messages,h.messages
   assert h.game._run_state!='error',h.game._message
  assert condition(),h.game.snapshot
 sessions=[];navigation=[]
 try:
  if a.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
  wait(lambda:h.service.readyToApply);assert h.service.apply();wait_save(h.app,h.service,timeout=15);h.wait_ready()
  for family in ('oggi','meteo','account','sports','casa','network','aquarium','game'):
   h.expression('familyId='+json.dumps(family));h.wait_ready();h.pump(80)
   navigation.append({'family':family,'view':h.value('presentedPageContentId')})
   h.expression('activateKey(9)');h.pump(60);assert h.value('overlay')==('gameMenu' if family=='game' else 'menu'),(family,h.value('overlay'))
   h.expression('activateKey(7)');h.pump(60);assert h.value('overlay')==''
  from check_game_menu import menu_prepare
  for name in ('Crono',):
   wait(lambda:h.game._process is None);h.expression('familyId="game"');h.wait_ready()
   menu_prepare(h.game,name,'impara');assert h.game.settingsAction('start',1)
   wait(lambda:h.game._run_state=='running' and bool(h.game.scene.get('cars')))
   h.pump(300);assert h.game.pause();wait(lambda:h.game._run_state=='paused' and h.game._save_state=='saved')
   sessions.append({'pilot':name,'mode':'impara','startPauseSave':'passed'})
   h.game.stop();wait(lambda:h.game._process is None)
  assert not h.messages and not h.transport,(h.messages,h.transport)
  h.expression('familyId="oggi"');h.wait_ready();capture=h.window.contentItem().grabToImage();saved=[]
  capture.ready.connect(lambda:saved.append(capture.saveToFile(str(a.output/'home.png'))),Qt.QueuedConnection);wait(lambda:bool(saved));assert saved[0]
  log.flush();assert not (a.output/'qt-native.log').read_text().strip()
  report={'status':'passed','theme':a.theme,'window':[h.window.width(),h.window.height()],'navigation':navigation,'sessions':sessions,'qmlWarnings':h.messages,'networkAttempts':h.transport,'scope':'Private actual Main and worker; navigation and Start/Pause/Save, no production training, optical FPS or model qualification'}
  (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
 finally:h.close();private.cleanup()

if __name__=='__main__':main()
