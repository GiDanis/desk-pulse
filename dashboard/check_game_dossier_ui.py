"""Per-pilot view, real training duration, history navigation and reset isolation."""
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
    p.add_argument('--capture-dir',type=Path);a=p.parse_args()
    private,base=isolate_process();project=Path(__file__).resolve().parents[1]
    if a.theme=='apple':
        bundle=project/'theme-projects/apple-calm/bundle';valid=validate_project(bundle)
        cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
        assert cache['digest']==valid['digest'] and cache['result']['qt']==qVersion()
        BundleManager(base,app_root=project/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    h=LegacyHarness(base,{'theme':a.theme if a.theme!='apple' else 'base','variant':'day','motion':'normal','game':True})
    def wait(predicate):
        end=time.monotonic()+20
        while not predicate() and time.monotonic()<end:h.pump(10)
        assert predicate(),h.game.snapshot
    def capture(name):
        if a.capture_dir:
            a.capture_dir.mkdir(parents=True,exist_ok=True);h.pump(50)
            assert h.window.grabWindow().save(str(a.capture_dir/(name+'.png')))
    try:
        if a.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
        assert h.service.setToken('typography.textScale',1.1);h.wait_ready()
        drivers=h.game._store.drivers();identity=drivers[0]['id'];other=drivers[1]['id']
        untouched=h.game._store.driver(other)
        h.expression('familyId="game"');h.wait_ready()
        assert h.game.start();wait(lambda:h.game.captured and h.game.snapshot['runState']=='running')
        assert not h.game.resetDriver(identity), 'Reset while running'
        h.pump(1000);assert h.game.pause();wait(lambda:not h.game.captured and h.game.snapshot['saveState']=='saved')
        assert not h.game.resetDriver(other), 'Reset a different pilot'
        saved=h.game._store.driver(identity);assert saved['steps']>0
        session=next(s for s in h.game._store.sessions(complete=False) if s['mode']=='impara')
        assert session['payload']['training']['steps']==saved['steps']
        assert session['payload']['training']['seconds']==saved['seconds']
        # Selecting a changed training method retains provenance of the saved model.
        assert not h.game.configure({'algorithm':'ppo'})
        h.game.stop()
        h.game._store.set_profile(identity,{**saved['profile'],'algorithm':'ppo'},allow_reconfigure=True)
        h.game._refresh()
        h.expression('const v=viewIndex.slice();v[8]=3;viewIndex=v');h.wait_ready()
        assert h.value('activeContentId')=='game.driver' and h.game._process is None
        capture('pilot-page')
        h.expression('activateKey(5)');h.wait_ready();assert h.value('overlay')=='gameDetails'
        capture('summary')
        h.expression('activateKey(6)');h.pump(50);assert h.value('gameDossierSection')=='parameters';capture('parameters')
        rows=h.game.snapshot['dossier']['parameters'];assert rows[0]['value']=='PPO'
        h.expression('activateKey(6)');h.pump(50);capture('history')
        h.expression('pilotAction("session:'+session['id']+'")');h.pump(50);capture('session-profile')
        assert h.value('gameSessionRows')[1]['value']=='Evoluzione'
        h.expression('activateKey(7)');h.pump(30);assert not h.value('gameSessionRows')
        h.expression('activateKey(6)');h.pump(30);capture('results-empty')
        h.expression('activateKey(9)');h.wait_ready()
        h.game.settingsAction('section:management',1);h.game.settingsAction('reset',1);h.pump(30)
        assert h.value('gameDossierSection')=='reset';capture('reset')
        h.expression('activateKey(5)');h.pump(30);assert h.value('gameResetPilot')==identity;capture('reset-confirmation')
        h.expression('activateKey(5)');h.pump(30);assert h.value('gameResetPilot')==''
        assert h.game._store.driver(identity)['steps']==0
        assert h.game._store.total_seconds(identity)==saved['seconds']
        # Leaving/reopening clears a pending confirmation.
        h.expression('activateKey(5)');h.pump(30)
        h.expression('activateKey(9)');h.pump(30);assert h.value('gameResetPilot')==''
        h.expression('popOverlay();pilotSection("reset")');h.pump(30)
        before_reset_sessions=h.game._store.sessions(complete=False)
        h.expression('activateKey(5)');h.expression('activateKey(8)');h.pump(30)
        h.expression('activateKey(5)');h.pump(50)
        fresh=h.game._store.driver(identity)
        assert not fresh['policy'] and not fresh['checkpoint'] and not fresh['candidate'] and not fresh['curriculum']
        assert fresh['steps']==0 and fresh['seconds']==0 and fresh['profile']['algorithm']=='ppo'
        assert h.game._store.driver(other)==untouched
        assert h.game._store.sessions(complete=False)==before_reset_sessions
        assert any(e['kind']=='reset' for e in h.game._store.driver_events(identity))
        capture('reset-completed')
        assert h.game._process is None
        h.expression('pilotAction("driver")');h.pump(50)
        h.game.settingsAction('pick:'+other,1);h.pump(50);assert h.game.snapshot['selectedDriverId']==other
        capture('other-pilot');assert not h.messages,h.messages
        report=dict(status='passed',platform=os.environ['QT_QPA_PLATFORM'],window=[h.window.width(),h.window.height()],
                    theme=a.theme,textScale=1.1,newView=True,sessionStats=True,previousProfile=True,
                    cancelResetPreservesTraining=True,confirmedResetOnlySelected=True,historyPreserved=True,
                    noAutomaticStart=True,qmlWarnings=h.messages)
        if a.capture_dir:(a.capture_dir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report))
    finally:h.close();private.cleanup()
if __name__=='__main__':main()
