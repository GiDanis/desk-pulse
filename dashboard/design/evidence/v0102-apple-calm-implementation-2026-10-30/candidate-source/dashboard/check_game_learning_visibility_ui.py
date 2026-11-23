"""Actual private worker: candidate laps, gradient counters, and safe pause."""
import argparse,json,os,time,hashlib
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')


def main():
    from theme_fixture_support import isolate_process,LegacyHarness
    from game_store import GameStore
    from game_residual_trainer import ResidualTrainer
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--theme',choices=('base','functional','apple'),default='base')
    p.add_argument('--checkpoint',type=Path);p.add_argument('--seconds',type=float,default=78)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    private,base=isolate_process();store=GameStore(base/'state/game');driver=store.drivers()[1]
    if args.checkpoint:
        c=json.loads(args.checkpoint.read_text())
        trainer=ResidualTrainer(driver['profile'],'oval-1',c,objective='impara')
        store.save_training(driver['id'],trainer.checkpoint(c.get('seconds',0)),trainer.learner.policy(),trainer.steps,c.get('seconds',0),trainer.metric,trainer.state)
    project=Path(__file__).resolve().parents[1]
    if args.theme=='apple':
        from theme_bundle import BundleManager,validate_project
        from PySide6.QtCore import qVersion
        bundle=project/'theme-projects/apple-calm/bundle';valid=validate_project(bundle)
        cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
        assert cache['digest']==valid['digest'] and cache['result']['qt']==qVersion()
        BundleManager(base,app_root=project/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    h=LegacyHarness(base,dict(theme='base' if args.theme=='apple' else args.theme,variant='day',motion='normal',game=True))
    rows=[]
    def wait(f,seconds=90):
        deadline=time.monotonic()+seconds
        while not f() and time.monotonic()<deadline:h.pump(10)
        assert f(),h.game.snapshot
    def received():
        s=h.game.scene;m=s.get('meta',{});r=m.get('residual',{})
        if not r:return
        car=s['cars'][0];timing=car.get('timing',{})
        row=dict(time=m['time'],trial=r['previewTrial'],updates=r['updates'],frozenUpdate=r['previewUpdate'],episodes=r['episodes'],verification=r['verification'],policy=m['policyVersion'],lap=timing.get('lapId'),last=timing.get('last'),valid=timing.get('currentValid'))
        if not rows or any(row[k]!=rows[-1][k] for k in ('trial','updates','episodes','verification')):rows.append(row)
    try:
        if args.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
        assert h.service.setToken('typography.textScale',1.1);h.wait_ready()
        h.expression('familyId="game"');h.wait_ready()
        h.game._refresh();assert h.game.selectDriver(driver['id']);assert h.game.setMode('impara')
        h.game.sceneChanged.connect(received)
        assert h.game.start();wait(lambda:bool(rows))
        assert h.window.grabWindow().save(str(args.output/'start.png'))
        started=time.monotonic()
        while time.monotonic()-started<args.seconds:
            h.pump(10);assert not h.messages,h.messages
        assert h.window.grabWindow().save(str(args.output/'learning.png'))
        assert rows[-1]['updates']>rows[0]['updates'],rows
        assert rows[-1]['episodes']>rows[0]['episodes'],rows
        assert rows[-1]['trial']>rows[0]['trial'],rows
        switches=[(a,b) for a,b in zip(rows,rows[1:]) if a['policy']!=b['policy']]
        assert switches,'No new candidate became visible'
        for a,b in switches:
            assert b['trial']>a['trial'] and b['last'] and b['last']['policy']==a['policy'],(a,b)
            assert b['valid'],b
        assert h.game.pause();wait(lambda:h.game.snapshot['saveState']=='saved' and not h.game.captured)
        saved=store.load(store.driver(driver['id'])['checkpoint'])
        assert saved['previewPolicy'] and saved['previewTrial']==rows[-1]['trial']
        names=('game_residual_trainer.py','game_timing.py','presentations/GameVisual.qml','presentations/GameTimingHud.qml')
        report=dict(status='passed',theme=args.theme,resolution=[h.window.width(),h.window.height()],qmlWarnings=h.messages,
            elapsed=time.monotonic()-started,candidateSwitches=len(switches),initial=rows[0],final=rows[-1],events=rows,
            sourceHashes={n:hashlib.sha256((Path(__file__).parent/n).read_bytes()).hexdigest() for n in names},originalStoreUsed=False)
        assert report['resolution']==[960,640]
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k not in ('events','sourceHashes')}),flush=True)
    finally:h.close();private.cleanup()


if __name__=='__main__':main()
