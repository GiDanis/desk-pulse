"""Private real Main/Worker, timing events and native event-loop frame samples."""
import argparse,os,json,time,statistics
from copy import deepcopy
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')


def main():
    from theme_fixture_support import isolate_process,LegacyHarness
    from theme_bundle import BundleManager,validate_project
    from PySide6.QtCore import QEventLoop,QTimer,QObject,qVersion
    from check_game_residual_ui import qualify_roster
    p=argparse.ArgumentParser();p.add_argument('--theme',default='apple');p.add_argument('--output',type=Path,required=True);p.add_argument('--sample',type=float,default=12);args=p.parse_args()
    private,base=isolate_process();project=Path(__file__).resolve().parents[1];args.output.mkdir(parents=True,exist_ok=True)
    if args.theme=='apple':
        bundle=project/'theme-projects/apple-calm/bundle';v=validate_project(bundle);cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
        assert cache['digest']==v['digest'] and cache['result']['qt']==qVersion()
        BundleManager(base,app_root=project/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    h=LegacyHarness(base,dict(theme=args.theme if args.theme!='apple' else 'base',variant='day',motion='normal',game=True));captures=[]
    def wait(f,seconds=90):
        end=time.monotonic()+seconds
        while time.monotonic()<end and not f():h.pump(10)
        assert f(),h.game.snapshot
    def capture(name):
        assert h.window.grabWindow().save(str(args.output/(name+'.png')));captures.append(name)
    def event_sample(seconds):
        frames=[]
        def frame():frames.append(time.monotonic())
        h.window.frameSwapped.connect(frame);loop=QEventLoop();QTimer.singleShot(int(seconds*1000),loop.quit);loop.exec();h.window.frameSwapped.disconnect(frame)
        spans=sorted(b-a for a,b in zip(frames,frames[1:]));return dict(samples=len(spans),p95=spans[int(len(spans)*.95)] if spans else None,maximum=max(spans) if spans else None)
    try:
        if args.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
        assert h.service.setToken('typography.textScale',1.1);h.wait_ready();qualify_roster(h.game._store);h.game._refresh()
        h.expression('familyId="game"');h.wait_ready();assert h.game.setMode('gara');h.game._race_laps=5;h.game._camera='circuito'
        def start_race():
            assert h.game.start();wait(lambda:h.game.scene.get('meta',{}).get('time',0)>2)
        start_race()
        hud=h.window.findChild(QObject,'gameTimingHud');assert hud and hud.property('visible')
        capture('personal-infield');samples=[]
        # Real Qt event loop, same active race. ABBA avoids one directional drift.
        for n,enabled in enumerate((True,False,False,True)):
            if n and args.sample>30:
                assert h.game.pause();wait(lambda:h.game.snapshot['saveState']=='saved')
                h.game.stop();start_race()
                hud=h.window.findChild(QObject,'gameTimingHud')
            hud.setProperty('contentEnabled',enabled)
            first=h.game.scene['meta']['time'];measured=event_sample(args.sample)
            assert h.game.snapshot['runState']=='running' and len(h.game.scene['cars'])==5
            samples.append(dict(hud=enabled,simulationStart=first,simulationEnd=h.game.scene['meta']['time'],**measured))
        hud.setProperty('contentEnabled',True)
        wait(lambda:len(h.game.scene.get('cars',[]))==5 and all(c.get('timing',{}).get('last') for c in h.game.scene['cars']))
        capture('last-lap-sectors');assert len(h.game.scene['cars'])==5
        before=h.game.scene['meta']['selected'];pilot=hud.property('pilot');h.game.selectAttempt(1)
        wait(lambda:h.game.scene['meta']['selected']!=before and hud.property('pilot')!=pilot)
        capture('selected-pilot');h.game._camera='sensori';h.game.changed.emit();h.pump(100)
        assert not hud.property('visible');h.game._camera='circuito';h.game.changed.emit();h.pump(100)
        assert h.game.pause();wait(lambda:h.game.snapshot['saveState']=='saved')
        assert not h.game.captured
        with h.game._store.connect() as db:
            n=db.execute('SELECT count(*) FROM timing_laps').fetchone()[0]
            assert n>=15,n  # 10 initial qualifying records + >=5 actual race laps.
        # Rendering-only edge fixtures, clearly distinct from measured race records.
        real=deepcopy(h.game.scene);car=real['cars'][real['meta']['selected']];fixture=deepcopy(car['timing'])
        hud.setProperty('visible',True);hud.setProperty('timing',dict(fixture,personal=None,last=None,deltas=[None,None,None],referenceLabel='Settori da misurare'));h.pump(100);capture('fixture-no-times')
        invalid=deepcopy(fixture);invalid['last']=dict(invalid['last'] or {},time=72.345,clean=False,standingStart=False)
        invalid['deltas']=[None,None,None];hud.setProperty('timing',invalid);h.pump(100);capture('fixture-invalid')
        hud.setProperty('timing',dict(fixture,source='preview'));h.pump(100);capture('fixture-preview')
        h.service.setVariant('night');h.wait_ready();h.pump(100);capture('night-text-scale-110')
        assert not h.messages,h.messages
        report=dict(status='passed',theme=args.theme,window=[h.window.width(),h.window.height()],captures=captures,timingRecords=n,fiveCarsVisible=True,selectionVerified=True,saveAcknowledgedAfterTiming=True,frameSamples=samples,eventLoop='QEventLoop.exec during ABBA, no processEvents pumping in measured samples; fresh identical seeded race per long segment',qmlWarnings=h.messages)
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    finally:h.close();private.cleanup()

if __name__=='__main__':main()
