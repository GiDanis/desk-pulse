"""Actual Main/settings/worker: drafts, focus, two tracks and selective reset."""
import argparse
import json
import os
from pathlib import Path
import time

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')


def main():
    from theme_fixture_support import isolate_process,LegacyHarness
    from theme_bundle import BundleManager,validate_project
    from PySide6.QtCore import qVersion
    p=argparse.ArgumentParser();p.add_argument('--theme',choices=('base','functional','apple'),default='base')
    p.add_argument('--palette',choices=('day','night'),default='day');p.add_argument('--text-scale',type=float,default=1.1)
    p.add_argument('--capture-dir',type=Path);a=p.parse_args()
    private,base=isolate_process();project=Path(__file__).resolve().parents[1]
    if a.theme=='apple':
        bundle=project/'theme-projects/apple-calm/bundle';valid=validate_project(bundle)
        cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
        assert cache['digest']==valid['digest'] and cache['result']['qt']==qVersion()
        BundleManager(base,app_root=project/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    h=LegacyHarness(base,{'theme':a.theme if a.theme!='apple' else 'base','variant':a.palette,'motion':'normal','game':True})
    captures=[]
    def wait(predicate):
        end=time.monotonic()+25
        while not predicate() and time.monotonic()<end:h.pump(10)
        assert predicate(),h.game.snapshot
    def capture(name):
        h.pump(50)
        if a.capture_dir:
            a.capture_dir.mkdir(parents=True,exist_ok=True)
            assert h.window.grabWindow().save(str(a.capture_dir/(name+'.png')))
            captures.append(name)
    def key(number):h.expression('activateKey('+str(number)+')');h.pump(20)
    def action(identity):h.expression('gameOption('+json.dumps(identity)+',1)');h.pump(30)
    def items(item):
        yield item
        for child in item.childItems():yield from items(child)
    try:
        if a.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
        assert h.service.setToken('typography.textScale',a.text_scale);h.wait_ready()
        identity=h.game.snapshot['selectedDriverId'];untouched=h.game._store.driver(identity)
        h.expression('familyId="game"');h.wait_ready();key(9);h.wait_ready();capture('session')
        assert h.value('overlay')=='gameMenu' and {'mode','driver','track','start'}.issubset({r['id'] for r in h.game.snapshot['settings']['rows']})
        key(6);assert h.game.snapshot['settings']['section']=='training';capture('training')
        action('advanced');action('group:network');action('population');key(6)
        assert h.game._store.driver(identity)==untouched
        assert not h.game.snapshot['settings']['dirty'] and not h.game.snapshot['settings']['editing']
        capture('fixed-network')
        key(7);key(7);action('section:management')
        action('create');capture('preset-picker');action('preset:ppo')
        created=h.game.snapshot['selectedDriverId'];assert created!=identity
        assert h.game.snapshot['profile']['algorithm']=='ppo'
        assert not h.game.configure({'algorithm':'evolution'})
        capture('created-pilot')
        action('section:session');action('track');capture('track-picker');action('pick:mallory-oval-1')
        assert h.game.snapshot['trackId']=='oval-1'
        action('start');wait(lambda:h.game.snapshot['runState']=='running');wait(lambda:bool(h.game.scene['cars']))
        assert h.game.snapshot['trackId']=='mallory-oval-1'
        assert h.game.snapshot['profile']['algorithm']=='ppo'
        assert len(h.game.scene['cars'])==1;capture('mallory-learning')
        view=h.value('viewIndex');key(6);key(8);assert h.value('viewIndex')==view
        started=time.monotonic();key(5);wait(lambda:not h.game.captured and h.game.snapshot['saveState']=='saved')
        pause=time.monotonic()-started
        assert h.game._store.driver(created,'mallory-oval-1')['steps']>0
        h.expression('pushOverlay("gameMenu")');h.wait_ready();h.game.settingsAction('section:training',1)
        h.game.settingsAction('advanced',1);h.game.settingsAction('group:learning',1)
        saved_rows={r['id']:r for r in h.game.snapshot['settings']['rows']}
        assert saved_rows['info:balance']['value']=='Progressivo'
        assert 'λ 0.99' in saved_rows['info:ppo']['value'],saved_rows['info:ppo']
        capture('balanced-learning-parameters')
        h.expression('popOverlay()');h.wait_ready()
        assert h.game._store.driver(identity,'oval-1')==untouched
        capture('mallory-paused')
        assert h.game.start();wait(lambda:h.game.snapshot['runState']=='running')
        assert h.game.pause();wait(lambda:not h.game.captured and h.game.snapshot['saveState']=='saved')
        h.expression('const v=viewIndex.slice();v[8]=3;viewIndex=v');h.wait_ready();capture('pilot')
        key(5);h.wait_ready();assert h.value('overlay')=='gameDetails'
        h.expression('pilotAction("driver")');h.pump(40);assert h.value('overlay')=='gameMenu';capture('pilot-picker')
        action('pick:'+created);assert h.value('overlay')=='gameDetails'
        key(9);h.wait_ready();action('section:management');action('reset')
        assert h.value('overlay')=='gameDetails' and h.value('gameDossierSection')=='reset'
        before=h.game._store.driver(created);old_oval=h.game._store.driver(created,'oval-1')
        key(5);capture('reset-confirmation');key(5);assert h.game._store.driver(created)==before
        key(5);key(8);key(5);assert h.game._store.driver(created)['steps']==0
        assert h.game._store.driver(created,'oval-1')==old_oval
        assert h.game._store.driver(identity,'oval-1')['profile']['population']==32
        key(9);h.wait_ready();action('section:session');capture('final-session')
        # Descriptions fit the viewport at the actual requested scale.
        for item in items(h.window.contentItem()):
            if item.objectName().startswith('gameSettingDescription') and item.property('visible'):
                assert item.property('contentHeight')<=item.property('height')+.1,(item.objectName(),item.property('contentHeight'),item.property('height'))
        assert not h.messages,h.messages
        assert not h.transport,h.transport
        report=dict(status='passed',theme=a.theme,palette=a.palette,textScale=a.text_scale,
                    platform=os.environ['QT_QPA_PLATFORM'],window=[h.window.width(),h.window.height()],
                    draftNoWrites=True,stableFocus=True,trackIsolation=True,profilePaths=True,
                    resetOnlySelectedPath=True,ppoPreviewSingleCar=True,pauseAckSeconds=pause,
                    screenshots=captures,qmlWarnings=h.messages,scope='Actual UI/worker in isolated state; no optical FPS or physical keypad certification')
        if a.capture_dir:(a.capture_dir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report))
    except BaseException:
        print('QML diagnostics:',h.messages,flush=True)
        raise
    finally:h.close();private.cleanup()


if __name__=='__main__':main()
