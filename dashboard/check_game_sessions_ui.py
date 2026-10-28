"""Real Main: five session modes, isolated checkpoints and actual Qualifica -> Gara."""
import argparse,json,os,time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')

def main():
    from theme_fixture_support import isolate_process,LegacyHarness
    from theme_bundle import BundleManager,validate_project
    from PySide6.QtCore import qVersion
    parser=argparse.ArgumentParser();parser.add_argument('--theme',default='base',choices=('base','functional','apple'));parser.add_argument('--output',type=Path,required=True);parser.add_argument('--qualification',action='store_true');parser.add_argument('--source-checkpoint',type=Path);parser.add_argument('--seconds',type=float,default=10);a=parser.parse_args()
    private,base=isolate_process();root=Path(__file__).resolve().parents[1]
    if a.theme=='apple':
        bundle=root/'theme-projects/apple-calm/bundle';valid=validate_project(bundle);cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text());assert cache['digest']==valid['digest'] and cache['result']['qt']==qVersion()
        BundleManager(base,app_root=root/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    h=LegacyHarness(base,dict(theme='functional' if a.theme=='functional' else 'base',variant='day',motion='normal',game=True))
    def wait(f,seconds=20):
        end=time.monotonic()+seconds
        while not f() and time.monotonic()<end:h.pump(5)
        assert f(),h.game.snapshot['message']
    def pause():
        assert h.game.pause();wait(lambda:h.game.snapshot['runState']=='paused' and h.game.snapshot['saveState']!='saving')
        assert h.game.snapshot['saveState']!='error',h.game.snapshot['message'];h.game.stop()
    records=[];rates=[];frame_times=[];moving_gaps=[];last_moving=[None];clock_times=[]
    try:
        if a.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
        h.expression('familyId="game"');h.wait_ready()
        assert h.game.createDriverPreset('neat');identity=h.game._selected
        if a.source_checkpoint:
            from game_academy_trainer import AcademyTrainer
            source=json.loads(a.source_checkpoint.read_text());checkpoint=source['checkpoint'];profile=source['profile']
            h.game._store.set_profile(identity,profile,allow_reconfigure=True)
            trainer=AcademyTrainer(profile,'oval-1',checkpoint)
            h.game._store.save_training(identity,checkpoint,trainer.learner.policy(),checkpoint['steps'],checkpoint['seconds'],curriculum=checkpoint['curriculum'])
            h.game._refresh()
        for mode in ('impara','impara_infinito','impara_sorpasso'):
            assert h.game.setMode(mode);assert h.game.start();wait(lambda:h.game.snapshot['runState']=='running' and h.game.scene.get('cars') and h.game.scene.get('mode')==mode)
            h.pump(1000);assert len(h.game.scene['cars'])==(3 if mode=='impara_sorpasso' else 1)
            assert h.game.scene['meta']['presentation']=='preview'
            before=h.game.scene['cars'][0]['resetKey'];h.pump(1000)
            assert h.game.scene['cars'][0]['resetKey']==before
            pause();records.append(dict(mode=mode,steps=h.game._store.driver(identity)['steps']))
        assert h.game.setMode('impara');original=h.game._store.driver(identity)['checkpoint'];assert original
        assert h.game.setMode('impara_infinito');assert h.game.start();wait(lambda:h.game.snapshot['runState']=='running')
        h.pump(1500)
        measuring=[True]
        def rendered():
            if not measuring[0]:return
            now=time.monotonic();frame_times.append(now);row=h.game.scene['cars'][0]
            key=row.get('resetKey')
            if row.get('completed') or row.get('speed',0)<.5:last_moving[0]=None;return
            if last_moving[0] and last_moving[0][0]==key:moving_gaps.append((now-last_moving[0][1])*1000)
            last_moving[0]=(key,now)
        h.window.frameSwapped.connect(rendered)
        from game_presentation import GamePresentationClock
        clocks=[c for c in h.window.findChildren(GamePresentationClock) if c.running]
        for c in clocks:c.tick.connect(lambda stamp:clock_times.append(stamp/1000) if measuring[0] else None)
        start=time.monotonic();last=None;sim=wall=0
        while time.monotonic()-start<a.seconds:
            h.pump(5);row=h.game.scene['cars'][0];now=time.monotonic()
            if last and last[0]==row['resetKey'] and not row['completed']:
                sim+=max(0,row['simulatedTime']-last[1]);wall+=now-last[2]
            last=(row['resetKey'],row['simulatedTime'],now)
            if row.get('simRate') is not None:rates.append(row['simRate'])
        measuring[0]=False
        pause()
        h.game._store.select_objective('impara');assert h.game._store.driver(identity)['checkpoint']==original
        if a.qualification:
            # These are declared reference pilots; no manufactured neural certificates.
            people=[]
            for _ in range(2):
                assert h.game.createDriverPreset('pure_pursuit');person=h.game._selected;people.append(person)
                assert h.game.setMode('impara');assert not h.game.start()
                assert h.game.setMode('qualifica');assert h.game.start();wait(lambda:h.game.snapshot['runState']=='running')
                wait(lambda:bool(h.game._store.driver(person)['timedQualifications']),seconds=100)
                h.game.pause();wait(lambda:h.game.snapshot['runState']=='paused');h.pump(100);h.game.stop()
            assert h.game.setMode('gara');h.game._participants=people;h.game._grid_order='slowest_first';assert h.game.start();wait(lambda:h.game.snapshot['runState']=='running' and h.game.scene['mode']=='gara')
            h.pump(4500);assert len(h.game.scene['cars'])==2
            pause();records.append(dict(mode='gara',certifiedReferencePilots=2))
        a.output.mkdir(parents=True,exist_ok=True);h.window.grabWindow().save(str(a.output/'screen.png'))
        intervals=sorted((y-x)*1000 for x,y in zip(frame_times,frame_times[1:]))
        def percentile(p):return intervals[int(p*(len(intervals)-1))] if intervals else None
        assert not h.messages,h.messages
        clock_gaps=sorted((b-a)*1000 for a,b in zip(clock_times,clock_times[1:]))
        def dist(rows):
            rows=sorted(rows)
            return dict(n=len(rows),p95Ms=rows[int(.95*(len(rows)-1))],p99Ms=rows[int(.99*(len(rows)-1))],maxMs=max(rows)) if rows else None
        report=dict(clockHz=len(clock_times)/a.seconds,clockGaps=dist(clock_gaps),movingFrameGaps=dist(moving_gaps),status='passed',platform=os.environ['QT_QPA_PLATFORM'],theme=a.theme,modes=records,watchedSimRate=sim/wall if wall else None,seconds=a.seconds,frames=len(frame_times),frameP95Ms=percentile(.95),frameP99Ms=percentile(.99),frameMaxMs=max(intervals) if intervals else None,qmlWarnings=h.messages,qualification=a.qualification)
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
    finally:h.close();private.cleanup()

if __name__=='__main__':main()
