"""Private native event-loop traces. No pumping/screenshots inside measured windows."""
import argparse,json,os,time,shutil,math
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')


def main():
    from theme_fixture_support import isolate_process,LegacyHarness
    from PySide6.QtCore import QEventLoop,QTimer,QObject,qVersion
    from theme_bundle import BundleManager,validate_project
    from check_game_residual_ui import qualify_roster
    parser=argparse.ArgumentParser();parser.add_argument('--theme',default='base');parser.add_argument('--load',default='race',choices=('race','qualification','ppo','sac','td3','tactic'))
    parser.add_argument('--seconds',type=float,default=120);parser.add_argument('--segments',type=int,default=1);parser.add_argument('--trace',action='store_true');parser.add_argument('--output',type=Path,required=True);parser.add_argument('--mature',action='store_true')
    a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    private,base=isolate_process();project=Path(__file__).resolve().parents[1]
    if a.theme=='apple':
        bundle=project/'theme-projects/apple-calm/bundle';v=validate_project(bundle)
        cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text());assert cache['digest']==v['digest'] and cache['result']['qt']==qVersion()
        BundleManager(base,app_root=project/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    h=None;runs=[]
    from game_store import GameStore
    store=GameStore(base/'state/game')
    def wait(f,seconds=120):
        end=time.monotonic()+seconds
        while time.monotonic()<end and not f():h.pump(10)
        assert f(),h.game.snapshot
    def visual_items(item):
        yield item
        for child in item.childItems():yield from visual_items(child)
    def percentile(values,p):
        s=sorted(values);return s[min(len(s)-1,math.ceil(p*len(s))-1)] if s else None
    try:
        drivers=store.drivers();driver=drivers[{'ppo':1,'sac':2,'td3':3,'tactic':4}.get(a.load,0)]
        if a.mature and a.load not in ('race','qualification'):
            # Synthetic replay maturity is explicit. It exercises realistic array
            # size/compression, and is not evidence of a learned racing skill.
            from game_residual_trainer import ResidualTrainer
            from game_residual_learning import OffPolicy
            import numpy as np
            t=ResidualTrainer(driver['profile'],'oval-1',objective='impara_sorpasso');private_seconds=60.
            if isinstance(t.learner,OffPolicy):
                rng=np.random.default_rng(4051);rows=t.learner.replay
                rows[:]=rng.normal(0,.2,rows.shape);rows[:,90:92]=np.tanh(rows[:,90:92]);rows[:,92]=.001;rows[:,183]=0
                t.learner.count=t.learner.capacity;t.learner.transitions=t.learner.capacity;t.learner.cursor=0
            else:
                # Actual mature PPO checkpoint when supplied; weights/optimizer
                # preserved in the private store, with migration at Start.
                mature=Path(os.environ.get('SMARTPC_MATURE_PPO','/nonexistent'))
                if mature.exists():
                    c=json.loads(mature.read_text());private_seconds=c.get('seconds',60.)
                    original=store.artifact(c);c['migrationSource']=original
                    t=ResidualTrainer(driver['profile'],'oval-1',c,objective='impara_sorpasso')
            store.save_training(driver['id'],t.checkpoint(private_seconds),t.learner.policy(),t.steps,private_seconds,t.metric,t.state)
        if a.load=='race':qualify_roster(store)
        # Prepare large fixtures before creating Qt timers/windows. Headless
        # qualifying or replay encoding must not starve a pending renderer load.
        h=LegacyHarness(base,dict(theme='base' if a.theme=='apple' else a.theme,variant='day',motion='normal',game=True))
        if a.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
        h.game._refresh();h.expression('familyId="game"');h.wait_ready()
        if a.load in ('race','qualification'):
            assert h.game.setMode('gara' if a.load=='race' else 'qualifica');h.game._race_laps=10
        else:
            assert h.game.selectDriver(driver['id']);assert h.game.setMode('impara_sorpasso')
        for n in range(a.segments):
            if n:h.game.stop()
            assert h.game.start();wait(lambda:h.game.snapshot['runState']=='running' and h.game.scene.get('meta',{}).get('time',0)>3)
            root=next(x for x in h.window.findChildren(QObject,'gameVisual') if x.property('track'))
            root.setProperty('tracing',a.trace)
            frames=[];poses=[];packets=[]
            def swapped():frames.append(time.monotonic())
            def presented(v):
                poses.append(v.toVariant() if hasattr(v,'toVariant') else v)
            def received():
                s=h.game.scene;packets.append(dict(received=time.monotonic(),timestamp=s['timestamp'],sequence=s['sequence'],phase=s['meta'].get('phase'),simTime=s['meta'].get('time'),carCount=len(s['cars']),rate=s['meta'].get('simRate'),saveState=h.game._save_state,previewState=s['meta'].get('previewState','running'),speed=s['cars'][s['meta'].get('selected',0)%len(s['cars'])].get('speed',0),resetKey=s['cars'][s['meta'].get('selected',0)%len(s['cars'])].get('resetKey',''),checkpoint=s['meta'].get('checkpoint'),pipeline=s['meta'].get('pipeline')))
            h.window.frameSwapped.connect(swapped)
            if a.trace:root.posePresented.connect(presented);h.game.sceneChanged.connect(received)
            before=time.monotonic();loop=QEventLoop();timer=QTimer();timer.setSingleShot(True);timer.setTimerType(__import__('PySide6.QtCore',fromlist=['Qt']).Qt.TimerType.PreciseTimer);timer.timeout.connect(loop.quit);timer.start(round(a.seconds*1000));loop.exec();elapsed=time.monotonic()-before
            h.window.frameSwapped.disconnect(swapped)
            if a.trace:root.posePresented.disconnect(presented);h.game.sceneChanged.disconnect(received)
            state=h.game.snapshot['runState'];assert state=='running',(a.load,state,h.game.scene.get('meta'))
            spans=[(b-c)*1000 for c,b in zip(frames,frames[1:])]
            motion=[(float(b['presentedMs'])-float(c['presentedMs'])) for c,b in zip(poses,poses[1:])]
            ages=[p['presentedMs']-p.get('poseSampleMs',p['publishedMs']) for p in poses if p.get('poseSampleMs',0)>0]
            summary=dict(segment=n,elapsed=elapsed,swaps=len(frames),softwareWallHz=(len(frames)-1)/(frames[-1]-frames[0]) if len(frames)>1 else None,
                swapP95Ms=percentile(spans,.95),swapP99Ms=percentile(spans,.99),swapMaxMs=max(spans) if spans else None,swapOver100=sum(v>100 for v in spans),
                presentP95Ms=percentile(motion,.95),presentP99Ms=percentile(motion,.99),presentMaxMs=max(motion) if motion else None,presentOver100=sum(v>100 for v in motion),
                poseAgeP95Ms=percentile(ages,.95),poseAgeMaxMs=max(ages) if ages else None,allCars=len(h.game.scene['cars']),visibleCars=sum(item.isVisible() for item in visual_items(root) if item.objectName().startswith('gameCar') and item.objectName()[7:].isdigit()),runState=state)
            runs.append(summary)
            (a.output/f'raw-{n}.json').write_text(json.dumps(dict(frames=frames,poses=poses,packets=packets),separators=(',',':')))
            assert h.game.pause();wait(lambda:h.game.snapshot['saveState']=='saved',180)
            assert h.window.grabWindow().save(str(a.output/f'end-{n}.png'))
            print(json.dumps(summary),flush=True)
        assert not h.messages,h.messages
        report=dict(status='passed',theme=a.theme,load=a.load,mature=a.mature,syntheticOffPolicyReplay=a.mature and a.load in ('sac','td3','tactic'),trace=a.trace,presenter=os.environ.get('SMARTPC_GAME_PRESENTER','timer'),window=[h.window.width(),h.window.height()],qt=qVersion(),runs=runs,qmlWarnings=h.messages,opticalFPS=False)
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    finally:
        if h is not None:h.close()
        private.cleanup()

if __name__=='__main__':main()
