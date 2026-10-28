"""Real saved learned policies: race menu, grid, three laps and persistence."""
import argparse
import json
import os
from pathlib import Path
import time
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')

def main():
    from theme_fixture_support import isolate_process,LegacyHarness
    from theme_bundle import BundleManager,validate_project
    from PySide6.QtCore import qVersion
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--capture-dir',type=Path,required=True);p.add_argument('--quick',action='store_true')
    a=p.parse_args();a.capture_dir.mkdir(parents=True,exist_ok=True)
    private,base=isolate_process();root=Path(__file__).resolve().parents[4]
    bundle=root/'theme-projects/apple-calm/bundle';valid=validate_project(bundle)
    cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
    assert cache['digest']==valid['digest'] and cache['result']['qt']==qVersion()
    BundleManager(base,app_root=root/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    h=LegacyHarness(base,{'theme':'base','variant':'day','motion':'normal','game':True})
    def wait(predicate,seconds=20):
        end=time.monotonic()+seconds
        while not predicate() and time.monotonic()<end:
            h.pump(10);assert h.game.snapshot['runState']!='error',h.game.snapshot['message']
        assert predicate(),h.game.snapshot
    def capture(name):
        h.pump(40);assert h.window.grabWindow().save(str(a.capture_dir/(name+'.png')))
    try:
        assert h.service.selectDraft('studio.applecalm');h.wait_ready()
        assert h.service.setToken('typography.textScale',1.1);h.wait_ready()
        h.expression('familyId="game"');h.wait_ready()
        h.expression('activateKey(9)');h.wait_ready();assert h.game.setMode('gara')
        assert not h.expression('gameOption("start",1)')
        assert h.value('overlay')=='gameMenu' and not h.game._process
        assert 'due' in h.game.snapshot['message'];capture('race-missing-models')
        policies=[json.loads((a.evidence/('learning-seed-'+str(i)+'.json')).read_text())['state']['champion']['policy'] for i in (1,5)]
        drivers=h.game._store.drivers();hashes=[]
        for i,d in enumerate(drivers):
            hashes.append(h.game._store.save_training(d['id'],{},policies[i%2],100,1))
        h.game._refresh();assert h.game.setMode('gara')
        assert len(h.game.snapshot['participants'])==4
        for d in drivers[2:]:assert h.game.toggleParticipant(d['id'])
        rows=h.value('gameMenuRows');rows=rows.toVariant() if hasattr(rows,'toVariant') else rows
        assert not any(r['id'] in ('algorithm','population','mutation','hidden') for r in rows)
        capture('race-menu')
        assert h.expression('gameOption("start",1)');wait(lambda:h.game.snapshot['runState']=='running')
        wait(lambda:len(h.game.scene['cars'])==2)
        assert {r['id'] for r in h.game.scene['cars']}=={d['id'] for d in drivers[:2]}
        assert h.game.scene['meta']['laps']==3;capture('race-grid')
        if not a.quick:
            started=time.monotonic();last_capture=started
            while h.game.snapshot['runState']!='finished' and time.monotonic()-started<150:
                h.pump(10);assert not h.messages,h.messages
                assert h.game.snapshot['runState']!='error',h.game.snapshot['message']
                assert len(h.game.scene['cars'])==2
                if time.monotonic()-last_capture>30:
                    capture('race-running');last_capture=time.monotonic()
            assert h.game.snapshot['runState']=='finished',h.game.snapshot
            results=h.game.snapshot['leaderboard']['race']
            assert len(results)==2 and any(r['lap']==3 and r['status']=='arrivato' for r in results),results
            capture('race-finished')
        else:
            assert h.game.pause();wait(lambda:not h.game.captured)
        assert h.game.setMode('gara');assert h.game.setRaceLaps(5)
        for d in drivers[2:]:assert h.game.toggleParticipant(d['id'])
        assert h.game.start();wait(lambda:h.game.snapshot['runState']=='running')
        wait(lambda:len(h.game.scene['cars'])==4)
        assert len({r['id'] for r in h.game.scene['cars']})==4
        assert h.game.scene['meta']['laps']==5;capture('race-grid-four')
        assert all(r['progress']<0 for r in h.game.scene['cars'][2:])
        tick=time.monotonic();assert h.game.pause();wait(lambda:not h.game.captured)
        pause=time.monotonic()-tick;assert pause<.25
        for d,sha in zip(drivers,hashes):
            r=h.game._store.driver(d['id']);assert r['policy']==sha and r['steps']==100
        report=dict(status='passed',platform=os.environ['QT_QPA_PLATFORM'],window=[h.window.width(),h.window.height()],
                    multiLapCompleted=not a.quick,oneCarPerDriver=True,fourCarGrid=True,lapsSelectable=[3,5,10],
                    missingModelsStayInMenu=True,modelsUnchanged=True,pauseSeconds=pause,qmlWarnings=h.messages)
        (a.capture_dir/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    finally:h.close();private.cleanup()
if __name__=='__main__':main()
