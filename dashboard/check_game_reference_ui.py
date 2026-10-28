"""Moving metric circuit and camera qualification, in isolated application state."""
import argparse
import json
import os
from pathlib import Path
import statistics
import time

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')


def main():
    from theme_fixture_support import isolate_process,LegacyHarness
    from theme_bundle import BundleManager,validate_project
    from PySide6.QtCore import qVersion
    p=argparse.ArgumentParser();p.add_argument('--capture-dir',type=Path)
    p.add_argument('--track',default='varano-short-1');p.add_argument('--seconds',type=float,default=8.)
    a=p.parse_args()
    private,base=isolate_process();a.capture_dir=a.capture_dir or base/'captures';a.capture_dir.mkdir(parents=True,exist_ok=True);project=Path(__file__).resolve().parents[1]
    bundle=project/'theme-projects/apple-calm/bundle';valid=validate_project(bundle)
    cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
    assert cache['digest']==valid['digest'] and cache['result']['qt']==qVersion()
    BundleManager(base,app_root=project/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    h=LegacyHarness(base,{'theme':'base','variant':'day','motion':'normal','game':True})
    def wait(predicate):
        end=time.monotonic()+25
        while not predicate() and time.monotonic()<end:h.pump(10)
        assert predicate(),h.game.snapshot
    def capture(name):
        h.pump(50);assert h.window.grabWindow().save(str(a.capture_dir/(name+'.png')))
    try:
        assert h.service.selectDraft('studio.applecalm');h.wait_ready()
        assert h.service.setToken('typography.textScale',1.1);h.wait_ready()
        assert h.game.setTrack(a.track)
        reference=next(d for d in h.game.snapshot['drivers'] if d['algorithm']=='pure_pursuit')
        identity=reference['id'];assert h.game.selectDriver(identity)
        h.game._store.activate_academy(identity);h.game._refresh()
        original=h.game._store.driver(identity)
        h.expression('familyId="game"');h.wait_ready()
        assert h.game.start();wait(lambda:h.game.snapshot['runState']=='running' and bool(h.game.scene['cars']))
        assert h.game.snapshot['mode']=='campione';capture('following-start')
        frames=[];h.window.frameSwapped.connect(lambda:frames.append(time.monotonic()))
        started=time.monotonic();pumps=[];positions=[]
        while time.monotonic()-started<a.seconds:
            tick=time.monotonic();h.pump(10);pumps.append(time.monotonic()-tick)
            positions.append(h.game.scene['cars'][0]['progress'])
            assert not h.messages,h.messages
            assert h.game.snapshot['runState']=='running',h.game.snapshot
        intervals=sorted(b-a for a,b in zip(frames,frames[1:]))
        frame_report={'frames':len(frames),'medianSeconds':statistics.median(intervals) if intervals else None,
                      'p95Seconds':intervals[min(len(intervals)-1,int(len(intervals)*.95))] if intervals else None,
                      'maxSeconds':max(intervals) if intervals else None,
                      'maxEventPumpSeconds':max(pumps),'movingProgressMeters':max(positions)-min(positions),
                      'scope':'Qt frameSwapped while reference car moves; no optical FPS claim'}
        assert frame_report['movingProgressMeters']>10
        capture('following-moving')
        for camera in ('duello','circuito','sensori'):
            h.expression('activateKey(8)');h.pump(80)
            assert h.game.snapshot['camera']==camera;capture(camera)
        tick=time.monotonic();h.expression('activateKey(5)');wait(lambda:not h.game.captured)
        latency=time.monotonic()-tick;assert latency<.25
        assert h.game._store.driver(identity)==original
        assert h.game.start();wait(lambda:h.game.captured)
        h.expression('activateKey(1)');wait(lambda:h.game._process is None)
        assert h.value('familyId')=='oggi';assert not h.messages,h.messages
        report={'status':'passed','platform':os.environ['QT_QPA_PLATFORM'],'window':[960,640],
                'track':a.track,'seconds':a.seconds,'cameras':['segui','duello','circuito','sensori'],
                'referenceNoTraining':True,'pauseAckSeconds':latency,'qmlWarnings':h.messages,
                'movingFrameTiming':frame_report}
        (a.capture_dir/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    finally:h.close();private.cleanup()


if __name__=='__main__':main()
