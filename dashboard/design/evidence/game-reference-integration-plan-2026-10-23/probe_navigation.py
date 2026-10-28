"""Planning probe: real Main navigation only, isolated fresh data; no Start."""
from pathlib import Path
import argparse,json,os,time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QT_QUICK_BACKEND','software')
def main():
 from theme_fixture_support import isolate_process,LegacyHarness
 p=argparse.ArgumentParser();p.add_argument('--theme',choices=('base','functional','apple'),default='apple');p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=True)
 private,base=isolate_process();project=Path(__import__('game').__file__).resolve().parents[1]
 if a.theme=='apple':
  from theme_bundle import BundleManager,validate_project
  from PySide6.QtCore import qVersion
  bundle=project/'theme-projects/apple-calm/bundle';v=validate_project(bundle);cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text());assert v['digest']==cache['digest'] and cache['result']['qt']==qVersion()
  BundleManager(base,app_root=project/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
 h=LegacyHarness(base,dict(theme=a.theme if a.theme!='apple' else 'base',variant='day',motion='normal',game=True));rows=[]
 try:
  if a.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
  h.expression('familyId="game"');h.wait_ready();h.expression('activateKey(9)');h.wait_ready()
  from check_game_menu import menu_prepare
  for mode in ('impara','impara_infinito','impara_sorpasso','qualifica','gara'):
   menu_prepare(h.game,'Crono',mode);h.pump(30);q=h.game._settings
   for _ in range(len(q.rows())+2):h.expression('activateKey(2)');h.pump(20)
   expected=q.rows()[0]['id'];top=q.selected;count=len(q.rows());sequence=[]
   for _ in range(2):
    for key in [8]*(count+2)+[2]*(count+2):
     start=time.monotonic();h.expression('activateKey('+str(key)+')');h.pump(20)
     sequence.append(dict(key=key,selected=q.selected,qmlIndex=h.value('gameData.settings.selectedIndex'),seconds=time.monotonic()-start))
   rows.append(dict(mode=mode,count=count,initial=top,expected=expected,returnedTop=q.selected==expected,sequence=sequence))
   assert q.selected==expected,(mode,q.selected,expected)
   print(mode,'navigation passed',flush=True)
  assert h.game._process is None
  (a.output/'report.json').write_text(json.dumps(dict(status='passed',theme=a.theme,window=[h.window.width(),h.window.height()],rows=rows,qmlWarnings=h.messages,scope='Fresh private PC Main; navigation only. No physical HID, saved checkpoint, Start, board intervention or training.'),indent=2)+'\n')
 finally:h.close();private.cleanup()
if __name__=='__main__':main()
